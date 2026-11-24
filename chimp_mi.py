# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 3: chimpanzee nut-cracking action sequences.

Calibrates the mutual-information (MI) decay result of Howard-Spink et al. 2024 (PeerJ 12:e18484)
against finite-state worlds: N1 first-order Markov chains (their null), N2 hidden Markov models
fitted to each chimpanzee (new), and P recursive Lin-Tegmark sequences (positive control).
Plan: AMENDMENT-2-STAGE3-CHIMP.md; code-level choices: AMENDMENT-3-STAGE3-CODE.md.

Two pipelines are run on the same MI profiles:
  paper (primary, AMENDMENT-3): as in the authors' public R code (Mendeley 10.17632/xdtnxzdchj.3,
      scripts 3, 6 and 7): pairs d apart over the concatenated sequence, entropy
      log2(N) - (1/N) sum N_i psi(N_i), 1,000 permutations per distance, Adjusted_MI = MI - mean
      permuted MI, lower bound = Adjusted_MI - 1.96 * SE(mean permuted MI); the fitted range is
      d = 1 .. (first d with lower bound < 0) - 1; models without constants fitted by unweighted
      least squares on the linear scale, no bounds; AICc counting the residual variance (3, 3, 5).
  a2 (secondary, as registered in AMENDMENT-2): cut at the first d with MI below the 95th
      percentile of the permuted MI; positive Adjusted_MI only; fits on log residuals weighted by
      1/log(1+d) (stage-1 code); AICc with 2, 2, 4 parameters.
Usage: python chimp_mi.py fetch --data-dir D ; python chimp_mi.py run --data-dir D --out-dir O
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
import time
import urllib.request
import zipfile

import numpy as np

INDIVIDUALS = {"fanle": 1368, "flanle": 453, "foaf": 299, "jeje": 1373, "jire": 482,
               "joya": 1178, "peley": 1168, "tua": 1940}
DMAX = 100
NPERM = 1000
SEED = 20261125
WORLDS = 100
K_RANGE = (2, 3, 4, 5, 6)
UNSAFE, SAFE, CONTROL_OK = 0.30, 0.10, 0.80
NA_TOKENS = {"", "NA", "N/A", "NaN", "nan", "NULL"}
EULER_GAMMA = 0.5772156649015329
MODELS = ("exponential", "powerlaw", "composite")
NPAR = {"exponential": 2, "powerlaw": 2, "composite": 4}
VARIANTS = ("paper", "a2")
KINDS = ("N1", "N2", "P")

MENDELEY = "https://data.mendeley.com/public-files/datasets/xdtnxzdchj/files/{}/file_downloaded"
FILES = {"Concatenated.zip": ("a760868a-74eb-4691-8a99-a8b096b290f1", 323483),
         "MI Estimation.zip": ("ede3a82b-ab9f-4345-a83f-f4a3d709703e", 126078)}


# ----------------------------------------------------------------------------- estimator

def psi_table(n):
    """digamma(k) for k = 0..n; entry 0 is 0 (only ever multiplied by a zero count)."""
    t = np.zeros(n + 1)
    if n >= 1:
        steps = np.concatenate([[0.0], np.cumsum(1.0 / np.arange(1, n))]) if n > 1 else np.zeros(1)
        t[1:] = -EULER_GAMMA + steps
    return t


def est_entropy(counts, psi):
    """log2(N) - (1/N) sum_i N_i psi(N_i) (the authors' estimator; mixed log bases kept)."""
    c = np.asarray(counts, dtype=np.int64)
    n = int(c.sum())
    if n <= 0:
        return float("nan")
    return float(np.log2(n) - np.sum(c * psi[c]) / n)


def mi_profile(seq, rng, nperm=NPERM, dmax=DMAX):
    """MI, mean / SE / 95th percentile of permuted MI at d = 1..dmax. seq: ints, -1 = missing
    (pairs with a missing element are dropped, as na.omit in the authors' JoinAct)."""
    s = np.asarray(seq, dtype=np.int64)
    K = int(s.max()) + 1 if s.size and s.max() >= 0 else 1
    psi = psi_table(len(s) + 1)
    mi = np.full(dmax, np.nan)
    pm = np.full(dmax, np.nan)
    se = np.full(dmax, np.nan)
    q95 = np.full(dmax, np.nan)
    offs = (np.arange(nperm, dtype=np.int64) * (K * K))[:, None]
    for d in range(1, dmax + 1):
        if d >= len(s):
            break
        a, b = s[:-d], s[d:]
        ok = (a >= 0) & (b >= 0)
        a, b = a[ok], b[ok]
        n = len(a)
        if n < 2:
            continue
        ha = est_entropy(np.bincount(a, minlength=K), psi)
        hb = est_entropy(np.bincount(b, minlength=K), psi)
        mi[d - 1] = ha + hb - est_entropy(np.bincount(a * K + b, minlength=K * K), psi)
        bp = rng.permuted(np.tile(b, (nperm, 1)), axis=1)
        j = (a[None, :] * K + bp + offs).ravel()
        cj = np.bincount(j, minlength=nperm * K * K).reshape(nperm, K * K)
        hj = np.log2(n) - np.sum(cj * psi[cj], axis=1) / n
        perm = ha + hb - hj
        pm[d - 1] = perm.mean()
        se[d - 1] = perm.std(ddof=1) / math.sqrt(nperm) if nperm > 1 else 0.0
        q95[d - 1] = np.quantile(perm, 0.95)
    return {"mi": mi, "perm_mean": pm, "perm_se": se, "perm_q95": q95}


def condense(seq):
    """Collapse runs of an identical element to one (the authors' condense rule)."""
    s = np.asarray(seq, dtype=np.int64)
    if s.size == 0:
        return s
    keep = np.ones(len(s), dtype=bool)
    keep[1:] = s[1:] != s[:-1]
    return s[keep]


# ----------------------------------------------------------------------------- range rules

def paper_cut(prof):
    """(index_max, number of fitted points): index_max = first d with lower bound < 0 (else the
    last finite d), fitted d = 1..index_max-1 (script 7: rows 1..which(LB < 0)[1] - 1)."""
    adj = prof["mi"] - prof["perm_mean"]
    lb = adj - 1.96 * prof["perm_se"]
    with np.errstate(invalid="ignore"):
        neg = np.flatnonzero(lb < 0)
    if neg.size:
        return int(neg[0]) + 1, int(neg[0])
    fin = np.flatnonzero(np.isfinite(adj))
    last = int(fin[-1]) + 1 if fin.size else 0
    return len(adj), last  # script 6: index_max <- 100 when no lower bound is negative


def a2_cut(prof):
    """Number of leading d before the first d whose MI is below the permuted 95th percentile."""
    with np.errstate(invalid="ignore"):
        below = np.flatnonzero(prof["mi"] < prof["perm_q95"])
    if below.size:
        return int(below[0])
    fin = np.flatnonzero(np.isfinite(prof["mi"]))
    return int(fin[-1]) + 1 if fin.size else 0


def positive_range(prof):
    """Largest d with Adjusted_MI > 0 (0 if none)."""
    adj = prof["mi"] - prof["perm_mean"]
    with np.errstate(invalid="ignore"):
        pos = np.flatnonzero(adj > 0)
    return int(pos[-1]) + 1 if pos.size else 0


# ----------------------------------------------------------------------------- model fits

def model_values(name, p, x):
    with np.errstate(all="ignore"):
        if name == "exponential":
            return p[0] * np.exp(-x * p[1])
        if name == "powerlaw":
            return p[0] * x ** p[1]
        return p[0] * np.exp(-x * p[1]) + p[2] * x ** p[3]


def start_grid(name, y, variant):
    y0 = float(y[0]) if len(y) and np.isfinite(y[0]) and y[0] != 0 else 1e-3
    if variant == "paper":
        if name == "exponential":
            return [(1.0, 1.0), (y0, 0.1), (y0, 0.5), (y0, 0.02)]
        if name == "powerlaw":
            return [(0.5, -0.1), (y0, -0.3), (y0, -1.0)]
        return [(0.1, 0.1, 0.1, 0.1), (-0.1, 0.1, 0.1, 0.1), (y0 / 2, 0.5, y0 / 2, -0.5),
                (y0 / 2, 0.1, y0 / 2, -1.0)]
    y0 = abs(y0)
    if name == "exponential":
        return [(y0, 0.1), (y0, 0.5), (y0, 0.02)]
    if name == "powerlaw":
        return [(y0, -0.1), (y0, -0.3), (y0, -1.0)]
    return [(y0 / 2, 0.5, y0 / 2, -0.5), (y0 / 2, 0.1, y0 / 2, -1.0), (y0 / 2, 0.05, y0 / 2, -0.2)]


A2_LOWER = {"exponential": [1e-12, -np.inf], "powerlaw": [1e-12, -np.inf],
            "composite": [1e-12, -np.inf, 1e-12, -np.inf]}


def fit_model(name, x, y, variant, extra_starts=()):
    """Best (rss, params) over the starts (each start itself is also a candidate), or None.
    Needs scipy."""
    from scipy.optimize import least_squares
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if variant == "paper":
        def resid(p):
            r = model_values(name, p, x) - y
            return np.where(np.isfinite(r), r, 1e6)
        lb = None
    else:
        w = 1.0 / np.log1p(x)
        ly = np.log(y)
        lb = np.array(A2_LOWER[name], dtype=float)

        def resid(p):
            m = model_values(name, p, x)
            with np.errstate(all="ignore"):
                r = (ly - np.log(np.maximum(m, 1e-300))) * w
            return np.where(np.isfinite(r), r, 1e6)
    best = None
    for x0 in list(start_grid(name, y, variant)) + list(extra_starts):
        x0 = np.asarray(x0, dtype=float)
        if lb is not None:
            x0 = np.maximum(x0, lb)
        if not np.all(np.isfinite(x0)):
            continue
        r0 = resid(x0)
        cands = [(float(r0 @ r0), x0)]
        try:
            if variant == "paper":
                r = least_squares(resid, x0, method="lm", max_nfev=4000)
            else:
                r = least_squares(resid, x0, method="trf", bounds=(lb, np.inf), max_nfev=4000)
            cands.append((float(r.fun @ r.fun), np.asarray(r.x, dtype=float)))
        except Exception:  # noqa: BLE001 - a failed start is skipped, as a failed nlsLM would be
            pass
        for rss, p in cands:
            if np.isfinite(rss) and (best is None or rss < best[0]):
                best = (rss, [float(v) for v in p])
    return best


def aicc(n, k, rss):
    """AICc up to a constant shared by all models fitted to the same n points."""
    if n - k - 1 <= 0:
        return float("nan")
    rss = max(float(rss), 1e-300)
    return n * math.log(rss / n) + 2 * k + 2.0 * k * (k + 1) / (n - k - 1)


def n_params(name, variant):
    return NPAR[name] + (1 if variant == "paper" else 0)


def fit_curve(x, y, variant):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    if variant == "a2":
        keep &= y > 0
    x, y = x[keep], y[keep]
    n = len(x)
    out = {"n_points": n, "aicc": {}, "params": {}, "best": None, "pl_win": False, "margin": None}
    fits = {}
    for m in MODELS:
        k = n_params(m, variant)
        if n - k - 1 <= 0 or n < NPAR[m]:
            continue
        extra = []
        if m == "composite" and "exponential" in fits and "powerlaw" in fits:
            ae, be = fits["exponential"][1]
            cp, dp = fits["powerlaw"][1]
            tiny = 0.0 if variant == "paper" else 1e-12
            extra = [(ae, be, tiny, -0.5), (tiny, 0.1, cp, dp)]
        with np.errstate(all="ignore"):
            res = fit_model(m, x, y, variant, extra)
        if res is None:
            continue
        fits[m] = res
        out["aicc"][m] = aicc(n, k, res[0])
        out["params"][m] = res[1]
    valid = {m: v for m, v in out["aicc"].items() if np.isfinite(v)}
    if valid:
        best = min(valid, key=lambda m: valid[m])
        out["best"] = best
        out["pl_win"] = best in ("powerlaw", "composite")
        pl = [valid[m] for m in ("powerlaw", "composite") if m in valid]
        if "exponential" in valid and pl:
            out["margin"] = valid["exponential"] - min(pl)
    return out


def analyse_profile(prof, keep_curve=False):
    d = np.arange(1, len(prof["mi"]) + 1, dtype=float)
    adj = prof["mi"] - prof["perm_mean"]
    index_max, npts = paper_cut(prof)
    cut2 = a2_cut(prof)
    out = {"index_max": index_max, "range_pos": positive_range(prof),
           "paper": fit_curve(d[:npts], adj[:npts], "paper"),
           "a2": fit_curve(d[:cut2], adj[:cut2], "a2")}
    if keep_curve:
        out["curve"] = {"mi": prof["mi"].tolist(), "adj": adj.tolist(),
                        "lower": (adj - 1.96 * prof["perm_se"]).tolist(),
                        "perm_q95": prof["perm_q95"].tolist()}
    return out


# ----------------------------------------------------------------------------- generators

def mle_transition(seq, K):
    """Maximum-likelihood first-order transition matrix over consecutive non-missing pairs; a row
    with no outgoing pair gets the sequence's marginal frequencies."""
    s = np.asarray(seq, dtype=np.int64)
    a, b = s[:-1], s[1:]
    ok = (a >= 0) & (b >= 0)
    C = np.bincount(a[ok] * K + b[ok], minlength=K * K).reshape(K, K).astype(float)
    marg = np.bincount(s[s >= 0], minlength=K).astype(float)
    marg /= marg.sum()
    rows = C.sum(axis=1)
    P = np.where(rows[:, None] > 0, C / np.maximum(rows, 1.0)[:, None], marg[None, :])
    return P


def simulate_chain(rng, P, n, start):
    K = P.shape[0]
    cum = np.cumsum(P, axis=1)
    cum[:, -1] = 1.0
    u = rng.random(n)
    s = np.empty(n, dtype=np.int64)
    s[0] = int(start)
    for t in range(1, n):
        s[t] = min(int(np.searchsorted(cum[s[t - 1]], u[t], side="right")), K - 1)
    return s


def stationary(A):
    K = A.shape[0]
    M = np.vstack([A.T - np.eye(K), np.ones((1, K))])
    rhs = np.zeros(K + 1)
    rhs[-1] = 1.0
    v = np.linalg.lstsq(M, rhs, rcond=None)[0]
    v = np.maximum(v, 0.0)
    return v / v.sum()


def forward_backward(pi, A, B, obs):
    """Batched scaled forward-backward. pi (S,K), A (S,K,K), B (S,K,M), obs (T,) ints.
    Returns log-likelihood (S,), gamma (T,S,K) and summed xi (S,K,K)."""
    T = len(obs)
    S, K = pi.shape
    E = np.transpose(B[:, :, obs], (2, 0, 1))  # T,S,K
    alpha = np.empty((T, S, K))
    c = np.empty((T, S))
    a = pi * E[0]
    c[0] = np.maximum(a.sum(axis=1), 1e-300)
    alpha[0] = a / c[0][:, None]
    for t in range(1, T):
        a = np.matmul(alpha[t - 1][:, None, :], A)[:, 0, :] * E[t]
        c[t] = np.maximum(a.sum(axis=1), 1e-300)
        alpha[t] = a / c[t][:, None]
    beta = np.empty((T, S, K))
    beta[T - 1] = 1.0
    for t in range(T - 2, -1, -1):
        v = (E[t + 1] * beta[t + 1]) / c[t + 1][:, None]
        beta[t] = np.matmul(A, v[:, :, None])[:, :, 0]
    ll = np.log(c).sum(axis=0)
    gamma = alpha * beta
    if T > 1:
        v = (E[1:] * beta[1:]) / c[1:][:, :, None]  # T-1,S,K
        xi = np.einsum("tsk,skj,tsj->skj", alpha[:-1], A, v)
    else:
        xi = np.zeros((S, K, K))
    return ll, gamma, xi


def _normalise(x, axis):
    x = x + 1e-10
    return x / x.sum(axis=axis, keepdims=True)


def em_step(pi, A, B, obs, M):
    ll, gamma, xi = forward_backward(pi, A, B, obs)
    pi2 = _normalise(gamma[0], 1)
    A2 = _normalise(xi, 2)
    onehot = np.eye(M)[obs]  # T,M
    B2 = _normalise(np.einsum("tsk,tm->skm", gamma, onehot), 2)
    return ll, pi2, A2, B2


def hmm_fit(obs, M, K, rng, n_starts=5, max_iter=300, tol=1e-6):
    """Baum-Welch from n_starts random starts run together; returns the best start's parameters,
    log-likelihood, iterations and BIC."""
    obs = np.asarray(obs, dtype=np.int64)
    S = n_starts
    pi = rng.dirichlet(np.ones(K), size=S)
    A = rng.dirichlet(np.ones(K), size=(S, K))
    B = rng.dirichlet(np.ones(M), size=(S, K))
    prev = np.full(S, -np.inf)
    it = 0
    for it in range(1, max_iter + 1):
        ll, pi, A, B = em_step(pi, A, B, obs, M)
        done = np.all(ll - prev < tol)
        prev = ll
        if done:
            break
    ll = forward_backward(pi, A, B, obs)[0]
    s = int(np.argmax(ll))
    T = len(obs)
    p = (K - 1) + K * (K - 1) + K * (M - 1)
    return {"K": K, "loglik": float(ll[s]), "bic": float(-2 * ll[s] + p * math.log(T)),
            "n_params": p, "iterations": it, "pi": pi[s], "A": A[s], "B": B[s]}


def hmm_simulate(rng, A, B, n):
    K, M = B.shape
    st = simulate_chain(rng, A, n, start=rng.choice(K, p=stationary(A)))
    cumB = np.cumsum(B, axis=1)
    cumB[:, -1] = 1.0
    u = rng.random(n)
    em = (u[:, None] >= cumB[st]).sum(axis=1)
    return np.minimum(em, M - 1).astype(np.int64)


def random_sparse_rows(rng, k, ps=(0.7, 0.2, 0.1)):
    m = min(len(ps), k)
    w = np.array(ps[:m], dtype=float)
    w /= w.sum()
    P = np.zeros((k, k))
    for i in range(k):
        P[i, rng.choice(k, size=m, replace=False)] = w
    return P


def strongly_connected(adj):
    k = adj.shape[0]
    reach = (np.asarray(adj) > 0) | np.eye(k, dtype=bool)
    for _ in range(k):
        reach = reach | ((reach.astype(np.int64) @ reach.astype(np.int64)) > 0)
    return bool(reach.all())


def balanced_matrix(rng, k, ps=(0.7, 0.2, 0.1), tries=1000):
    for _ in range(tries):
        Mx = random_sparse_rows(rng, k, ps)
        if strongly_connected(Mx):
            return Mx
    raise RuntimeError("no irreducible matrix found")


def lin_tegmark_sequence(rng, M, depth, q=2):
    """Recursive hierarchical model (Lin and Tegmark 2017; as in stage 1's mi_decay.py)."""
    k = M.shape[0]
    cum = np.cumsum(M, axis=1)
    cum[:, -1] = 1.0
    seq = np.array([int(rng.integers(k))], dtype=np.int64)
    for _ in range(depth):
        u = rng.random((len(seq), q))
        child = (u[:, :, None] >= cum[seq][:, None, :]).sum(axis=2)
        seq = np.minimum(child, k - 1).reshape(-1).astype(np.int64)
    return seq


def lin_tegmark_n(rng, k, n):
    depth = max(1, int(math.ceil(math.log2(max(n, 2)))))
    return lin_tegmark_sequence(rng, balanced_matrix(rng, max(k, 2)), depth)[:n]


# ----------------------------------------------------------------------------- data

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    manifest = {}
    for name, (fid, size) in FILES.items():
        path = os.path.join(data_dir, name)
        if not (os.path.exists(path) and os.path.getsize(path) == size):
            req = urllib.request.Request(MENDELEY.format(fid), headers={"User-Agent": "MV2-research"})
            data = urllib.request.urlopen(req, timeout=300).read()
            with open(path, "wb") as fh:
                fh.write(data)
        manifest[name] = {"bytes": os.path.getsize(path), "expected_bytes": size,
                          "sha256": sha256(path)}
        print(f"{name}: {manifest[name]}", flush=True)
    with open(os.path.join(data_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    return 0


def _zip_members(zf):
    out = {}
    for m in zf.infolist():
        if m.is_dir():
            continue
        base = os.path.basename(m.filename)
        if m.filename.startswith("__MACOSX") or base.startswith("._"):
            continue
        out.setdefault(base.lower(), []).append(m)
    return out


def _read_csv(zf, member):
    text = zf.read(member).decode("utf-8-sig", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []
    body = [r for r in rows[1:] if any(c.strip() for c in r)]
    return rows[0], body


def _col(header, name):
    for i, h in enumerate(header):
        if h.strip() == name:
            return i
    for i, h in enumerate(header):
        if h.strip().lower() == name.lower():
            return i
    return None


def load_individuals(data_dir):
    """Event labels of each individual's Concatenated/<name>_all.csv (AMENDMENT-3 loader)."""
    report = {"members": [], "individuals": {}, "problems": []}
    seqs = {}
    with zipfile.ZipFile(os.path.join(data_dir, "Concatenated.zip")) as zf:
        members = _zip_members(zf)
        report["members"] = sorted([m.filename, m.file_size] for ms in members.values() for m in ms)
        for name, expected in INDIVIDUALS.items():
            cand = members.get(f"{name}_all.csv", [])
            if len(cand) != 1:
                report["problems"].append(f"{name}: {len(cand)} files named {name}_all.csv")
                continue
            header, body = _read_csv(zf, cand[0])
            col = _col(header, "Event")
            if col is None:
                report["problems"].append(f"{name}: no Event column in {header}")
                continue
            labels = [r[col].strip() if col < len(r) else "" for r in body]
            n_na = sum(1 for v in labels if v in NA_TOKENS)
            report["individuals"][name] = {"file": cand[0].filename, "header": header,
                                           "rows": len(labels), "expected": expected, "missing": n_na}
            if len(labels) != expected:
                report["problems"].append(f"{name}: {len(labels)} rows, expected {expected}")
            seqs[name] = labels
    return seqs, report


def encode(labels):
    cats = sorted({v for v in labels if v not in NA_TOKENS})
    idx = {c: i for i, c in enumerate(cats)}
    return np.array([idx.get(v, -1) for v in labels], dtype=np.int64), cats


def load_their_mi(data_dir):
    """The authors' own MI tables (MI Estimation/2012/<name>[_condensed]_estimated_MI_perm_1000.csv)."""
    out = {}
    path = os.path.join(data_dir, "MI Estimation.zip")
    if not os.path.exists(path):
        return out
    with zipfile.ZipFile(path) as zf:
        members = _zip_members(zf)
        for name in INDIVIDUALS:
            for version, fn in (("full", f"{name}_estimated_mi_perm_1000.csv"),
                                ("condensed", f"{name}_condensed_estimated_mi_perm_1000.csv")):
                cand = members.get(fn, [])
                if len(cand) != 1:
                    continue
                header, body = _read_csv(zf, cand[0])
                ci, cl, cx = _col(header, "MInfo"), _col(header, "Adjusted_MI_Lowerbound"), _col(header, "index")

                def num(r, c):
                    try:
                        return float(r[c])
                    except (TypeError, ValueError, IndexError):
                        return float("nan")
                if ci is None:
                    continue
                d = [int(num(r, cx)) if cx is not None and np.isfinite(num(r, cx)) else i + 1
                     for i, r in enumerate(body)]
                out[(name, version)] = {"d": d, "mi": [num(r, ci) for r in body],
                                        "lower": [num(r, cl) for r in body] if cl is not None else None}
    return out


def compare_their(ours_curve, theirs):
    mi = ours_curve["mi"]
    diffs = [abs(mi[d - 1] - v) for d, v in zip(theirs["d"], theirs["mi"])
             if 1 <= d <= len(mi) and np.isfinite(v) and np.isfinite(mi[d - 1])]
    their_index = None
    if theirs["lower"] is not None:
        neg = [d for d, v in zip(theirs["d"], theirs["lower"]) if np.isfinite(v) and v < 0]
        their_index = min(neg) if neg else 100
    return {"n_compared": len(diffs), "max_abs_diff": max(diffs) if diffs else None,
            "match_1e-6": bool(diffs) and max(diffs) < 1e-6, "their_index_max": their_index}


# ----------------------------------------------------------------------------- grading

def their_upper(x):
    """Upper end of the authors' exactPoiCI (script 6) as written: 0.5 * qchisq(0.975, 2X)."""
    from scipy.stats import chi2
    return float(0.5 * chi2.ppf(0.975, 2.0 * x))


def c3_p(real_margin, world_margins):
    if real_margin is None or not np.isfinite(real_margin):
        return 1.0
    m = [(-np.inf if v is None else v) for v in world_margins]
    return (1 + sum(1 for v in m if v >= real_margin)) / (len(m) + 1)


def verdict(control_median, n2_median, n_c3_sig):
    if control_median < CONTROL_OK:
        return "CONTROL_FAILED"
    if n2_median >= UNSAFE:
        return "SIGNATURE_UNSAFE_AGAINST_HMM"
    if n2_median <= SAFE and n_c3_sig >= 4:
        return "HIERARCHY_SIGNATURE_SURVIVES_HMM"
    return "MIXED"


PRIORS = {"R1": 0.70, "R2": 0.35, "R3": 0.65, "R4": 0.55, "R5": 0.75, "R6": 0.15,
          "R7": 0.60, "R8": 0.30}


def grade(results, worlds, c0):
    """results[(name, version)] = {"real": analysis, "N1": [..], "N2": [..], "P": [..]}."""
    per = {}
    for (name, version), r in sorted(results.items()):
        row = {"real_index_max": r["real"]["index_max"], "real_range_pos": r["real"]["range_pos"]}
        for v in VARIANTS:
            row[v] = {"real_pl_win": r["real"][v]["pl_win"], "real_best": r["real"][v]["best"],
                      "real_margin": r["real"][v]["margin"], "real_n_points": r["real"][v]["n_points"]}
            for k in KINDS:
                ws = r[k]
                row[v][f"{k}_pl_win_rate"] = float(np.mean([w[v]["pl_win"] for w in ws])) if ws else None
                row[v][f"{k}_pl_win_hits"] = int(sum(w[v]["pl_win"] for w in ws))
            row[v]["C3_p"] = c3_p(r["real"][v]["margin"], [w[v]["margin"] for w in r["N2"]])
        n1 = np.array([w["index_max"] for w in r["N1"]], dtype=float)
        n2 = np.array([w["index_max"] for w in r["N2"]], dtype=float)
        up = their_upper(n1.mean())
        row["C4_upper"] = up
        row["C4_N1_mean_index"] = float(n1.mean())
        row["C4_share_N2"] = float(np.mean(n2 > up))
        row["C4_real_exceeds"] = bool(r["real"]["index_max"] > up)
        loo = [n1[j] > their_upper(np.delete(n1, j).mean()) for j in range(len(n1))]
        row["C4b_share_N1_self"] = float(np.mean(loo))
        for k in KINDS:
            row[f"{k}_median_index_max"] = float(np.median([w["index_max"] for w in r[k]]))
        per[f"{name}/{version}"] = row
    out = {"per_individual_version": per}
    for v in VARIANTS:
        rate = {k: float(np.median([row[v][f"{k}_pl_win_rate"] for row in per.values()])) for k in KINDS}
        full = {k: row for k, row in per.items() if k.endswith("/full")}
        n_sig = sum(1 for row in full.values() if row[v]["C3_p"] <= 0.05)
        c1 = sum(1 for row in full.values() if row[v]["real_pl_win"])
        out[v] = {"median_pl_win_rate": rate, "C1_real_full_pl_win": c1, "C3_sig_full": n_sig,
                  "verdict": verdict(rate["P"], rate["N2"], n_sig)}
    c4_med = float(np.median([row["C4_share_N2"] for row in per.values()]))
    c4b_med = float(np.median([row["C4b_share_N1_self"] for row in per.values()]))
    out["C4_median_share_N2"] = c4_med
    out["C4b_median_share_N1_self"] = c4b_med
    out["C4_real_exceeds_full"] = sum(1 for k, row in per.items() if k.endswith("/full") and row["C4_real_exceeds"])
    out["C0"] = c0
    c0_match = sum(1 for k, v in c0.items() if k.endswith("/full") and v.get("match_1e-6"))
    p = out["paper"]
    outcome = {"R1": p["C1_real_full_pl_win"] >= 6, "R2": p["median_pl_win_rate"]["N1"] >= 0.30,
               "R3": p["median_pl_win_rate"]["N2"] >= 0.30, "R4": c4_med >= 0.30,
               "R5": p["median_pl_win_rate"]["P"] >= 0.80,
               "R6": p["verdict"] == "HIERARCHY_SIGNATURE_SURVIVES_HMM",
               "R7": c0_match >= 6, "R8": c4b_med >= 0.30}
    briers = {k: (PRIORS[k] - (1.0 if outcome[k] else 0.0)) ** 2 for k in PRIORS}
    out["predictions"] = {k: {"prior": PRIORS[k], "outcome": outcome[k], "brier": briers[k]} for k in PRIORS}
    out["brier_mean"] = float(np.mean(list(briers.values())))
    hits = sum(row["paper"]["N2_pl_win_hits"] for row in per.values())
    out["ledger"] = {"chimp-mi-plwin-vs-hmm": {"worlds": worlds * len(per), "hits": int(hits)}}
    out["primary_verdict"] = p["verdict"]
    return out


# ----------------------------------------------------------------------------- run

def _hmm_task(task):
    name, K, obs, M, seed = task
    rng = np.random.default_rng(seed)
    r = hmm_fit(obs, M, K, rng)
    return name, K, r


def _world_task(task):
    kind, name, w, seed, n, M, model, real, nperm, dmax = task
    rng = np.random.default_rng(seed)
    if kind == "real":
        full = real
    elif kind == "N1":
        full = simulate_chain(rng, model["P"], n, model["start"])
    elif kind == "N2":
        full = hmm_simulate(rng, model["A"], model["B"], n)
    else:
        full = lin_tegmark_n(rng, M, n)
    out = {"kind": kind, "name": name, "world": w}
    for version, seq in (("full", full), ("condensed", condense(full))):
        prof = mi_profile(seq, rng, nperm, dmax)
        out[version] = analyse_profile(prof, keep_curve=(kind == "real"))
        out[version]["length"] = int(len(seq))
    return out


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run(data_dir, out_dir, worlds=WORLDS, nperm=NPERM, dmax=DMAX, workers=4):
    from multiprocessing import Pool
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    seqs, report = load_individuals(data_dir)
    with open(os.path.join(out_dir, "load_report.json"), "w") as fh:
        json.dump(clean(report), fh, indent=1)
    if report["problems"]:
        print("LOADER STOP (nothing graded):", report["problems"], flush=True)
        print(json.dumps(clean(report))[:4000], flush=True)
        return 2
    names = list(INDIVIDUALS)
    data, cats = {}, {}
    for name in names:
        data[name], cats[name] = encode(seqs[name])
        print(f"{name}: {len(data[name])} actions, {len(cats[name])} action types, "
              f"{int((data[name] < 0).sum())} missing", flush=True)
    models = {}
    with Pool(workers) as pool:
        tasks = []
        for ii, name in enumerate(names):
            obs = data[name][data[name] >= 0]
            for K in K_RANGE:
                tasks.append((name, K, obs, len(cats[name]), [SEED, ii, 7, K]))
        fits = pool.map(_hmm_task, tasks)
        hmm_by = {}
        for name, K, r in fits:
            hmm_by.setdefault(name, []).append(r)
        for name in names:
            best = min(hmm_by[name], key=lambda r: r["bic"])
            obs = data[name][data[name] >= 0]
            models[name] = {"N1": {"P": mle_transition(data[name], len(cats[name])), "start": int(obs[0])},
                            "N2": {"A": best["A"], "B": best["B"]},
                            "hmm_table": [{k: r[k] for k in ("K", "loglik", "bic", "n_params", "iterations")}
                                          for r in sorted(hmm_by[name], key=lambda r: r["K"])],
                            "hmm_K": best["K"]}
            print(f"{name}: HMM K by BIC = {best['K']} ({time.time() - t0:.0f} s)", flush=True)
        tasks = []
        for ii, name in enumerate(names):
            n, M = len(data[name]), len(cats[name])
            tasks.append(("real", name, 0, [SEED, ii, 9, 0], n, M, None, data[name], nperm, dmax))
            for ki, kind in enumerate(KINDS):
                for w in range(worlds):
                    tasks.append((kind, name, w, [SEED, ii, ki, w], n, M,
                                  models[name].get(kind), None, nperm, dmax))
        results = {}
        done = 0
        for res in pool.imap_unordered(_world_task, tasks, chunksize=2):
            for version in ("full", "condensed"):
                slot = results.setdefault((res["name"], version), {"real": None, "N1": [], "N2": [], "P": []})
                if res["kind"] == "real":
                    slot["real"] = res[version]
                else:
                    slot[res["kind"]].append(dict(res[version], world=res["world"]))
            done += 1
            if done % 100 == 0:
                print(f"{done}/{len(tasks)} worlds ({time.time() - t0:.0f} s)", flush=True)
    for slot in results.values():
        for k in KINDS:
            slot[k].sort(key=lambda w: w["world"])
    their = load_their_mi(data_dir)
    c0 = {}
    for (name, version), th in their.items():
        c0[f"{name}/{version}"] = compare_their(results[(name, version)]["real"]["curve"], th)
        c0[f"{name}/{version}"]["our_index_max"] = results[(name, version)]["real"]["index_max"]
    graded = grade(results, worlds, c0)
    graded.update({"stage": 3, "seed": SEED, "worlds": worlds, "nperm": nperm, "dmax": dmax,
                   "action_types": {n: len(cats[n]) for n in names},
                   "models": {n: {k: models[n][k] for k in ("hmm_K", "hmm_table")} for n in names},
                   "runtime_s": time.time() - t0})
    real = {f"{n}/{v}": results[(n, v)]["real"] for (n, v) in results}
    with open(os.path.join(out_dir, "chimp_results.json"), "w") as fh:
        json.dump(clean(graded), fh, indent=1)
    with open(os.path.join(out_dir, "chimp_real_curves.json"), "w") as fh:
        json.dump(clean(real), fh)
    worlds_rows = {f"{n}/{v}": {k: [{"index_max": w["index_max"], "range_pos": w["range_pos"],
                                     "length": w["length"],
                                     **{va: {x: w[va][x] for x in ("pl_win", "best", "margin", "n_points")}
                                        for va in VARIANTS}} for w in results[(n, v)][k]]
                                for k in KINDS} for (n, v) in results}
    with open(os.path.join(out_dir, "chimp_worlds.json"), "w") as fh:
        json.dump(clean(worlds_rows), fh)
    write_md(graded, os.path.join(out_dir, "RESULTS-CHIMP.md"))
    print("verdict (paper pipeline):", graded["primary_verdict"], flush=True)
    print("verdict (a2 pipeline):", graded["a2"]["verdict"], flush=True)
    return 0


def write_md(g, path):
    L = ["# Stage 3 results: chimpanzee action sequences", "",
         "MV2 of Munim, Inc. Made with AI agents; no human expert has checked these results. "
         "Generated by chimp_mi.py; plan AMENDMENT-2-STAGE3-CHIMP.md, code choices AMENDMENT-3-STAGE3-CODE.md.", "",
         f"Primary verdict (paper pipeline): **{g['primary_verdict']}**; secondary (a2 pipeline): "
         f"**{g['a2']['verdict']}**.", ""]
    for v in VARIANTS:
        r = g[v]
        L.append(f"- {v}: median PL-win rate N1 {r['median_pl_win_rate']['N1']:.3f}, N2 "
                 f"{r['median_pl_win_rate']['N2']:.3f}, P {r['median_pl_win_rate']['P']:.3f}; real full "
                 f"PL-win {r['C1_real_full_pl_win']} of 8; C3 p <= 0.05 in {r['C3_sig_full']} of 8")
    L += [f"- C4 median share of HMM worlds beyond the authors' Markov interval: {g['C4_median_share_N2']:.3f}",
          f"- C4b median share of Markov worlds beyond their own interval: {g['C4b_median_share_N1_self']:.3f}",
          f"- real full sequences beyond the interval: {g['C4_real_exceeds_full']} of 8",
          f"- mean Brier score {g['brier_mean']:.4f}", "",
          "| individual/version | real PL-win | N1 rate | N2 rate | P rate | C3 p | index real | C4 upper |",
          "|---|---|---|---|---|---|---|---|"]
    for k, row in g["per_individual_version"].items():
        p = row["paper"]
        L.append(f"| {k} | {p['real_pl_win']} | {p['N1_pl_win_rate']:.2f} | {p['N2_pl_win_rate']:.2f} | "
                 f"{p['P_pl_win_rate']:.2f} | {p['C3_p']:.3f} | {row['real_index_max']} | {row['C4_upper']:.1f} |")
    L += ["", "| prediction | prior | outcome | Brier |", "|---|---|---|---|"]
    for k, r in g["predictions"].items():
        L.append(f"| {k} | {r['prior']} | {r['outcome']} | {r['brier']:.4f} |")
    L += ["", "C0 (our MI against the authors' own MI tables):", ""]
    for k, r in sorted(g["C0"].items()):
        L.append(f"- {k}: compared {r['n_compared']} distances, max |diff| {r['max_abs_diff']}, "
                 f"their index {r['their_index_max']}, ours {r['our_index_max']}")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--data-dir", required=True)
    r = sub.add_parser("run")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--worlds", type=int, default=WORLDS)
    r.add_argument("--nperm", type=int, default=NPERM)
    r.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return fetch(a.data_dir)
    return run(a.data_dir, a.out_dir, a.worlds, a.nperm, DMAX, a.workers)


if __name__ == "__main__":
    sys.exit(main())

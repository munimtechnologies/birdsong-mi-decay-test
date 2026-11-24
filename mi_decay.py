# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 1: calibrate the mutual-information (MI) decay test that is read as
evidence of hierarchical song structure (Sainburg, Theilman, Thielk and Gentner 2019, Nat Commun
10:3636; Youngblood 2024, Proc R Soc B 291:20240250) in simulated worlds whose sequences come from
FINITE-STATE processes, which have no recursive hierarchy (see PLAN.md).

Pipeline reimplemented from the paper's methods and the public code of Sainburg et al.
(github.com/timsainb/ParallelsBirdsongLanguagePaper, parallelspaper/information_theory.py and
model_fitting.py):
  * MI(d) = H(a) + H(b) - H(a,b) over all pairs d apart inside each sequence, entropies by
    S = log2(N) - (1/N) sum_i N_i psi(N_i) (their mix of log2 and natural-log digamma is kept;
    it cancels in MI - shuffled MI because both use the same N at each distance),
  * baseline: the same MI after permuting each sequence, a new permutation for each distance,
  * sig(d) = MI(d) - baseline(d) for d = 1..100; points with sig <= 0 are dropped,
  * exponential a*exp(-b d)+c, power law a*d^b+c and composite a*exp(-b d)+p*d^q+c fitted on
    log residuals scaled by 1/log(1+d) with their bounds, compared by AICc (3, 3 and 5 parameters),
    relative probabilities from AICc differences.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

DISTANCES = np.arange(1, 101)
MODELS = ("exponential", "powerlaw", "composite")
N_PARAMS = {"exponential": 3, "powerlaw": 3, "composite": 5}
STRONG = 0.999
UNSAFE = 0.30
SAFE = 0.10

LOWER = {"exponential": [1e-10, 1e-10, 1e-10],
         "powerlaw": [1e-10, -np.inf, 1e-10],
         "composite": [1e-19, 1e-10, 1e-10, -np.inf, 1e-10]}
UPPER = {"exponential": [np.inf, np.inf, np.inf],
         "powerlaw": [np.inf, -1e-10, np.inf],
         "composite": [np.inf, np.inf, np.inf, -1e-10, np.inf]}


# ----------------------------------------------------------------------------- estimator

def digamma(x):
    """Digamma of positive values (recurrence up to 6, then the asymptotic series)."""
    x = np.array(x, dtype=float, ndmin=1)
    out = np.zeros_like(x)
    small = x < 6.0
    while np.any(small):
        out[small] -= 1.0 / x[small]
        x[small] += 1.0
        small = x < 6.0
    inv2 = 1.0 / (x * x)
    out += (np.log(x) - 0.5 / x
            - inv2 * (1.0 / 12 - inv2 * (1.0 / 120 - inv2 * (1.0 / 252
                                                             - inv2 * (1.0 / 240 - inv2 / 132)))))
    return out


def est_entropy_counts(counts):
    """Sainburg et al.'s estimator: log2(N) - (1/N) sum N_i psi(N_i)."""
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    n = c.sum()
    if n <= 0:
        return float("nan")
    return float(np.log2(n) - np.sum(c * digamma(c)) / n)


def mi_at(seqs, d, n_symbols):
    """Estimated MI between elements d apart, pairs pooled over sequences longer than d."""
    a_parts = [s[d:] for s in seqs if len(s) > d]
    if not a_parts:
        return float("nan")
    b_parts = [s[:-d] for s in seqs if len(s) > d]
    a = np.concatenate(a_parts)
    b = np.concatenate(b_parts)
    ca = np.unique(a, return_counts=True)[1]
    cb = np.unique(b, return_counts=True)[1]
    cab = np.unique(a * n_symbols + b, return_counts=True)[1]
    return est_entropy_counts(ca) + est_entropy_counts(cb) - est_entropy_counts(cab)


def as_int_seqs(seqs):
    out = [np.asarray(s, dtype=np.int64) for s in seqs]
    return [s for s in out if len(s) > 0]


def mi_curve(seqs, rng, distances=DISTANCES, n_shuff=1):
    """MI and shuffled baseline at each distance (one new within-sequence permutation per
    distance and repeat, as in sequential_mutual_information of Sainburg et al.)."""
    seqs = as_int_seqs(seqs)
    n_symbols = int(max(int(s.max()) for s in seqs)) + 1
    mi = np.array([mi_at(seqs, int(d), n_symbols) for d in distances])
    base = np.zeros(len(distances))
    for _ in range(n_shuff):
        base += np.array([mi_at([rng.permutation(s) for s in seqs], int(d), n_symbols)
                          for d in distances])
    base /= n_shuff
    return mi, base


# ----------------------------------------------------------------------------- model fits

def model_values(name, p, x):
    if name == "exponential":
        return p[0] * np.exp(-x * p[1]) + p[2]
    if name == "powerlaw":
        return p[0] * x ** p[1] + p[2]
    return p[0] * np.exp(-x * p[1]) + p[2] * x ** p[3] + p[4]


def starts(name, y):
    y0 = float(y[0])
    ylo = float(max(np.min(y), 1e-9))
    if name == "exponential":
        return [[a, b, c] for a in (0.5, y0) for b in (0.01, 0.1, 1.0) for c in (1e-5, ylo)]
    if name == "powerlaw":
        return [[a, q, c] for a in (0.5, y0) for q in (-0.1, -0.5, -1.5) for c in (1e-5, ylo)]
    return [[a, b, p, q, 1e-5] for a in (0.5, y0) for b in (0.05, 0.5)
            for p in (0.5, 0.1 * y0) for q in (-0.3, -1.0)]


def fit_model(name, x, y):
    """Best (rss, params) over the start grid, or None. Needs scipy."""
    from scipy.optimize import least_squares
    lb = np.array(LOWER[name], dtype=float)
    ub = np.array(UPPER[name], dtype=float)
    w = 1.0 / np.log1p(x)
    ly = np.log(y)

    def resid(p):
        m = np.maximum(model_values(name, p, x), 1e-300)
        return (ly - np.log(m)) * w

    best = None
    for x0 in starts(name, y):
        x0 = np.minimum(np.maximum(np.asarray(x0, dtype=float), lb), ub)
        try:
            r = least_squares(resid, x0, bounds=(lb, ub), method="trf", max_nfev=2000)
        except Exception:  # noqa: BLE001
            continue
        rss = float(np.sum(r.fun ** 2))
        if np.isfinite(rss) and (best is None or rss < best[0]):
            best = (rss, [float(v) for v in r.x])
    return best


def aicc(n, k, rss):
    if n - k - 1 <= 0:
        return float("nan")
    rss = max(float(rss), 1e-300)
    return n * math.log(rss / n) + 2 * k + 2.0 * k * (k + 1) / (n - k - 1)


def rel_probs(aiccs):
    names = [m for m in MODELS if m in aiccs and np.isfinite(aiccs[m])]
    if not names:
        return {}
    lo = min(aiccs[m] for m in names)
    raw = {m: math.exp(-(aiccs[m] - lo) / 2.0) for m in names}
    tot = sum(raw.values())
    return {m: raw[m] / tot for m in names}


def fit_curve(distances, sig):
    d = np.asarray(distances, dtype=float)
    s = np.asarray(sig, dtype=float)
    keep = np.isfinite(s) & (s > 0)
    x, y = d[keep], s[keep]
    out = {"n_points": int(keep.sum()), "aicc": {}, "params": {}, "w": {}, "best": None,
           "fire_best": False, "fire_strong": False, "d_aicc_exp_minus_comp": None}
    if len(x) < N_PARAMS["composite"] + 2:
        return out
    with np.errstate(all="ignore"):
        for m in MODELS:
            res = fit_model(m, x, y)
            if res is None:
                continue
            out["aicc"][m] = aicc(len(x), N_PARAMS[m], res[0])
            out["params"][m] = res[1]
    w = rel_probs(out["aicc"])
    out["w"] = w
    if w:
        best = max(w, key=lambda m: w[m])
        out["best"] = best
        out["fire_best"] = best == "composite"
        out["fire_strong"] = bool(best == "composite" and w["composite"] > STRONG)
    if "exponential" in out["aicc"] and "composite" in out["aicc"]:
        out["d_aicc_exp_minus_comp"] = out["aicc"]["exponential"] - out["aicc"]["composite"]
    return out


# ----------------------------------------------------------------------------- generators

def random_sparse_rows(rng, k, ps=(0.7, 0.2, 0.1)):
    """k x k row-stochastic matrix; each row puts ps on distinct random states."""
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
        M = random_sparse_rows(rng, k, ps)
        if strongly_connected(M):
            return M
    raise RuntimeError("no irreducible matrix found")


def group_chain(rng, n_groups, group_size, lam):
    """First-order chain on syllables in phrase groups: with prob lam the next syllable follows
    the group's own sparse transitions, otherwise it is uniform over the other groups."""
    K = n_groups * group_size
    P = np.zeros((K, K))
    for g in range(n_groups):
        idx = np.arange(g * group_size, (g + 1) * group_size)
        others = np.setdiff1d(np.arange(K), idx)
        P[np.ix_(idx, idx)] = lam * random_sparse_rows(rng, group_size)
        P[np.ix_(idx, others)] = (1.0 - lam) / len(others)
    return P


def simulate_chain(rng, P, n, start=None):
    K = P.shape[0]
    cum = np.cumsum(P, axis=1)
    cum[:, -1] = 1.0
    u = rng.random(n)
    s = np.empty(n, dtype=np.int64)
    s[0] = int(rng.integers(K)) if start is None else int(start)
    for t in range(1, n):
        s[t] = min(int(np.searchsorted(cum[s[t - 1]], u[t], side="right")), K - 1)
    return s


def lin_tegmark_sequence(rng, M, depth, q=2):
    """Recursive hierarchical model (Lin and Tegmark; Sainburg et al.'s gen_seq_hierarchical):
    every symbol is replaced by q children drawn from its row of M, depth times."""
    k = M.shape[0]
    cum = np.cumsum(M, axis=1)
    cum[:, -1] = 1.0
    seq = np.array([int(rng.integers(k))], dtype=np.int64)
    for _ in range(depth):
        u = rng.random((len(seq), q))
        child = (u[:, :, None] >= cum[seq][:, None, :]).sum(axis=2)
        seq = np.minimum(child, k - 1).reshape(-1).astype(np.int64)
    return seq


def world_w0(rng):
    P = balanced_matrix(rng, 12)
    return [simulate_chain(rng, P, 4000) for _ in range(30)]


def world_w1(rng):
    P = group_chain(rng, 3, 4, 0.9)
    return [simulate_chain(rng, P, 4000) for _ in range(30)]


def world_w2(rng):
    seqs = []
    for b in range(30):
        P = group_chain(rng, 3, 4, float(rng.uniform(0.5, 0.99)))
        seqs.append(simulate_chain(rng, P, 4000) + 12 * b)
    return seqs


def world_w3(rng, n_days=30, n_bouts=50, n_types=3, type_size=6, persist=0.8):
    mats = [balanced_matrix(rng, type_size) for _ in range(n_types)]
    days = []
    for _ in range(n_days):
        parts = []
        t = int(rng.integers(n_types))
        for b in range(n_bouts):
            if b > 0 and rng.random() >= persist:
                t = int((t + 1 + rng.integers(n_types - 1)) % n_types)
            L = 20 + int(rng.poisson(60))
            s = simulate_chain(rng, mats[t], L, start=int(rng.integers(type_size)))
            parts.append(s + t * type_size)
        days.append(np.concatenate(parts))
    return days


def world_w4(rng, n_ind=331, n_syl=114, mean_songs=8.23, repeat=0.7, noise=0.05):
    p = 1.0 / np.arange(1, n_syl + 1)
    p /= p.sum()
    seqs = []
    for _ in range(n_ind):
        m = int(rng.integers(1, 4))
        rep = [rng.choice(n_syl, size=int(rng.integers(6, 32)), p=p) for _ in range(m)]
        n_songs = 1 + int(rng.poisson(mean_songs - 1))
        k = int(rng.integers(m))
        parts = []
        for j in range(n_songs):
            if j > 0 and m > 1 and rng.random() >= repeat:
                k = int((k + 1 + rng.integers(m - 1)) % m)
            song = rep[k].copy()
            flip = rng.random(len(song)) < noise
            if flip.any():
                song[flip] = rng.choice(n_syl, size=int(flip.sum()), p=p)
            parts.append(song)
        seqs.append(np.concatenate(parts).astype(np.int64))
    return seqs


def world_w5(rng):
    M = balanced_matrix(rng, 5)
    return [lin_tegmark_sequence(rng, M, 12) for _ in range(30)]


SCENARIOS = [
    ("W0_plain_markov", world_w0),
    ("W1_two_timescale_markov", world_w1),
    ("W2_pooled_individuals", world_w2),
    ("W3_bout_song_types", world_w3),
    ("W4_house_finch_design", world_w4),
    ("W5_recursive_hierarchy", world_w5),
]
NON_HIER = ("W1_two_timescale_markov", "W2_pooled_individuals", "W3_bout_song_types",
            "W4_house_finch_design")


def verdict(rates):
    """rates: scenario -> fire rate of the primary (strong composite) criterion."""
    nonhier = [rates[k] for k in NON_HIER]
    if rates["W0_plain_markov"] >= UNSAFE:
        v = "UNCALIBRATED_EVEN_PLAIN_MARKOV"
    elif max(nonhier) >= UNSAFE:
        v = "UNCALIBRATED_MULTI_TIMESCALE"
    elif max(nonhier + [rates["W0_plain_markov"]]) <= SAFE:
        v = "CALIBRATED"
    else:
        v = "MIXED"
    return {"verdict": v, "positive_control_ok": rates["W5_recursive_hierarchy"] >= 0.80}


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run_calibration(worlds, seed, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows, summary, curves = [], {}, {}
    show = [1, 2, 5, 10, 20, 50, 100]
    t0 = time.time()
    for si, (name, fn) in enumerate(SCENARIOS):
        fires_s = fires_b = 0
        dvals, curve_sum, curve_n = [], np.zeros(len(DISTANCES)), np.zeros(len(DISTANCES))
        for w in range(worlds):
            rng = np.random.default_rng([seed, si, w])
            seqs = fn(rng)
            mi, base = mi_curve(seqs, rng)
            sig = mi - base
            fit = fit_curve(DISTANCES, sig)
            fires_s += int(fit["fire_strong"])
            fires_b += int(fit["fire_best"])
            if fit["d_aicc_exp_minus_comp"] is not None:
                dvals.append(fit["d_aicc_exp_minus_comp"])
            ok = np.isfinite(sig)
            curve_sum[ok] += sig[ok]
            curve_n[ok] += 1
            rows.append({"scenario": name, "world": w, "n_symbols_total": int(sum(len(s) for s in seqs)),
                         "n_sequences": len(seqs), "sig_at": {str(d): float(sig[d - 1]) for d in show},
                         **{k: fit[k] for k in ("n_points", "aicc", "w", "best", "fire_best",
                                                "fire_strong", "d_aicc_exp_minus_comp")}})
        mean_curve = np.where(curve_n > 0, curve_sum / np.maximum(curve_n, 1), np.nan)
        curves[name] = [[int(d), float(v)] for d, v in zip(DISTANCES, mean_curve)]
        summary[name] = {"worlds": worlds, "fires_strong": fires_s, "fire_rate_strong": fires_s / worlds,
                         "fires_best": fires_b, "fire_rate_best": fires_b / worlds,
                         "median_d_aicc_exp_minus_comp": float(np.median(dvals)) if dvals else None}
        print("%s: strong %d/%d, best %d/%d (%.0f s)" % (name, fires_s, worlds, fires_b, worlds,
                                                         time.time() - t0), flush=True)
    rates = {k: v["fire_rate_strong"] for k, v in summary.items()}
    rates_best = {k: v["fire_rate_best"] for k, v in summary.items()}
    result = {"stage": 1, "seed": seed, "worlds_per_scenario": worlds,
              "primary_criterion": "composite has the lowest AICc and relative probability > 0.999",
              "summary": summary, "grade_primary": verdict(rates),
              "grade_secondary_lowest_aicc": verdict(rates_best),
              "runtime_s": time.time() - t0}
    with open(os.path.join(out_dir, "calibration.json"), "w") as fh:
        json.dump(clean(result), fh, indent=1)
    with open(os.path.join(out_dir, "calibration_worlds.json"), "w") as fh:
        json.dump(clean(rows), fh)
    with open(os.path.join(out_dir, "calibration_curves.json"), "w") as fh:
        json.dump(clean(curves), fh)
    print(json.dumps(clean(result["grade_primary"])), flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("calibrate")
    c.add_argument("--out-dir", required=True)
    c.add_argument("--worlds", type=int, default=50)
    c.add_argument("--seed", type=int, default=20261124)
    a = ap.parse_args(argv)
    if a.cmd == "calibrate":
        run_calibration(a.worlds, a.seed, a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 4 (AMENDMENT-4-STAGE4-BENGALESE.md): does the composite
(exponential + power-law) MI-decay verdict that Sainburg et al. (2019, Nat Commun 10:3636) read as
hierarchy in Bengalese finch song exceed what a per-bird FINITE-MEMORY syntax model produces when
it is given the same design (birds, days, bouts, sample size)?

Data: Bengalese Finch Song Repository (Nicholson, Queen and Sober; figshare 4805749 version 9,
CC BY 4.0), hand-labelled syllables in crowsetta 'simple-seq' CSVs (onset_s, offset_s, label)
inside the .wav.csv.tar.gz archives. The archives are STREAMED: only the CSV members are kept,
the audio is never written to disk. File ids and md5s are taken from figshare's own API at run
time and every archive's md5 is checked against figshare's computed_md5.

Tests (registered):
  T4a  composite verdict (stage-1 code, mi_decay.py pinned by git blob) on the real curve, all
       bird-day sequences pooled as in the paper.
  T4b  the same after permuting the ORDER of bouts (files) within each bird-day.
  T4c  per-bird k-gram (variable memory k = 1..8 chosen by 5-fold held-out log-likelihood,
       Witten-Bell smoothing, START/END tokens) generating every bout independently; days keep
       their real number of bouts. A k-gram is a finite-state process.
  Self-check of T4c on synthetic finch-shaped data (S0 in-class, S1 out-of-class finite-state,
  S3 cross-bout persistence, S4 within-bout recursive hierarchy) before any grade counts.
The MI curve, the fits and the firing rule are imported from the registered stage-1 core.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tarfile
import time
import urllib.request
import zipfile

import numpy as np

ARTICLE_API = "https://api.figshare.com/v2/articles/4805749/versions/9"
VIREO_ZIP = "https://ndownloader.figshare.com/files/4793170"   # Textgrids.zip, figshare 3081814 v1
VIREO_MD5 = "443655cbd17ee4134cd63c4d427a91f4"
TAR_RE = re.compile(r"^sober\.repo1\.([A-Za-z0-9]+)\.(\d{6})\.wav\.csv\.tar\.gz$")
N_TARS = 18
BIRDS = ("bl26lb16", "gr41rd51", "gy6or6", "or60yw70")
COLS = ("onset_s", "offset_s", "label")
UA = {"User-Agent": "mv2-research-job/1.0"}

START, END = -1, -2
K_GRID = tuple(range(1, 9))
N_FOLDS = 5
N_PERM = 100
N_SURR = 100
PCTL = 95.0
FIRE_MAJORITY = 0.5
MIN_NULL = 20
MAX_FALSE = 0.125
P_ORDER = 0.05
MIN_SYLLABLES = 10000
MIN_DAYS = 2
MIN_BOUTS = 20
CORE_FALLBACK = "/data/core"


def _core():
    try:
        import mi_decay  # noqa: F401
    except ImportError:
        if os.path.isdir(CORE_FALLBACK) and CORE_FALLBACK not in sys.path:
            sys.path.insert(0, CORE_FALLBACK)
        import mi_decay  # noqa: F401
    return sys.modules["mi_decay"]


# ------------------------------------------------------------------ loader (pure parts)

def parse_tar_name(name):
    """'sober.repo1.<bird>.<mmddyy>.wav.csv.tar.gz' -> (bird, 'yymmdd') or None."""
    m = TAR_RE.match(name)
    if not m:
        return None
    d = m.group(2)
    return m.group(1), d[4:6] + d[0:2] + d[2:4]


def is_csv_member(name):
    base = name.replace("\\", "/").split("/")[-1]
    return (base.lower().endswith(".csv") and not base.startswith("._")
            and "__MACOSX" not in name)


def parse_simple_seq(text):
    """Labels of one simple-seq CSV in onset order (stable; rows with a bad onset keep file
    order after the rest). Returns (labels, columns); labels is None if a column is missing."""
    rd = csv.DictReader(io.StringIO(text))
    cols = [(c or "").strip() for c in (rd.fieldnames or [])]
    if not set(COLS) <= set(cols):
        return None, cols
    rows = []
    for r in rd:
        r = {(k or "").strip(): v for k, v in r.items()}
        v = r.get("label")
        lab = v.strip() if isinstance(v, str) else ""
        if not lab:
            continue
        try:
            on = float(r.get("onset_s"))
        except (TypeError, ValueError):
            on = float("nan")
        rows.append((on, lab))
    order = sorted(range(len(rows)),
                   key=lambda i: (math.isnan(rows[i][0]),
                                  0.0 if math.isnan(rows[i][0]) else rows[i][0], i))
    return [rows[i][1] for i in order], cols


def build_days(per_tar):
    """per_tar: {tar_name: {member: csv_text}} -> (days, report).
    days = [(bird, day, [bout_labels, ...]), ...] sorted by bird then day; bouts = annotated
    CSV files with >= 1 label, in member-name order."""
    days, rep = [], {"n_csv": 0, "n_bad_header": 0, "n_empty": 0, "bad_header_cols": [],
                     "unparsed_tars": []}
    for tname in sorted(per_tar):
        pt = parse_tar_name(tname)
        if pt is None:
            rep["unparsed_tars"].append(tname)
            continue
        bird, day = pt
        bouts = []
        for mem in sorted(per_tar[tname]):
            rep["n_csv"] += 1
            labels, cols = parse_simple_seq(per_tar[tname][mem])
            if labels is None:
                rep["n_bad_header"] += 1
                if len(rep["bad_header_cols"]) < 5:
                    rep["bad_header_cols"].append(cols[:10])
                continue
            if not labels:
                rep["n_empty"] += 1
                continue
            bouts.append(labels)
        days.append((bird, day, bouts))
    days.sort(key=lambda x: (x[0], x[1]))
    return days, rep


def encode_days(days):
    """Labels -> ints, one symbol per (bird, label) (labels mean nothing across birds)."""
    index, out = {}, []
    for bird, day, bouts in days:
        cb = []
        for b in bouts:
            arr = []
            for lab in b:
                key = (bird, lab)
                if key not in index:
                    index[key] = len(index)
                arr.append(index[key])
            if arr:
                cb.append(tuple(arr))
        out.append((bird, day, cb))
    return out, len(index)


def describe(cdays):
    birds = sorted({b for b, _, _ in cdays})
    per = {}
    for b in birds:
        ds = [x for x in cdays if x[0] == b and x[2]]
        bouts = [bt for x in ds for bt in x[2]]
        per[b] = {"days": len(ds), "bouts": len(bouts),
                  "syllables": int(sum(len(bt) for bt in bouts)),
                  "symbols": len({w for bt in bouts for w in bt}),
                  "mean_bout_len": (float(np.mean([len(bt) for bt in bouts])) if bouts else None)}
    return {"birds": per,
            "n_day_sequences": int(sum(1 for x in cdays if x[2])),
            "n_bouts": int(sum(len(x[2]) for x in cdays)),
            "n_syllables": int(sum(len(bt) for x in cdays for bt in x[2]))}


def loader_gate(md5_ok, n_tars, rep, desc):
    """Registered loader checks; returns list of failures (empty = pass)."""
    fails = []
    if n_tars != N_TARS:
        fails.append(f"archives {n_tars} != {N_TARS}")
    if not all(md5_ok.values()) or len(md5_ok) != N_TARS:
        fails.append("md5 mismatch or missing archive")
    if rep["n_csv"] == 0 or rep["n_bad_header"] > 0.01 * rep["n_csv"]:
        fails.append(f"bad headers {rep['n_bad_header']} of {rep['n_csv']}")
    if desc["n_syllables"] < MIN_SYLLABLES:
        fails.append(f"syllables {desc['n_syllables']} < {MIN_SYLLABLES}")
    for b in BIRDS:
        d = desc["birds"].get(b)
        if d is None or d["days"] < MIN_DAYS or d["bouts"] < MIN_BOUTS:
            fails.append(f"bird {b} too small: {d}")
    return fails


# ------------------------------------------------------------------ finite-memory null

class KGram:
    """k-th order Markov model of bouts with START padding and an END outcome, Witten-Bell
    interpolation down to an add-one unigram. Finite-state (states = last k tokens)."""

    def __init__(self, bouts, k, outcomes):
        self.k = int(k)
        self.out = list(outcomes) + [END]
        self.idx = {w: i for i, w in enumerate(self.out)}
        self.counts = {}
        for b in bouts:
            seq = [START] * self.k + list(b) + [END]
            for i in range(self.k, len(seq)):
                w = seq[i]
                for j in range(self.k + 1):
                    h = tuple(seq[i - j:i])
                    d = self.counts.get(h)
                    if d is None:
                        d = self.counts[h] = {}
                    d[w] = d.get(w, 0) + 1
        self._p = {}
        self._c = {}

    def start(self):
        return (START,) * self.k

    def push(self, h, w):
        return (h[1:] + (w,)) if self.k else ()

    def dist(self, h):
        p = self._p.get(h)
        if p is not None:
            return p
        p = np.ones(len(self.out))
        for w, c in self.counts.get((), {}).items():
            p[self.idx[w]] += c
        p = p / p.sum()
        for j in range(1, self.k + 1):
            d = self.counts.get(h[self.k - j:])
            if not d:
                continue
            n = sum(d.values())
            t = len(d)
            q = t * p
            for w, c in d.items():
                q[self.idx[w]] += c
            p = q / (n + t)
        self._p[h] = p
        return p

    def loglik(self, bouts):
        tot, n = 0.0, 0
        for b in bouts:
            h = self.start()
            for w in list(b) + [END]:
                tot += math.log(self.dist(h)[self.idx[w]])
                n += 1
                h = self.push(h, w)
        return tot, n

    def sample_bout(self, rng, cap):
        out, h = [], self.start()
        last = len(self.out) - 1
        while len(out) < cap:
            c = self._c.get(h)
            if c is None:
                c = self._c[h] = np.cumsum(self.dist(h))
            i = min(int(np.searchsorted(c, rng.random(), side="right")), last)
            w = self.out[i]
            if w == END:
                break
            out.append(w)
            h = self.push(h, w)
        return out

    def sample_nonempty(self, rng, cap, tries=50):
        b = []
        for _ in range(tries):
            b = self.sample_bout(rng, cap)
            if b:
                break
        return b


def choose_k(bouts, outcomes, k_grid=K_GRID, folds=N_FOLDS):
    """k with the highest 5-fold held-out log-likelihood (bout i in fold i % folds);
    ties go to the smaller k."""
    scores = {}
    for k in k_grid:
        tot = 0.0
        for f in range(folds):
            train = [b for i, b in enumerate(bouts) if i % folds != f]
            test = [b for i, b in enumerate(bouts) if i % folds == f]
            if not train or not test:
                continue
            tot += KGram(train, k, outcomes).loglik(test)[0]
        scores[k] = tot
    best = max(k_grid, key=lambda k: (scores[k], -k))
    return best, scores


def fit_models(cdays, k_grid=K_GRID):
    models, info, caps = {}, {}, {}
    for b in sorted({x[0] for x in cdays}):
        bouts = [bt for x in cdays if x[0] == b for bt in x[2]]
        if not bouts:
            continue
        vocab = sorted({w for bt in bouts for w in bt})
        k, scores = choose_k(bouts, vocab, k_grid)
        models[b] = KGram(bouts, k, vocab)
        caps[b] = 2 * max(len(bt) for bt in bouts)
        info[b] = {"k": k, "heldout_loglik": {str(kk): v for kk, v in scores.items()}}
    return models, info, caps


def day_sequences(cdays):
    seqs = [np.asarray([w for bt in bouts for w in bt], dtype=np.int64) for _, _, bouts in cdays]
    return [s for s in seqs if len(s) > 0]


def permute_bouts(rng, cdays):
    out = []
    for b, d, bouts in cdays:
        idx = rng.permutation(len(bouts))
        out.append((b, d, [bouts[int(i)] for i in idx]))
    return out


def kgram_surrogate(rng, cdays, models, caps):
    out = []
    for b, d, bouts in cdays:
        out.append((b, d, [tuple(models[b].sample_nonempty(rng, caps[b])) for _ in bouts]))
    return out


# ------------------------------------------------------------------ grading (pure)

def finite(xs):
    return np.asarray([float(x) for x in xs if x is not None and math.isfinite(float(x))],
                      dtype=float)


def upper_p(real, null):
    g = finite(null)
    if real is None or not math.isfinite(float(real)) or len(g) == 0:
        return None
    return float((1 + np.sum(g >= float(real))) / (1 + len(g)))


def summarize_null(real_gap, fires, gaps):
    fires = [bool(f) for f in fires]
    g = finite(gaps)
    return {"n": len(fires), "fire_rate": (float(np.mean(fires)) if fires else None),
            "n_finite_gap": int(len(g)),
            "gap_p95": (float(np.percentile(g, PCTL)) if len(g) else None),
            "p_upper": upper_p(real_gap, gaps)}


def grade_null(real_gap, fires, gaps):
    """Same rule as stage 2 (T2c): EXCEEDS_FINITE_STATE if the real exp-minus-composite AICc gap
    is above the null's 95th percentile; FINITE_STATE_SUFFICES if the null fires in >= 50% and the
    real gap is below it; else UNRESOLVED (also with < 20 finite null gaps)."""
    out = summarize_null(real_gap, fires, gaps)
    out["real_gap"] = None if real_gap is None else float(real_gap)
    out["grade"] = "UNRESOLVED"
    if real_gap is None or not math.isfinite(float(real_gap)) or out["n_finite_gap"] < MIN_NULL:
        return out
    rate = out["fire_rate"] if out["fire_rate"] is not None else 0.0
    if real_gap > out["gap_p95"]:
        out["grade"] = "EXCEEDS_FINITE_STATE"
    elif rate >= FIRE_MAJORITY and real_gap < out["gap_p95"]:
        out["grade"] = "FINITE_STATE_SUFFICES"
    return out


def final_grade(t4c_grade, t4b_p, calibrated):
    if not calibrated:
        return "UNRESOLVED_UNCALIBRATED"
    if t4c_grade == "FINITE_STATE_SUFFICES":
        return "FINITE_STATE_SUFFICES"
    if t4c_grade == "EXCEEDS_FINITE_STATE" and t4b_p is not None:
        return "CROSS_BOUT_ORDER" if t4b_p <= P_ORDER else "WITHIN_BOUT_EXCESS"
    return "UNRESOLVED"


def selfcheck_verdict(summary):
    ok = (summary["S0"]["t4c_exceeds"] <= MAX_FALSE and summary["S1"]["t4c_exceeds"] <= MAX_FALSE)
    return {"t4c_calibrated": bool(ok),
            "false_exceeds_S0": summary["S0"]["t4c_exceeds"],
            "false_exceeds_S1": summary["S1"]["t4c_exceeds"],
            "exceeds_S3_cross_bout": summary["S3"]["t4c_exceeds"],
            "cross_bout_label_S3": summary["S3"]["cross_bout_order"],
            "power_S4_within_bout_hierarchy": summary["S4"]["t4c_exceeds"]}


def jsonable(o):
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return [jsonable(v) for v in o.tolist()]
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return f if math.isfinite(f) else None
    return o


# ------------------------------------------------------------------ synthetic finches

def _rows3(rng, n_from, n_to):
    return [rng.choice(n_to, size=min(3, n_to), replace=False) for _ in range(n_from)]


P3 = np.array([0.7, 0.2, 0.1])


def _pick3(rng, choices):
    return int(choices[min(int(np.searchsorted(np.cumsum(P3[:len(choices)]), rng.random(),
                                               side="right")), len(choices) - 1)])


class Order2Bird:
    """S0: second-order chain over n syllables; context (x, y) with START = n; after the first
    syllable the bout ends with prob p_end before each further syllable."""

    def __init__(self, rng, n=10, p_end=0.04):
        self.n, self.p_end = n, p_end
        self.rows = _rows3(rng, (n + 1) * (n + 1), n)

    def bout(self, rng, cap=200):
        x = y = self.n
        out = []
        while len(out) < cap:
            if out and rng.random() < self.p_end:
                break
            w = _pick3(rng, self.rows[x * (self.n + 1) + y])
            out.append(w)
            x, y = y, w
        return out


class PhraseBird:
    """S1: finite-state phrase machine: 4 fixed phrases (2-4 syllables), each sung
    Geometric(0.35) times, first-order sparse phrase transitions, bout ends with prob 0.12
    after each phrase block."""

    def __init__(self, rng, n=10, n_phr=4, p_rep=0.35, p_end=0.12):
        self.phr = [tuple(int(v) for v in rng.integers(0, n, size=int(rng.integers(2, 5))))
                    for _ in range(n_phr)]
        self.rows = _rows3(rng, n_phr, n_phr)
        self.p_rep, self.p_end, self.n_phr = p_rep, p_end, n_phr

    def bout(self, rng, cap=300):
        out = []
        p = int(rng.integers(self.n_phr))
        while len(out) < cap:
            for _ in range(int(rng.geometric(self.p_rep))):
                out.extend(self.phr[p])
            if rng.random() < self.p_end:
                break
            p = _pick3(rng, self.rows[p])
        return out[:cap]


class TypedBird:
    """S3: three bout types, each its own Order2Bird over its own 6 syllables; the bout type
    persists from one bout to the next with prob 0.8 (finite-state, across bouts)."""

    def __init__(self, rng, n_types=3, n=6, persist=0.8):
        self.types = [Order2Bird(rng, n=n) for _ in range(n_types)]
        self.n, self.persist, self.t = n, persist, 0

    def new_day(self, rng):
        self.t = int(rng.integers(len(self.types)))

    def bout(self, rng, cap=200):
        if rng.random() >= self.persist:
            k = len(self.types)
            self.t = int((self.t + 1 + rng.integers(k - 1)) % k)
        return [w + self.t * self.n for w in self.types[self.t].bout(rng, cap)]


def _balanced(rng, k):
    for _ in range(1000):
        P = np.zeros((k, k))
        for i in range(k):
            P[i, rng.choice(k, size=min(3, k), replace=False)] = P3[:min(3, k)] / P3[:min(3, k)].sum()
        reach = (P > 0) | np.eye(k, dtype=bool)
        for _ in range(k):
            reach = reach | ((reach.astype(np.int64) @ reach.astype(np.int64)) > 0)
        if reach.all():
            return P
    raise RuntimeError("no irreducible matrix")


class TreeBird:
    """S4: every bout is a Lin-Tegmark recursive sequence (5 symbols, 2 children, depth 5,
    32 syllables): within-bout hierarchy, positive control."""

    def __init__(self, rng, n=5, depth=5):
        self.M = _balanced(rng, n)
        self.cum = np.cumsum(self.M, axis=1)
        self.cum[:, -1] = 1.0
        self.n, self.depth = n, depth

    def bout(self, rng, cap=200):
        seq = np.array([int(rng.integers(self.n))], dtype=np.int64)
        for _ in range(self.depth):
            u = rng.random((len(seq), 2))
            child = (u[:, :, None] >= self.cum[seq][:, None, :]).sum(axis=2)
            seq = np.minimum(child, self.n - 1).reshape(-1)
        return [int(v) for v in seq[:cap]]


WORLD_KINDS = {"S0": Order2Bird, "S1": PhraseBird, "S3": TypedBird, "S4": TreeBird}


def synth_days(rng, kind, n_birds=4, n_days=5, bouts_per_day=60):
    """Finch-shaped design: birds x days x bouts; symbols offset per bird."""
    out = []
    width = 18
    for b in range(n_birds):
        bird = WORLD_KINDS[kind](rng)
        for d in range(n_days):
            if hasattr(bird, "new_day"):
                bird.new_day(rng)
            bouts = []
            for _ in range(bouts_per_day):
                bt = bird.bout(rng)
                if bt:
                    bouts.append(tuple(int(w) + width * b for w in bt))
            out.append((f"b{b}", f"d{d}", bouts))
    return out


# ------------------------------------------------------------------ analysis

def curve_and_fit(seqs, rng):
    core = _core()
    mi, base = core.mi_curve(seqs, rng)
    sig = mi - base
    return sig, core.fit_curve(core.DISTANCES, sig)


def _gap(fit):
    g = fit.get("d_aicc_exp_minus_comp")
    return None if g is None else float(g)


def analyse(cdays, rng, n_perm, n_surr, tag=""):
    t0 = time.time()
    sig, fit = curve_and_fit(day_sequences(cdays), rng)
    real_gap = _gap(fit)
    models, info, caps = fit_models(cdays)
    res = {"T4a": {"fire_strong": bool(fit.get("fire_strong")), "fire_best": bool(fit.get("fire_best")),
                   "best": fit.get("best"), "gap": real_gap, "fit": fit, "sig": sig},
           "kgram": info}
    fires, gaps = [], []
    for _ in range(n_perm):
        _, f = curve_and_fit(day_sequences(permute_bouts(rng, cdays)), rng)
        fires.append(bool(f.get("fire_strong")))
        gaps.append(_gap(f))
    res["T4b"] = summarize_null(real_gap, fires, gaps)
    fires, gaps = [], []
    for _ in range(n_surr):
        _, f = curve_and_fit(day_sequences(kgram_surrogate(rng, cdays, models, caps)), rng)
        fires.append(bool(f.get("fire_strong")))
        gaps.append(_gap(f))
    res["T4c"] = grade_null(real_gap, fires, gaps)
    res["seconds"] = time.time() - t0
    print(f"{tag} T4a={res['T4a']['fire_strong']} T4b_p={res['T4b']['p_upper']} "
          f"T4c={res['T4c']['grade']} k={[v['k'] for v in info.values()]} "
          f"({res['seconds']:.0f}s)", flush=True)
    return res


def selfcheck(seed, n_worlds, n_perm, n_surr, out_dir):
    rows = []
    for wi, kind in enumerate(("S0", "S1", "S3", "S4")):
        for w in range(n_worlds):
            rng = np.random.default_rng([seed, wi, w])
            cdays = synth_days(rng, kind)
            r = analyse(cdays, rng, n_perm, n_surr, tag=f"{kind}#{w}")
            rows.append({"world": kind, "i": w, "t4a_fire": r["T4a"]["fire_strong"],
                         "real_gap": r["T4a"]["gap"], "t4b_p": r["T4b"]["p_upper"],
                         "t4b_fire_rate": r["T4b"]["fire_rate"], "t4c": r["T4c"]["grade"],
                         "t4c_p": r["T4c"]["p_upper"], "t4c_fire_rate": r["T4c"]["fire_rate"],
                         "k": [v["k"] for v in r["kgram"].values()],
                         "final": final_grade(r["T4c"]["grade"], r["T4b"]["p_upper"], True)})
    summary = {}
    for kind in ("S0", "S1", "S3", "S4"):
        rs = [x for x in rows if x["world"] == kind]
        n = max(1, len(rs))
        summary[kind] = {"worlds": len(rs),
                         "t4a_fire_rate": sum(x["t4a_fire"] for x in rs) / n,
                         "t4c_exceeds": sum(x["t4c"] == "EXCEEDS_FINITE_STATE" for x in rs) / n,
                         "t4c_suffices": sum(x["t4c"] == "FINITE_STATE_SUFFICES" for x in rs) / n,
                         "cross_bout_order": sum(x["final"] == "CROSS_BOUT_ORDER" for x in rs) / n}
    out = {"seed": seed, "n_worlds": n_worlds, "n_perm": n_perm, "n_surr": n_surr,
           "summary": summary, "verdict": selfcheck_verdict(summary)}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "selfcheck4.json"), "w") as fh:
        json.dump(jsonable(out), fh, indent=1)
    with open(os.path.join(out_dir, "selfcheck4_worlds.json"), "w") as fh:
        json.dump(jsonable(rows), fh, indent=1)
    print("SELFCHECK4", json.dumps(jsonable(out["verdict"])), flush=True)
    return out


# ------------------------------------------------------------------ network parts

class HashReader:
    def __init__(self, raw):
        self.raw, self.md5, self.n = raw, hashlib.md5(), 0

    def read(self, size=-1):
        b = self.raw.read() if size is None or size < 0 else self.raw.read(size)
        self.md5.update(b)
        self.n += len(b)
        return b


def read_csvs_from_stream(raw):
    """Read a .tar.gz from a file-like stream without seeking; keep only CSV members.
    Returns ({member: text}, md5 hex of every byte of the stream, number of bytes)."""
    hr = HashReader(raw)
    texts = {}
    tf = tarfile.open(fileobj=hr, mode="r|gz")
    for m in tf:
        if m.isfile() and is_csv_member(m.name):
            texts[m.name] = tf.extractfile(m).read().decode("utf-8", "replace")
    tf.close()
    while hr.read(1 << 20):
        pass
    return texts, hr.md5.hexdigest(), hr.n


def stream_csvs(url, tries=3):
    """Stream one .tar.gz from the web; see read_csvs_from_stream."""
    last = None
    for t in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as resp:
                return read_csvs_from_stream(resp)
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  try {t + 1} failed: {exc}", flush=True)
            time.sleep(30)
    raise RuntimeError(f"download failed: {last}")


def fetch_all(data_dir):
    meta = json.loads(urllib.request.urlopen(urllib.request.Request(ARTICLE_API, headers=UA),
                                             timeout=120).read().decode("utf-8"))
    files = [f for f in meta.get("files", []) if parse_tar_name(f.get("name", ""))]
    per_tar, md5_ok, fetch = {}, {}, {"license": (meta.get("license") or {}).get("name"),
                                      "version": meta.get("version"), "archives": []}
    root = os.path.join(data_dir, "bfsongrepo-csv")
    os.makedirs(root, exist_ok=True)
    for f in sorted(files, key=lambda x: x["name"]):
        name = f["name"]
        want = f.get("computed_md5") or f.get("supplied_md5")
        cache = os.path.join(root, name + ".json")
        if os.path.exists(cache):
            with open(cache) as fh:
                c = json.load(fh)
        else:
            t0 = time.time()
            texts, md5, nbytes = stream_csvs(f["download_url"])
            c = {"md5": md5, "bytes": nbytes, "texts": texts}
            if md5 == want:
                with open(cache, "w") as fh:
                    json.dump(c, fh)
            print(f"{name}: {len(texts)} csv, {nbytes} bytes, md5 ok={md5 == want} "
                  f"({time.time() - t0:.0f}s)", flush=True)
        md5_ok[name] = c["md5"] == want
        per_tar[name] = c["texts"]
        fetch["archives"].append({"name": name, "bytes": c["bytes"], "md5": c["md5"],
                                  "figshare_md5": want, "n_csv": len(c["texts"])})
    return per_tar, md5_ok, fetch


def vireo_manifest():
    """Structure only (no label sequences): names, tiers, interval counts, label counts."""
    raw = urllib.request.urlopen(urllib.request.Request(VIREO_ZIP, headers=UA), timeout=300).read()
    md5 = hashlib.md5(raw).hexdigest()
    z = zipfile.ZipFile(io.BytesIO(raw))
    names = [n for n in z.namelist() if n.lower().endswith(".textgrid") and "__MACOSX" not in n]
    tiers, n_int, n_lab, labset, enc = {}, 0, 0, set(), {}
    for n in names:
        b = z.read(n)
        if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
            t, e = b.decode("utf-16", "replace"), "utf-16"
        else:
            t, e = b.decode("utf-8", "replace"), "utf-8"
        enc[e] = enc.get(e, 0) + 1
        for tn in re.findall(r'name = "(.*?)"', t):
            tiers[tn] = tiers.get(tn, 0) + 1
        n_int += len(re.findall(r"intervals \[\d+\]", t))
        labs = [x for x in re.findall(r'text = "(.*?)"', t) if x.strip()]
        n_lab += len(labs)
        labset.update(x.strip() for x in labs)
    return {"zip_md5": md5, "zip_md5_ok": md5 == VIREO_MD5, "n_zip_members": len(z.namelist()),
            "n_textgrid": len(names), "first_names": sorted(names)[:8], "encodings": enc,
            "tier_names": tiers, "n_intervals": n_int, "n_nonempty_labels": n_lab,
            "n_distinct_labels": len(labset)}


def run_stage4(data_dir, out_dir, seed, n_perm, n_surr):
    os.makedirs(out_dir, exist_ok=True)
    try:
        vm = vireo_manifest()
    except Exception as exc:  # noqa: BLE001
        vm = {"error": str(exc)}
    with open(os.path.join(out_dir, "vireo_manifest.json"), "w") as fh:
        json.dump(jsonable(vm), fh, indent=1)
    per_tar, md5_ok, fetch = fetch_all(data_dir)
    days, rep = build_days(per_tar)
    cdays, n_sym = encode_days(days)
    desc = describe(cdays)
    fails = loader_gate(md5_ok, len(per_tar), rep, desc)
    report = {"fetch": fetch, "parse": rep, "describe": desc, "n_symbols": n_sym,
              "gate_failures": fails, "loader_ok": not fails}
    with open(os.path.join(out_dir, "load_report4.json"), "w") as fh:
        json.dump(jsonable(report), fh, indent=1)
    if fails:
        print("LOADER STOP", fails, flush=True)
        return None
    rng = np.random.default_rng(seed)
    res = analyse(cdays, rng, n_perm, n_surr, tag="BF")
    res["describe"] = desc
    with open(os.path.join(out_dir, "stage4_results.json"), "w") as fh:
        json.dump(jsonable(res), fh, indent=1)
    return res


def grade(out_dir):
    def load(name):
        p = os.path.join(out_dir, name)
        if not os.path.exists(p):
            return None
        with open(p) as fh:
            return json.load(fh)
    sc, lr, st = load("selfcheck4.json"), load("load_report4.json"), load("stage4_results.json")
    g = {"selfcheck": sc["verdict"] if sc else None}
    if lr is None or not lr.get("loader_ok"):
        g["grade"] = "LOADER_STOP"
    elif st is None or sc is None:
        g["grade"] = "UNRESOLVED_MISSING_OUTPUT"
    else:
        cal = bool(sc["verdict"]["t4c_calibrated"])
        g.update({"grade": final_grade(st["T4c"]["grade"], st["T4b"]["p_upper"], cal),
                  "B1_T4a_fires": st["T4a"]["fire_strong"],
                  "B2_k_ge3_in_3of4": sum(1 for v in st["kgram"].values() if v["k"] >= 3) >= 3,
                  "B3_selfcheck_calibrated": cal,
                  "B4_T4b_majority": (st["T4b"]["fire_rate"] is not None
                                      and st["T4b"]["fire_rate"] >= FIRE_MAJORITY),
                  "B6_S4_power_ge_half": sc["verdict"]["power_S4_within_bout_hierarchy"] >= 0.5,
                  "B7_S3_exceeds_ge_half": sc["verdict"]["exceeds_S3_cross_bout"] >= 0.5,
                  "T4c": st["T4c"], "T4b": st["T4b"]})
        g["B5_finite_state_suffices"] = g["grade"] == "FINITE_STATE_SUFFICES"
    with open(os.path.join(out_dir, "grade4.json"), "w") as fh:
        json.dump(jsonable(g), fh, indent=1)
    print("GRADE4", g["grade"], flush=True)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selfcheck")
    s.add_argument("--out-dir", required=True)
    s.add_argument("--worlds", type=int, default=12)
    s.add_argument("--perm", type=int, default=20)
    s.add_argument("--surr", type=int, default=40)
    s.add_argument("--seed", type=int, default=20261124)
    r = sub.add_parser("stage4")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--perm", type=int, default=N_PERM)
    r.add_argument("--surr", type=int, default=N_SURR)
    r.add_argument("--seed", type=int, default=20261124)
    gp = sub.add_parser("grade")
    gp.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "selfcheck":
        selfcheck(a.seed, a.worlds, a.perm, a.surr, a.out_dir)
    elif a.cmd == "stage4":
        run_stage4(a.data_dir, a.out_dir, a.seed, a.perm, a.surr)
    else:
        grade(a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

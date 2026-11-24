"""Stage-2 core of birdsong-mi-decay-test: T2a, T2b, T2c on per-bird song lists,
plus a self-check of T2c on synthetic house-finch-shaped data.

Apache-2.0. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents.

Written and registered (AMENDMENT-0-STAGE2.md) BEFORE any stage-1 result or any
house-finch data was opened. It assumes no column name: the stage-2 loader
(AMENDMENT-1, written from the manifest only) turns the authors' files into

    birds = [(bird_id, songs), ...]
    songs = list of songs in recording order; song = sequence of syllable labels

The MI curve, the fits and the firing rule are the registered stage-1 code
(mi_decay.py, git blob 83d578e3d03d130ac31f5cb4da5b3eb9bb077659), imported lazily
so the pure logic here can be unit-tested with numpy alone.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np

N_PERM = 100          # T2b song-order permutations (PLAN.md)
N_SURR = 100          # T2c surrogate datasets (PLAN.md)
PCTL = 95.0           # real gap compared with this percentile of the null gaps
FIRE_MAJORITY = 0.5   # T2c: surrogates must fire in >= 50%
MIN_NULL = 20         # fewer finite null gaps than this -> UNRESOLVED
TYPE_THR = 0.34       # song-type clustering: normalised edit distance <= this
MAX_FALSE = 0.125     # self-check: at most 2 of 16 null worlds may grade EXCEEDS
COVER_D = (1, 10, 25, 50, 100)
CORE_FALLBACK = "/data/core"


def _core():
    try:
        import mi_decay  # noqa: F401
    except ImportError:
        if os.path.isdir(CORE_FALLBACK) and CORE_FALLBACK not in sys.path:
            sys.path.insert(0, CORE_FALLBACK)
        import mi_decay  # noqa: F401
    return sys.modules["mi_decay"]


# ---------------------------------------------------------------- pure logic

def encode(birds):
    """Map syllable labels to 0..K-1 in order of first appearance.

    Returns (coded, labels); coded = [(bird_id, [tuple_of_ints, ...]), ...].
    Empty songs are dropped; birds keep their place even if they end up empty.
    """
    index = {}
    coded = []
    for bid, songs in birds:
        cs = []
        for song in songs:
            arr = []
            for lab in song:
                if lab not in index:
                    index[lab] = len(index)
                arr.append(index[lab])
            if arr:
                cs.append(tuple(arr))
        coded.append((bid, cs))
    return coded, list(index)


def join_songs(songs):
    if not songs:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate([np.asarray(s, dtype=np.int64) for s in songs])


def bird_sequences(coded):
    """One joined sequence per bird (Youngblood's design); empty birds dropped."""
    seqs = [join_songs(songs) for _, songs in coded]
    return [s for s in seqs if len(s) > 0]


def coverage(seqs, ds=COVER_D):
    """How many birds and lagged pairs contribute to the MI estimate at lag d."""
    lens = [len(s) for s in seqs]
    return {str(d): {"birds": int(sum(1 for n in lens if n > d)),
                     "pairs": int(sum(max(0, n - d) for n in lens))} for d in ds}


def permute_songs(rng, songs):
    idx = rng.permutation(len(songs))
    return [songs[int(i)] for i in idx]


def repeat_rate(items):
    """Share of consecutive pairs with items[i+1] == items[i]; nan if < 2 items."""
    n = len(items)
    if n < 2:
        return float("nan")
    rep = sum(1 for i in range(n - 1) if items[i + 1] == items[i])
    return rep / (n - 1)


def _repeat_or_redraw(rng, keys, rate):
    """Sequence of len(keys) items: repeat the previous one with prob `rate`,
    otherwise draw (with the observed multiplicities) among items != previous."""
    n = len(keys)
    if n == 0:
        return []
    r = rate if (rate is not None and math.isfinite(rate)) else 0.0
    out = [keys[int(rng.integers(n))]]
    for _ in range(n - 1):
        prev = out[-1]
        if rng.random() < r:
            out.append(prev)
            continue
        others = [k for k in keys if k != prev]
        out.append(others[int(rng.integers(len(others)))] if others else prev)
    return out


def surrogate_songs(rng, songs, rate=None):
    """T2c as registered: repeat-or-redraw at the bird's observed (exact) repeat rate."""
    keys = [tuple(s) for s in songs]
    r = repeat_rate(keys) if rate is None else rate
    return _repeat_or_redraw(rng, keys, r)


def edit_distance(a, b):
    a, b = tuple(a), tuple(b)
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def norm_dist(a, b):
    m = max(len(a), len(b))
    return 0.0 if m == 0 else edit_distance(a, b) / m


def song_types(songs, thr=TYPE_THR):
    """Single-linkage types within one bird: songs at normalised edit distance <= thr
    share a type. Types are numbered by first occurrence."""
    n = len(songs)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if norm_dist(songs[i], songs[j]) <= thr:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)
    lab = {}
    out = []
    for i in range(n):
        r = find(i)
        if r not in lab:
            lab[r] = len(lab)
        out.append(lab[r])
    return out


def surrogate_typed(rng, songs, thr=TYPE_THR, types=None):
    """T2c-type: repeat-or-redraw on song TYPES at the bird's observed type-repeat
    rate; each surrogate song is a random real rendition of its type.
    `types` (from song_types) may be passed in to avoid recomputing it."""
    if not songs:
        return []
    keys = [tuple(s) for s in songs]
    if types is None:
        types = song_types(keys, thr)
    by_type = {}
    for s, t in zip(keys, types):
        by_type.setdefault(t, []).append(s)
    seq = _repeat_or_redraw(rng, types, repeat_rate(types))
    return [by_type[t][int(rng.integers(len(by_type[t])))] for t in seq]


def finite(xs):
    return np.asarray([float(x) for x in xs
                       if x is not None and math.isfinite(float(x))], dtype=float)


def upper_p(real, null):
    g = finite(null)
    if real is None or not math.isfinite(float(real)) or len(g) == 0:
        return None
    return float((1 + np.sum(g >= float(real))) / (1 + len(g)))


def summarize_null(real_gap, fires, gaps):
    fires = [bool(f) for f in fires]
    g = finite(gaps)
    return {"n": len(fires),
            "fire_rate": (float(np.mean(fires)) if fires else None),
            "n_finite_gap": int(len(g)),
            "gap_p95": (float(np.percentile(g, PCTL)) if len(g) else None),
            "p_upper": upper_p(real_gap, gaps)}


def grade_t2(real_gap, surr_fires, surr_gaps):
    """Registered T2c rule (PLAN.md): EXCEEDS_FINITE_STATE if the real exp-minus-
    composite AICc gap is above the surrogates' 95th percentile; FINITE_STATE_SUFFICES
    if surrogates fire in >= 50% and the real gap is below it; else UNRESOLVED."""
    out = summarize_null(real_gap, surr_fires, surr_gaps)
    out["real_gap"] = None if real_gap is None else float(real_gap)
    out["grade"] = "UNRESOLVED"
    if (real_gap is None or not math.isfinite(float(real_gap))
            or out["n_finite_gap"] < MIN_NULL):
        return out
    p95 = out["gap_p95"]
    rate = out["fire_rate"] if out["fire_rate"] is not None else 0.0
    if real_gap > p95:
        out["grade"] = "EXCEEDS_FINITE_STATE"
    elif rate >= FIRE_MAJORITY and real_gap < p95:
        out["grade"] = "FINITE_STATE_SUFFICES"
    return out


def selfcheck_verdict(summary):
    """summary[world][key] = share of worlds graded EXCEEDS by that test."""
    c_t2c = (summary["F0"]["t2c_exceeds"] <= MAX_FALSE
             and summary["F1"]["t2c_exceeds"] <= MAX_FALSE)
    c_typ = (summary["F0"]["t2c_type_exceeds"] <= MAX_FALSE
             and summary["F1"]["t2c_type_exceeds"] <= MAX_FALSE)
    primary = "T2c" if c_t2c else ("T2c_type" if c_typ else None)
    return {"t2c_calibrated": bool(c_t2c), "t2c_type_calibrated": bool(c_typ),
            "stage2_primary": primary,
            "power_t2c": summary["F2"]["t2c_exceeds"],
            "power_t2c_type": summary["F2"]["t2c_type_exceeds"]}


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


# ---------------------------------------------------------- synthetic finches

def finch_world(rng, order="redraw", noise=0.0, n_ind=331, n_syl=114,
                mean_songs=8.23, repeat=0.7, k_range=(2, 5), len_range=(6, 12)):
    """House-finch-shaped birds (shape of Youngblood 2024: 331 birds, 114
    syllable types, 8.23 songs per bird). Each bird has k song types (random
    syllable strings). order='redraw': repeat the type with prob `repeat`, else
    another type; order='cycle': A B C A B C ... (finite-state, not
    repeat-or-redraw). noise: per-syllable substitution prob in each rendition."""
    birds = []
    for b in range(n_ind):
        k = int(rng.integers(k_range[0], k_range[1] + 1))
        types = []
        for _ in range(k):
            L = int(rng.integers(len_range[0], len_range[1] + 1))
            types.append(tuple(int(x) for x in rng.integers(0, n_syl, size=L)))
        n = 1 + int(rng.poisson(mean_songs - 1))
        if order == "cycle":
            start = int(rng.integers(k))
            seq = [(start + i) % k for i in range(n)]
        else:
            seq = [int(rng.integers(k))]
            for _ in range(n - 1):
                if rng.random() < repeat:
                    seq.append(seq[-1])
                else:
                    others = [t for t in range(k) if t != seq[-1]]
                    seq.append(others[int(rng.integers(len(others)))])
        songs = []
        for t in seq:
            s = list(types[t])
            if noise > 0:
                for i in range(len(s)):
                    if rng.random() < noise:
                        s[i] = int(rng.integers(0, n_syl))
            songs.append(tuple(s))
        birds.append((b, songs))
    return birds


# ------------------------------------------------------------ curve + tests

_NO_FIT = {"fire_strong": False, "fire_best": False, "d_aicc_exp_minus_comp": None,
           "best": None}


def curve_and_fit(seqs, rng):
    if not seqs:
        return None, dict(_NO_FIT)
    core = _core()
    mi, base = core.mi_curve(seqs, rng)
    sig = mi - base
    return sig, core.fit_curve(core.DISTANCES, sig)


def _gap(fit):
    g = fit.get("d_aicc_exp_minus_comp")
    return None if g is None else float(g)


def run_level(birds, rng, n_perm=N_PERM, n_surr=N_SURR, with_type=True, tag=""):
    coded, labels = encode(birds)
    seqs = bird_sequences(coded)
    t0 = time.time()
    sig, fit = curve_and_fit(seqs, rng)
    real_gap = _gap(fit)
    n_songs = [len(s) for _, s in coded]
    rates = [repeat_rate([tuple(x) for x in s]) for _, s in coded]
    btypes = [song_types(s) for _, s in coded]
    trates = [repeat_rate(t) for t in btypes]
    res = {"describe": {"n_birds": len(seqs), "n_songs": int(sum(n_songs)),
                        "n_syllables": int(sum(len(s) for s in seqs)),
                        "n_symbols": len(labels),
                        "mean_songs_per_bird": (float(np.mean(n_songs)) if n_songs else None),
                        "mean_exact_repeat_rate": (float(np.mean(finite(rates))) if len(finite(rates)) else None),
                        "mean_type_repeat_rate": (float(np.mean(finite(trates))) if len(finite(trates)) else None),
                        "coverage": coverage(seqs)},
           "T2a": {"fire_strong": bool(fit.get("fire_strong")),
                   "fire_best": bool(fit.get("fire_best")),
                   "best": fit.get("best"), "gap": real_gap, "fit": fit,
                   "sig": sig}}
    fires, gaps = [], []
    for _ in range(n_perm):
        pb = [(b, permute_songs(rng, s)) for b, s in coded]
        _, f = curve_and_fit(bird_sequences(pb), rng)
        fires.append(bool(f.get("fire_strong")))
        gaps.append(_gap(f))
    res["T2b"] = summarize_null(real_gap, fires, gaps)
    tests = [("T2c", lambda r, s, t: surrogate_songs(r, s))]
    if with_type:
        tests.append(("T2c_type", lambda r, s, t: surrogate_typed(r, s, types=t)))
    for name, maker in tests:
        fires, gaps = [], []
        for _ in range(n_surr):
            sb = [(b, maker(rng, s, t)) for (b, s), t in zip(coded, btypes)]
            _, f = curve_and_fit(bird_sequences(sb), rng)
            fires.append(bool(f.get("fire_strong")))
            gaps.append(_gap(f))
        res[name] = grade_t2(real_gap, fires, gaps)
    print(f"{tag} level done {time.time() - t0:.0f}s T2a={res['T2a']['fire_strong']} "
          + " ".join(f"{n}={res[n]['grade']}" for n, _ in tests), flush=True)
    return res


SC_WORLDS = (("F0", "redraw", 0.0), ("F1", "redraw", 0.05), ("F2", "cycle", 0.0))


def selfcheck(seed, n_worlds, n_surr, out_dir):
    rng = np.random.default_rng(seed)
    rows = []
    for name, order, noise in SC_WORLDS:
        for w in range(n_worlds):
            birds = finch_world(rng, order=order, noise=noise)
            r = run_level(birds, rng, n_perm=0, n_surr=n_surr, tag=f"{name}#{w}")
            rows.append({"world": name, "i": w,
                         "t2a_fire": r["T2a"]["fire_strong"], "real_gap": r["T2a"]["gap"],
                         "t2c": r["T2c"]["grade"], "t2c_p": r["T2c"]["p_upper"],
                         "t2c_fire_rate": r["T2c"]["fire_rate"],
                         "t2c_type": r["T2c_type"]["grade"], "t2c_type_p": r["T2c_type"]["p_upper"],
                         "t2c_type_fire_rate": r["T2c_type"]["fire_rate"],
                         "exact_repeat": r["describe"]["mean_exact_repeat_rate"],
                         "type_repeat": r["describe"]["mean_type_repeat_rate"]})
    summary = {}
    for name, _, _ in SC_WORLDS:
        rs = [x for x in rows if x["world"] == name]
        n = max(1, len(rs))
        summary[name] = {
            "worlds": len(rs),
            "t2a_fire_rate": sum(x["t2a_fire"] for x in rs) / n,
            "t2c_exceeds": sum(x["t2c"] == "EXCEEDS_FINITE_STATE" for x in rs) / n,
            "t2c_suffices": sum(x["t2c"] == "FINITE_STATE_SUFFICES" for x in rs) / n,
            "t2c_type_exceeds": sum(x["t2c_type"] == "EXCEEDS_FINITE_STATE" for x in rs) / n,
            "t2c_type_suffices": sum(x["t2c_type"] == "FINITE_STATE_SUFFICES" for x in rs) / n}
    out = {"seed": seed, "n_worlds": n_worlds, "n_surr": n_surr,
           "worlds": {n: {"order": o, "noise": z} for n, o, z in SC_WORLDS},
           "summary": summary, "verdict": selfcheck_verdict(summary)}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "selfcheck.json"), "w") as fh:
        json.dump(jsonable(out), fh, indent=1)
    with open(os.path.join(out_dir, "selfcheck_worlds.json"), "w") as fh:
        json.dump(jsonable(rows), fh, indent=1)
    print("SELFCHECK", json.dumps(jsonable(out["summary"])), json.dumps(jsonable(out["verdict"])), flush=True)
    return out


def load_levels(path):
    """{"levels": {"2": [{"bird": id, "songs": [[label, ...], ...]}, ...], ...}}"""
    with open(path) as fh:
        raw = json.load(fh)
    return {str(lv): [(b["bird"], b["songs"]) for b in birds]
            for lv, birds in raw["levels"].items()}


def run_stage2(levels, seed, out_dir, n_perm, n_surr, primary="T2c"):
    rng = np.random.default_rng(seed)
    res = {}
    for lv in sorted(levels):
        res[lv] = run_level(levels[lv], rng, n_perm=n_perm, n_surr=n_surr, tag=f"DS{lv}")
    p = res.get("2")
    out = {"seed": seed, "n_perm": n_perm, "n_surr": n_surr, "primary_test": primary,
           "levels": res}
    if p is not None:
        out["grade_primary"] = p[primary]["grade"] if primary in p else "UNRESOLVED"
        out["Q8_T2a_replicates"] = p["T2a"]["fire_strong"]
        out["Q9_T2b_majority"] = (p["T2b"]["fire_rate"] is not None
                                  and p["T2b"]["fire_rate"] >= FIRE_MAJORITY)
        out["Q10_finite_state_suffices"] = out["grade_primary"] == "FINITE_STATE_SUFFICES"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "stage2_results.json"), "w") as fh:
        json.dump(jsonable(out), fh, indent=1)
    print("STAGE2", out.get("grade_primary"), flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("selfcheck")
    s.add_argument("--out-dir", required=True)
    s.add_argument("--worlds", type=int, default=16)
    s.add_argument("--surr", type=int, default=50)
    s.add_argument("--seed", type=int, default=20261124)
    r = sub.add_parser("stage2")
    r.add_argument("--birds-json", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--perm", type=int, default=N_PERM)
    r.add_argument("--surr", type=int, default=N_SURR)
    r.add_argument("--seed", type=int, default=20261124)
    r.add_argument("--primary", default="T2c", choices=["T2c", "T2c_type"])
    a = ap.parse_args(argv)
    if a.cmd == "selfcheck":
        selfcheck(a.seed, a.worlds, a.surr, a.out_dir)
    else:
        run_stage2(load_levels(a.birds_json), a.seed, a.out_dir, a.perm, a.surr, a.primary)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name. MV2, Munim, Inc., mv2@munimtech.com
"""birdsong-mi-decay-test, stage 6B (AMENDMENT-6B-STAGE6B-SPEECH-SIZE.md): how much read English
does the composite (exponential + power-law) MI-decay verdict need before it fires?

D1: whole chapters of LibriSpeech train-clean-100 drawn at random until N phones, N = 200k, 500k,
1M, 2M, 5 draws each. D2: all of train-clean-100, plus per-speaker k-gram surrogates (40).
D3: all of train-clean-360 (run last; optional).

Uses the pinned registered code: speech_stage6.py (loader helpers, zip fetch), bf_stage4.py
(curve_and_fit, day_sequences, fit_models, kgram_surrogate, grade_null) and mi_decay.py (via
bf_stage4). Only numpy and the standard library are imported at module level.
"""
import argparse
import json
import math
import os
import sys
import time
import zipfile

import numpy as np

CORE_FALLBACK = "/data/core"
PRIMARY = "train-clean-100"
LARGE = "train-clean-360"
SIZES = (200000, 500000, 1000000, 2000000)
REPS = 5
FIRE_MIN = 3
N_SURR_FULL = 40
SEED = 20261128

# registered loader gate (primary subset)
MIN_SPEAKERS = 200
MIN_PHONES = 2500000
MAX_BAD_FRAC = 0.01
MIN_LABELS, MAX_LABELS = 30, 50

FORECASTS = (("Q1", 0.85), ("Q2", 0.35), ("Q3", 0.50), ("Q4", 0.60), ("Q5", 0.55),
             ("Q6", 0.30), ("Q7", 0.30), ("Q8", 0.80))


# ------------------------------------------------------------------ pure helpers

def sample_chapters(cdays, target, rng):
    """Whole chapters in a random order until the sample has at least `target` phones (all
    chapters if the pool is smaller). Returns (chapters in their original order, phones)."""
    order = rng.permutation(len(cdays))
    picked, total = [], 0
    for i in order:
        if total >= target:
            break
        picked.append(int(i))
        total += sum(len(u) for u in cdays[int(i)][2])
    picked.sort()
    return [cdays[i] for i in picked], total


def group_cdays(rows):
    """rows: [(speaker, chapter, utt_no, phone-code tuple)] -> cdays sorted by speaker then
    chapter (as integers), utterances in number order, empty utterances dropped."""
    groups = {}
    for spk, chap, no, t in rows:
        if t:
            groups.setdefault((spk, chap), []).append((no, t))
    out = []
    for key in sorted(groups, key=lambda k: (int(k[0]), int(k[1]))):
        out.append((key[0], key[1], [u for _, u in sorted(groups[key], key=lambda x: x[0])]))
    return out


def gate6b(md5_ok, rd, desc):
    fails = []
    if not md5_ok:
        fails.append("zip md5 does not match Zenodo's checksum")
    if rd["files"] == 0:
        fails.append(f"{PRIMARY}: no TextGrid files")
        return fails
    if rd["bad"] > MAX_BAD_FRAC * rd["files"]:
        fails.append(f"{PRIMARY}: {rd['bad']} of {rd['files']} files without a phone tier")
    if desc["speakers"] < MIN_SPEAKERS:
        fails.append(f"{PRIMARY}: speakers {desc['speakers']} < {MIN_SPEAKERS}")
    if desc["phones"] < MIN_PHONES:
        fails.append(f"{PRIMARY}: phones {desc['phones']} < {MIN_PHONES}")
    if not MIN_LABELS <= rd["n_labels"] <= MAX_LABELS:
        fails.append(f"{PRIMARY}: {rd['n_labels']} phone labels, outside {MIN_LABELS}-{MAX_LABELS}")
    return fails


def fire_counts(d1_rows):
    """{size: number of draws that fired} over the registered sizes (None if no draw)."""
    out = {}
    for n in SIZES:
        rows = [r for r in d1_rows if r["size"] == n]
        out[n] = sum(1 for r in rows if r["fire_strong"]) if rows else None
    return out


def headline6b(loader_ok, counts, d2_fire, d3_fire):
    """Registered headline. counts: {size: fires of 5}; d2_fire, d3_fire: bool or None."""
    if not loader_ok:
        return "LOADER_STOP"
    f200 = counts.get(SIZES[0])
    if f200 is None:
        return "UNRESOLVED_MISSING_OUTPUT"
    if f200 >= FIRE_MIN:
        return "FIRES_AT_BIRD_SIZE"
    if f200 == FIRE_MIN - 1:
        return "MIXED"
    larger = [counts.get(n) is not None and counts.get(n) >= FIRE_MIN for n in SIZES[1:]]
    if any(larger) or d2_fire is True or d3_fire is True:
        return "FIRES_ABOVE_BIRD_SIZE"
    return "NEVER_FIRES" if d3_fire is not None else "NEVER_FIRES_TO_TRAIN_CLEAN_100"


def smallest_firing(counts, d2_fire, d3_fire):
    for n in SIZES:
        if counts.get(n) is not None and counts[n] >= FIRE_MIN:
            return str(n)
    if d2_fire:
        return "all of " + PRIMARY
    if d3_fire:
        return "all of " + LARGE
    return None


def mean_gap(d1_rows, n):
    g = [r["gap"] for r in d1_rows if r["size"] == n and r["gap"] is not None
         and math.isfinite(r["gap"])]
    return (sum(g) / len(g)) if g else None


def forecast_outcomes(counts, d2_fire, d3_fire, head, d2_grade, d1_rows):
    m_lo, m_hi = mean_gap(d1_rows, SIZES[0]), mean_gap(d1_rows, SIZES[-1])
    return {
        "Q1": counts.get(SIZES[0]) is not None and counts[SIZES[0]] <= 1,
        "Q2": counts.get(1000000) is not None and counts[1000000] >= FIRE_MIN,
        "Q3": d2_fire is True,
        "Q4": None if d3_fire is None else bool(d3_fire),
        "Q5": head == "FIRES_ABOVE_BIRD_SIZE",
        "Q6": head in ("NEVER_FIRES", "NEVER_FIRES_TO_TRAIN_CLEAN_100"),
        "Q7": d2_grade == "EXCEEDS_FINITE_STATE",
        "Q8": (m_lo is not None and m_hi is not None and m_hi > m_lo),
    }


def brier(outcomes):
    s, n = 0.0, 0
    for q, p in FORECASTS:
        o = outcomes.get(q)
        if o is None:
            continue
        s += (p - (1.0 if o else 0.0)) ** 2
        n += 1
    return (s / n) if n else None


# ------------------------------------------------------------------ pinned code

def _s6():
    try:
        import speech_stage6  # noqa: F401
    except ImportError:
        if os.path.isdir(CORE_FALLBACK) and CORE_FALLBACK not in sys.path:
            sys.path.insert(0, CORE_FALLBACK)
        import speech_stage6  # noqa: F401
    return sys.modules["speech_stage6"]


def read_subset(zip_path, subset, s6):
    """-> (cdays, info). Phones are coded at once as small integers (first-seen order), so even
    train-clean-360 fits in memory."""
    code = {}
    rows = []
    files = bad = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            p = s6.parse_member_name(n)
            if p is None or p[0] != subset:
                continue
            files += 1
            ph = s6.utt_phones(s6.decode_bytes(z.read(n)))
            if ph is None:
                bad += 1
                continue
            if not ph:
                continue
            rows.append((p[1], p[2], p[3], tuple(code.setdefault(x, len(code)) for x in ph)))
    cdays = group_cdays(rows)
    return cdays, {"files": files, "bad": bad, "n_labels": len(code), "labels": sorted(code)}


def _dump(out_dir, name, obj, s6):
    with open(os.path.join(out_dir, name), "w") as fh:
        json.dump(s6.jsonable(obj), fh, indent=1)


def _verdict(bf, cdays, rng):
    sig, fit = bf.curve_and_fit(bf.day_sequences(cdays), rng)
    return {"fire_strong": bool(fit.get("fire_strong")), "best": fit.get("best"),
            "gap": bf._gap(fit), "n_points": fit.get("n_points"), "w": fit.get("w"),
            "aicc": fit.get("aicc"), "sig": sig}


def run(data_dir, out_dir, seed, reps, n_surr, skip_large):
    os.makedirs(out_dir, exist_ok=True)
    s6 = _s6()
    bf = s6._stage4()
    t0 = time.time()
    zip_path, info = s6.fetch_zip(data_dir)
    cdays, rd = read_subset(zip_path, PRIMARY, s6)
    desc = s6.describe6(cdays)
    fails = gate6b(info["md5_ok"], rd, desc)
    _dump(out_dir, "load_report6b.json", {"zenodo": info, PRIMARY: dict(rd, describe=desc),
                                          "gate_failures": fails, "loader_ok": not fails}, s6)
    print("LOADER", "OK" if not fails else f"STOP {fails}", desc, flush=True)
    if fails:
        return 0
    # D1: size series
    d1 = []
    for si, n in enumerate(SIZES):
        for r in range(reps):
            rng = np.random.default_rng([seed, 1, si, r])
            sub, tot = sample_chapters(cdays, n, rng)
            v = _verdict(bf, sub, rng)
            v.update({"size": n, "draw": r, "phones": tot, "chapters": len(sub),
                      "speakers": len({x[0] for x in sub})})
            d1.append(v)
            _dump(out_dir, "d1_sizes.json", d1, s6)
            print(f"D1 N={n} draw={r} phones={tot} fire={v['fire_strong']} best={v['best']} "
                  f"gap={v['gap']} ({time.time() - t0:.0f}s)", flush=True)
    # D2: all of the primary subset, then per-speaker k-gram surrogates
    rng = np.random.default_rng([seed, 2])
    real = _verdict(bf, cdays, rng)
    d2 = {"describe": desc, "real": real, "n_surr": n_surr}
    _dump(out_dir, "d2_full.json", d2, s6)
    print(f"D2 real fire={real['fire_strong']} best={real['best']} gap={real['gap']} "
          f"({time.time() - t0:.0f}s)", flush=True)
    models, kinfo, caps = bf.fit_models(cdays)
    d2["k"] = {s: x["k"] for s, x in kinfo.items()}
    fires, gaps = [], []
    for j in range(n_surr):
        sur = bf.kgram_surrogate(rng, cdays, models, caps)
        _, f = bf.curve_and_fit(bf.day_sequences(sur), rng)
        fires.append(bool(f.get("fire_strong")))
        gaps.append(bf._gap(f))
        del sur
        if (j + 1) % 5 == 0 or j + 1 == n_surr:
            d2["surrogate_fires"], d2["surrogate_gaps"] = fires, gaps
            d2["T6c"] = bf.grade_null(real["gap"], fires, gaps)
            _dump(out_dir, "d2_full.json", d2, s6)
            print(f"D2 surrogates {j + 1}/{n_surr} T6c={d2['T6c']['grade']} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    del models, cdays
    # D3: all of the large subset (optional, last)
    if not skip_large:
        c3, r3 = read_subset(zip_path, LARGE, s6)
        d3desc = s6.describe6(c3)
        rng = np.random.default_rng([seed, 3])
        v3 = _verdict(bf, c3, rng)
        _dump(out_dir, "d3_large.json", {"describe": d3desc, "files": r3["files"],
                                         "bad": r3["bad"], "n_labels": r3["n_labels"],
                                         "real": v3}, s6)
        print(f"D3 fire={v3['fire_strong']} best={v3['best']} gap={v3['gap']} "
              f"({time.time() - t0:.0f}s)", flush=True)
    return 0


def _load(out_dir, name):
    p = os.path.join(out_dir, name)
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        return json.load(fh)


def grade(out_dir):
    lr = _load(out_dir, "load_report6b.json")
    d1 = _load(out_dir, "d1_sizes.json") or []
    d2 = _load(out_dir, "d2_full.json")
    d3 = _load(out_dir, "d3_large.json")
    loader_ok = bool(lr and lr.get("loader_ok"))
    counts = fire_counts(d1)
    complete = all(sum(1 for r in d1 if r["size"] == n) == REPS for n in SIZES)
    d2_fire = None if d2 is None else bool(d2["real"]["fire_strong"])
    d3_fire = None if d3 is None else bool(d3["real"]["fire_strong"])
    head = headline6b(loader_ok, counts, d2_fire, d3_fire)
    d2_grade = None if (d2 is None or "T6c" not in d2) else d2["T6c"]["grade"]
    out = forecast_outcomes(counts, d2_fire, d3_fire, head, d2_grade, d1)
    g = {"headline": head, "d1_complete": complete,
         "fires_of_5": {str(n): counts[n] for n in SIZES},
         "mean_gap": {str(n): mean_gap(d1, n) for n in SIZES},
         "smallest_firing": smallest_firing(counts, d2_fire, d3_fire),
         "d2_fire": d2_fire, "d2_T6c": None if d2 is None else d2.get("T6c"),
         "d3_fire": d3_fire, "forecast_outcomes": out, "brier": brier(out)}
    with open(os.path.join(out_dir, "grade6b.json"), "w") as fh:
        json.dump(g, fh, indent=1)
    print("GRADE6B", head, json.dumps(g["fires_of_5"]), flush=True)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--data-dir", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--seed", type=int, default=SEED)
    r.add_argument("--reps", type=int, default=REPS)
    r.add_argument("--surr", type=int, default=N_SURR_FULL)
    r.add_argument("--skip-large", action="store_true")
    gp = sub.add_parser("grade")
    gp.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a.data_dir, a.out_dir, a.seed, a.reps, a.surr, a.skip_large)
    grade(a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

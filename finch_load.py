# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, AMENDMENT-1 (house-finch loader), step 2 of 2.

Turns the export of export_finch.R into the input of the registered stage-2 code
(mi_stage2.py, AMENDMENT-0):  {"levels": {"2": [{"bird": id, "songs": [[label, ...], ...]}, ...],
"3": ..., "4": ...}}  with level = the authors' deep-split level (cluster_2, cluster_3, cluster_4).

Rules (from the authors' public code, docs/index.Rmd of Youngblood 2024, read before any data):
  * a bird's sequence is its rows of processed_data$data in file order (the authors never sort);
  * a song is a maximal run of consecutive rows of one bird with the same `song` value, so the
    songs joined in order give back exactly the authors' sequence;
  * no row is dropped.

Check C0 (hard): the authors saved their raw MI curves (mi_data.RData, mi_raw = MI before the
shuffled baseline is subtracted, natural-log Grassberger estimator s = ln N - sum N_i psi(N_i)/N,
pairs never span two birds). This loader recomputes that curve from its own sequences at d = 1..100
and requires max |ours - theirs| < 1e-6 for deep split 2, 3 and 4 (their list items 1, 2, 3).
That proves the sequences (labels and order) are the authors' own before any test runs.

Stops (exit 1, nothing written for stage 2): missing export; any NA label; any song value that
comes back in a second, non-adjacent run within a bird; birds or songs more than 5% away from the
paper's 331 birds and 2,724 songs; C0 failure. Every stop writes load_report.json (counts and
check values only, no data values).

Usage: python finch_load.py <data_dir> <out_dir>
"""
import csv
import json
import math
import os
import sys

import numpy as np

LEVELS = ("2", "3", "4")
COLS = {"2": "c2", "3": "c3", "4": "c4"}
THEIR_INDEX = {"2": 1, "3": 2, "4": 3}
C0_TOL = 1e-6
C0_D = 100
EXPECT_BIRDS = 331
EXPECT_SONGS = 2724
REL_TOL = 0.05
NA = ("NA", "", "NaN")


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


def ent_nat(counts):
    """Youngblood's s_calc: ln N - (1/N) sum N_i psi(N_i), over non-zero counts."""
    c = np.asarray(counts, dtype=float)
    c = c[c > 0]
    n = c.sum()
    if n <= 0:
        return float("nan")
    return float(math.log(n) - np.sum(c * digamma(c)) / n)


def mi_nat(seqs, d):
    """Raw MI at lag d over all pairs d apart inside each sequence (birds with length > d)."""
    xs, ys = [], []
    for s in seqs:
        s = np.asarray(s, dtype=np.int64)
        if len(s) > d:
            xs.append(s[:-d])
            ys.append(s[d:])
    if not xs:
        return float("nan")
    x = np.concatenate(xs)
    y = np.concatenate(ys)
    k = int(max(int(x.max()), int(y.max()))) + 1
    cx = np.bincount(x, minlength=k)
    cy = np.bincount(y, minlength=k)
    cxy = np.bincount(x * k + y)
    return ent_nat(cx) + ent_nat(cy) - ent_nat(cxy)


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(rd)
        return [dict(zip(header, r)) for r in rd if r]


def build_levels(rows):
    """Birds in order of first appearance; each bird's rows in file order; songs = runs."""
    order, by_ind = [], {}
    for r in rows:
        ind = r["individual"]
        if ind not in by_ind:
            by_ind[ind] = []
            order.append(ind)
        by_ind[ind].append(r)
    n_songs, n_split = 0, 0
    for ind in order:
        runs = []
        for r in by_ind[ind]:
            if not runs or runs[-1] != r["song"]:
                runs.append(r["song"])
        n_songs += len(runs)
        n_split += len(runs) - len(set(runs))
    levels, stats = {}, {"n_rows": len(rows), "n_birds": len(order), "n_songs": n_songs,
                         "n_song_values_split": n_split, "levels": {}}
    for lv in LEVELS:
        col = COLS[lv]
        birds, labels, n_na = [], set(), 0
        for ind in order:
            songs, prev = [], None
            for i, r in enumerate(by_ind[ind]):
                if i == 0 or r["song"] != prev:
                    songs.append([])
                    prev = r["song"]
                lab = r[col]
                if lab in NA:
                    n_na += 1
                labels.add(lab)
                songs[-1].append(lab)
            birds.append({"bird": ind, "songs": songs})
        levels[lv] = birds
        stats["levels"][lv] = {"n_symbols": len(labels), "n_na": n_na}
    return levels, stats


def int_sequences(birds):
    """Joined songs per bird, labels coded 0..K-1 by first appearance."""
    index, seqs = {}, []
    for b in birds:
        arr = []
        for song in b["songs"]:
            for lab in song:
                if lab not in index:
                    index[lab] = len(index)
                arr.append(index[lab])
        if arr:
            seqs.append(np.asarray(arr, dtype=np.int64))
    return seqs


def to_float(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return f


def read_their(data_dir, g):
    path = os.path.join(data_dir, "their_mi_%d.tsv" % g)
    if not os.path.exists(path):
        return None
    rows = read_rows(path)
    return {int(to_float(r["dist"])): to_float(r["mi_raw"]) for r in rows
            if math.isfinite(to_float(r["dist"]))}


def c0_check(levels, theirs, max_d=C0_D, tol=C0_TOL):
    """theirs: {g: {dist: mi_raw}}. Returns per-pair max abs differences and the verdict."""
    ours = {}
    for lv in LEVELS:
        seqs = int_sequences(levels[lv])
        ours[lv] = {d: mi_nat(seqs, d) for d in range(1, max_d + 1)}
    diff = {}
    for g, curve in sorted(theirs.items()):
        for lv in LEVELS:
            ds = [d for d in range(1, max_d + 1)
                  if d in curve and math.isfinite(curve[d]) and math.isfinite(ours[lv][d])]
            diff["%d~%s" % (g, lv)] = (max(abs(ours[lv][d] - curve[d]) for d in ds)
                                       if ds else None)
    ok = len(theirs) == 3
    for lv in LEVELS:
        v = diff.get("%d~%s" % (THEIR_INDEX[lv], lv))
        ok = ok and v is not None and v < tol
    return {"pass": bool(ok), "tol": tol, "max_d": max_d, "max_abs_diff": diff,
            "n_their_curves": len(theirs)}


def problems(stats):
    out = []
    for lv in LEVELS:
        if stats["levels"][lv]["n_na"]:
            out.append("NA labels at deep split %s" % lv)
    if stats["n_song_values_split"]:
        out.append("song values split into non-adjacent runs")
    if abs(stats["n_birds"] - EXPECT_BIRDS) > REL_TOL * EXPECT_BIRDS:
        out.append("birds %d vs paper %d" % (stats["n_birds"], EXPECT_BIRDS))
    if abs(stats["n_songs"] - EXPECT_SONGS) > REL_TOL * EXPECT_SONGS:
        out.append("songs %d vs paper %d" % (stats["n_songs"], EXPECT_SONGS))
    return out


def main(data_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    report = {"amendment": "AMENDMENT-1-FINCH-LOADER.md", "stop": []}
    path = os.path.join(data_dir, "finch_rows.tsv")
    if not os.path.exists(path):
        report["stop"].append("finch_rows.tsv missing (export failed)")
    else:
        levels, stats = build_levels(read_rows(path))
        report["stats"] = stats
        report["stop"].extend(problems(stats))
        theirs = {}
        for g in (1, 2, 3, 4):
            c = read_their(data_dir, g)
            if c is not None:
                theirs[g] = c
        c0 = c0_check(levels, theirs)
        report["C0"] = c0
        if not c0["pass"]:
            report["stop"].append("C0 failed: our raw MI curve does not match the authors' mi_raw")
    report["ok"] = not report["stop"]
    with open(os.path.join(out_dir, "load_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps(report, indent=1), flush=True)
    if not report["ok"]:
        print("LOADER STOP: " + "; ".join(report["stop"]), flush=True)
        return 1
    with open(os.path.join(data_dir, "finch_levels.json"), "w") as fh:
        json.dump({"levels": levels}, fh)
    print("LOADER OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 8: calibrate criterion C8 ("a pure power law beats both the
exponential and the composite") as a signature of recursive hierarchy in MI-decay curves.
Registered in AMENDMENT-8-STAGE8.md before any stage-8 world was simulated.

Uses the stage-1 pipeline unchanged: mi_decay.py is fetched from the public repository by
gate8.py (sha256 logged) into MV2_LIB (default /tmp/mv2-stage8).

  python stage8.py selftest
  python stage8.py calibrate --out-dir /out --worlds 50 --seed 20261127
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.environ.get("MV2_LIB", "/tmp/mv2-stage8"))
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import mi_decay as md  # noqa: E402
import grade8  # noqa: E402


# ----------------------------------------------------------------------------- new worlds

def sparse_table(rng, rows, k, ps=(0.7, 0.2, 0.1)):
    """rows x k row-stochastic table; each row puts ps on distinct random symbols."""
    w = np.array(ps, dtype=float)
    w /= w.sum()
    P = np.zeros((rows, k))
    for i in range(rows):
        P[i, rng.choice(k, size=len(ps), replace=False)] = w
    return P


def high_order_chain(rng, table, k, order, n, eps=0.02):
    """Finite-state chain of the given order: the last `order` symbols are hashed to a row of
    `table`; with probability eps the next symbol is uniform (keeps the chain irreducible)."""
    cum = np.cumsum(table, axis=1)
    cum[:, -1] = 1.0
    n_rows = table.shape[0]
    mod = k ** order
    s = np.empty(n, dtype=np.int64)
    s[:order] = rng.integers(k, size=order)
    ctx = 0
    for v in s[:order]:
        ctx = (ctx * k + int(v)) % mod
    u = rng.random(n)
    e = rng.random(n)
    r = rng.integers(k, size=n)
    for t in range(order, n):
        if e[t] < eps:
            v = int(r[t])
        else:
            row = (ctx * 2654435761) % n_rows
            v = min(int(np.searchsorted(cum[row], u[t], side="right")), k - 1)
        s[t] = v
        ctx = (ctx * k + v) % mod
    return s


def world_f5(rng):
    """10 birds, each with its own W3-style song types (18 own syllables), 3 days each."""
    seqs = []
    for b in range(10):
        for day in md.world_w3(rng, n_days=3):
            seqs.append(day + 18 * b)
    return seqs


def world_f6(rng):
    """One bird with a high-order (4 to 8) finite-state syntax, 30 sequences of 4,000."""
    k = 12
    order = int(rng.integers(4, 9))
    table = sparse_table(rng, 2048, k)
    return [high_order_chain(rng, table, k, order, 4000) for _ in range(30)]


def world_l1(rng, n_days=30, day_len=4000, n_types=3, type_size=6, alpha=1.2, xmin=20, cap=4000):
    """Non-hierarchical long memory: bouts of song types with Pareto(alpha) bout lengths
    (minimum 20, capped at 4,000); the type changes at every bout end."""
    mats = [md.balanced_matrix(rng, type_size) for _ in range(n_types)]
    days = []
    for _ in range(n_days):
        parts, total = [], 0
        t = int(rng.integers(n_types))
        while total < day_len:
            u = 1.0 - float(rng.random())
            length = int(min(cap, np.floor(xmin * u ** (-1.0 / alpha))))
            s = md.simulate_chain(rng, mats[t], length, start=int(rng.integers(type_size)))
            parts.append(s + t * type_size)
            total += length
            t = int((t + 1 + rng.integers(n_types - 1)) % n_types)
        days.append(np.concatenate(parts)[:day_len].astype(np.int64))
    return days


def world_r1(rng):
    M = md.balanced_matrix(rng, 5)
    return [md.lin_tegmark_sequence(rng, M, 12) for _ in range(30)]


def world_r2(rng):
    M = md.balanced_matrix(rng, 8)
    return [md.lin_tegmark_sequence(rng, M, 12) for _ in range(30)]


def world_r3(rng):
    M = md.balanced_matrix(rng, 5)
    return [md.lin_tegmark_sequence(rng, M, 8, q=3) for _ in range(30)]


def world_r4(rng):
    """Days of 40 short recursive bouts (depth 7, 128 symbols each) joined, 30 days."""
    M = md.balanced_matrix(rng, 5)
    return [np.concatenate([md.lin_tegmark_sequence(rng, M, 7) for _ in range(40)])
            for _ in range(30)]


def world_r5(rng):
    """30 pooled birds, each with its own recursive grammar and own 5 symbols."""
    seqs = []
    for b in range(30):
        M = md.balanced_matrix(rng, 5)
        seqs.append(md.lin_tegmark_sequence(rng, M, 12) + 5 * b)
    return seqs


WORLD_FNS = {
    "F0_plain_markov": md.world_w0,
    "F1_two_timescale_markov": md.world_w1,
    "F2_pooled_individuals": md.world_w2,
    "F3_bout_song_types": md.world_w3,
    "F4_house_finch_design": md.world_w4,
    "F5_pooled_bout_birds": world_f5,
    "F6_high_order_markov": world_f6,
    "L1_heavy_tailed_bouts": world_l1,
    "R1_lin_tegmark_k5_d12": world_r1,
    "R2_lin_tegmark_k8_d12": world_r2,
    "R3_lin_tegmark_k5_d8_q3": world_r3,
    "R4_recursive_bouts": world_r4,
    "R5_pooled_recursive_birds": world_r5,
}


# ----------------------------------------------------------------------------- run

def selftest():
    assert list(WORLD_FNS) == grade8.ALL, "kinds out of registered order"
    rng = np.random.default_rng([1, 2, 3])
    expect_len = {"R1_lin_tegmark_k5_d12": 4096, "R2_lin_tegmark_k8_d12": 4096,
                  "R3_lin_tegmark_k5_d8_q3": 6561, "R4_recursive_bouts": 5120,
                  "R5_pooled_recursive_birds": 4096, "F6_high_order_markov": 4000,
                  "L1_heavy_tailed_bouts": 4000}
    for name in ("F5_pooled_bout_birds", "F6_high_order_markov", "L1_heavy_tailed_bouts",
                 "R1_lin_tegmark_k5_d12", "R2_lin_tegmark_k8_d12", "R3_lin_tegmark_k5_d8_q3",
                 "R4_recursive_bouts", "R5_pooled_recursive_birds"):
        seqs = WORLD_FNS[name](rng)
        assert len(seqs) == 30, (name, len(seqs))
        for s in seqs:
            assert s.dtype == np.int64 and s.min() >= 0, name
            if name in expect_len:
                assert len(s) == expect_len[name], (name, len(s))
        print("selftest %s: %d sequences, %d symbols, alphabet %d"
              % (name, len(seqs), sum(len(s) for s in seqs),
                 len(np.unique(np.concatenate(seqs)))), flush=True)
    # high-order chain stays inside its alphabet and uses most of it
    t = sparse_table(rng, 64, 12)
    assert np.allclose(t.sum(axis=1), 1.0)
    s = high_order_chain(rng, t, 12, 5, 3000)
    assert s.max() < 12 and len(np.unique(s)) >= 8
    # grade rules on hand-made rates
    rates = {k: 0.0 for k in grade8.ALL}
    for k in grade8.RECURSIVE:
        rates[k] = 0.6
    assert grade8.grade(rates)["verdict"] == "CALIBRATED_HIERARCHY_SIGNATURE"
    print("selftest ok", flush=True)
    return 0


def run_calibration(worlds, seed, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows, summary, curves = [], {}, {}
    show = [1, 2, 5, 10, 20, 50, 100]
    t0 = time.time()
    for si, name in enumerate(grade8.ALL):
        fn = WORLD_FNS[name]
        best_counts = {"powerlaw": 0, "composite": 0, "exponential": 0, "none": 0}
        strong_pl = strong_comp = 0
        curve_sum, curve_n = np.zeros(len(md.DISTANCES)), np.zeros(len(md.DISTANCES))
        for w in range(worlds):
            rng = np.random.default_rng([seed, si, w])
            seqs = fn(rng)
            mi, base = md.mi_curve(seqs, rng)
            sig = mi - base
            fit = md.fit_curve(md.DISTANCES, sig)
            best = fit["best"] or "none"
            best_counts[best] += 1
            wts = fit["w"] or {}
            spl = bool(best == "powerlaw" and wts.get("powerlaw", 0.0) > grade8.STRONG)
            strong_pl += int(spl)
            strong_comp += int(fit["fire_strong"])
            ok = np.isfinite(sig)
            curve_sum[ok] += sig[ok]
            curve_n[ok] += 1
            rows.append({"kind": name, "world": w, "n_symbols_total": int(sum(len(s) for s in seqs)),
                         "n_sequences": len(seqs), "sig_at": {str(d): float(sig[d - 1]) for d in show},
                         "n_points": fit["n_points"], "aicc": fit["aicc"], "w": fit["w"],
                         "best": fit["best"], "c8": best == "powerlaw", "c8_strong": spl,
                         "composite_strong": fit["fire_strong"]})
        mean_curve = np.where(curve_n > 0, curve_sum / np.maximum(curve_n, 1), np.nan)
        curves[name] = [[int(d), float(v)] for d, v in zip(md.DISTANCES, mean_curve)]
        summary[name] = {"worlds": worlds, "c8_fires": best_counts["powerlaw"],
                         "c8_rate": best_counts["powerlaw"] / worlds,
                         "c8_strong_fires": strong_pl, "c8_strong_rate": strong_pl / worlds,
                         "composite_strong_fires": strong_comp, "best_counts": best_counts}
        print("%s: C8 %d/%d, C8 strong %d/%d, composite strong %d/%d, best %s (%.0f s)"
              % (name, best_counts["powerlaw"], worlds, strong_pl, worlds, strong_comp, worlds,
                 json.dumps(best_counts), time.time() - t0), flush=True)
    rates = {k: summary[k]["c8_rate"] for k in grade8.ALL}
    rates_strong = {k: summary[k]["c8_strong_rate"] for k in grade8.ALL}
    g = grade8.grade(rates)
    outcomes = grade8.forecast_outcomes(rates, g["verdict"])
    result = {"stage": 8, "seed": seed, "worlds_per_kind": worlds,
              "primary_criterion": "C8: powerlaw has the lowest AICc of exponential, powerlaw, composite",
              "secondary_criterion": "C8 and powerlaw relative probability > 0.999",
              "summary": summary, "grade_primary": g, "grade_secondary_strong": grade8.grade(rates_strong),
              "forecast_outcomes": outcomes, "brier": grade8.brier(outcomes),
              "runtime_s": time.time() - t0}
    with open(os.path.join(out_dir, "stage8.json"), "w") as fh:
        json.dump(md.clean(result), fh, indent=1)
    with open(os.path.join(out_dir, "stage8_worlds.json"), "w") as fh:
        json.dump(md.clean(rows), fh)
    with open(os.path.join(out_dir, "stage8_curves.json"), "w") as fh:
        json.dump(md.clean(curves), fh)
    print(json.dumps(md.clean(g)), flush=True)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    c = sub.add_parser("calibrate")
    c.add_argument("--out-dir", required=True)
    c.add_argument("--worlds", type=int, default=grade8.WORLDS)
    c.add_argument("--seed", type=int, default=grade8.SEED)
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    run_calibration(a.worlds, a.seed, a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

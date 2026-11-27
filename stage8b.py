# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""birdsong-mi-decay-test, stage 8B: pin the pooled-birds false-alarm rate of criterion C8 ("a
pure power law beats both the exponential and the composite"), test it against long-memory
processes without hierarchy (quantized fractional Gaussian noise; heavy-tailed bouts on a shared
alphabet), and grade a reachable strong criterion C8R. Registered in AMENDMENT-8B-STAGE8B.md
before any stage-8B world was simulated. Motivated by the stage-8 MIXED grade (F2 3 of 50).

Uses the stage-1 pipeline and the stage-8 worlds unchanged: mi_decay.py, stage8.py and grade8.py
are fetched from the public repository by gate8b.py (sha256 logged) into MV2_LIB.

  python stage8b.py selftest
  python stage8b.py calibrate --out-dir /out --seed 20261128
"""
import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.environ.get("MV2_LIB", "/tmp/mv2-stage8b"))
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import mi_decay as md  # noqa: E402
import stage8  # noqa: E402
import grade8b  # noqa: E402

N_BINS = 8


# ----------------------------------------------------------------------------- new worlds

def fgn_autocov(n, H):
    k = np.arange(n + 1, dtype=float)
    return 0.5 * (np.abs(k + 1) ** (2 * H) - 2 * np.abs(k) ** (2 * H) + np.abs(k - 1) ** (2 * H))


def fgn(rng, n, H):
    """Two independent unit-variance fractional Gaussian noise paths of length n (Davies-Harte
    circulant embedding)."""
    g = fgn_autocov(n, H)
    c = np.concatenate([g, g[-2:0:-1]])          # length 2n
    lam = np.fft.fft(c).real
    lam = np.where(lam < 0, 0.0, lam)            # round-off only; fGn embedding is non-negative
    m = len(c)
    xi = rng.standard_normal(m) + 1j * rng.standard_normal(m)
    y = np.fft.fft(np.sqrt(lam / m) * xi)
    return y.real[:n], y.imag[:n]


def quantize(x, bins=N_BINS):
    """Equiprobable bins from the sequence's own quantiles -> int64 symbols 0..bins-1."""
    edges = np.quantile(x, [i / bins for i in range(1, bins)])
    return np.searchsorted(edges, x, side="right").astype(np.int64)


def world_fgn(rng, H, n_seq=30, n=4000):
    seqs = []
    while len(seqs) < n_seq:
        a, b = fgn(rng, n, H)
        seqs.append(quantize(a))
        if len(seqs) < n_seq:
            seqs.append(quantize(b))
    return seqs


def world_l2(rng):
    return world_fgn(rng, 0.7)


def world_l3(rng):
    return world_fgn(rng, 0.9)


def world_l4(rng, n_days=30, day_len=4000, n_types=3, k=12, alpha=1.5, xmin=20, cap=4000):
    """Long memory without hierarchy on ONE shared alphabet: three regimes, each its own
    irreducible chain over the same 12 syllables; Pareto(alpha 1.5) regime durations (minimum 20,
    capped at 4,000); the regime changes at every bout end."""
    mats = [md.balanced_matrix(rng, k) for _ in range(n_types)]
    days = []
    for _ in range(n_days):
        parts, total = [], 0
        t = int(rng.integers(n_types))
        while total < day_len:
            u = 1.0 - float(rng.random())
            length = int(min(cap, np.floor(xmin * u ** (-1.0 / alpha))))
            parts.append(md.simulate_chain(rng, mats[t], length, start=int(rng.integers(k))))
            total += length
            t = int((t + 1 + rng.integers(n_types - 1)) % n_types)
        days.append(np.concatenate(parts)[:day_len].astype(np.int64))
    return days


def world_f7(rng):
    """30 pooled birds as in F2 (stage-1 W2) but on ONE shared 12-syllable alphabet."""
    return [md.simulate_chain(rng, md.group_chain(rng, 3, 4, float(rng.uniform(0.5, 0.99))), 4000)
            for _ in range(30)]


WORLD_FNS = {
    "F2_pooled_individuals": md.world_w2,
    "F6_high_order_markov": stage8.world_f6,
    "F7_pooled_shared_alphabet": world_f7,
    "L2_fgn_h07": world_l2,
    "L3_fgn_h09": world_l3,
    "L4_shared_alphabet_heavy_bouts": world_l4,
    "R1_lin_tegmark_k5_d12": stage8.world_r1,
    "R5_pooled_recursive_birds": stage8.world_r5,
}


# ----------------------------------------------------------------------------- run

def selftest():
    assert list(WORLD_FNS) == grade8b.ALL, "kinds out of registered order"
    rng = np.random.default_rng([8, 2, 2])
    # fGn: variance and lag-1 / lag-10 autocovariance match theory, averaged without centring
    # (true mean 0) over 800 independent paths of 1,024 (unbiased; long memory makes a single
    # path's estimate too noisy for a test; tolerance about 4 standard errors at H 0.9)
    for H in (0.7, 0.9):
        g = fgn_autocov(10, H)
        acc = {0: 0.0, 1: 0.0, 10: 0.0}
        cnt = 0
        for _ in range(400):
            for x in fgn(rng, 1024, H):
                acc[0] += float(np.mean(x * x))
                for lag in (1, 10):
                    acc[lag] += float(np.mean(x[:-lag] * x[lag:]))
                cnt += 1
        for lag in (0, 1, 10):
            r = acc[lag] / cnt
            assert abs(r - g[lag]) < 0.06, ("fgn autocovariance", H, lag, r, g[lag])
        print("selftest fgn H %.1f: lag1 %.4f (theory %.4f), lag10 %.4f (theory %.4f)"
              % (H, acc[1] / cnt, g[1], acc[10] / cnt, g[10]), flush=True)
    q = quantize(rng.standard_normal(8000))
    counts = np.bincount(q, minlength=N_BINS)
    assert q.min() == 0 and q.max() == N_BINS - 1 and counts.min() >= 990, counts
    for name in grade8b.ALL:
        seqs = WORLD_FNS[name](rng)
        assert len(seqs) == 30, (name, len(seqs))
        for s in seqs:
            assert s.dtype == np.int64 and s.min() >= 0, name
        alpha = len(np.unique(np.concatenate(seqs)))
        if name in ("L2_fgn_h07", "L3_fgn_h09"):
            assert alpha == N_BINS and all(len(s) == 4000 for s in seqs), name
        if name in ("F7_pooled_shared_alphabet", "L4_shared_alphabet_heavy_bouts"):
            assert alpha <= 12 and all(len(s) == 4000 for s in seqs), name
        print("selftest %s: %d sequences, %d symbols, alphabet %d"
              % (name, len(seqs), sum(len(s) for s in seqs), alpha), flush=True)
    assert grade8b.c8r("powerlaw", {"exponential": -100.0, "powerlaw": -110.0, "composite": -106.0})
    assert not grade8b.c8r("powerlaw", {"exponential": -100.0, "powerlaw": -109.0, "composite": -105.0})
    print("selftest ok", flush=True)
    return 0


def run_calibration(seed, out_dir, scale=1.0):
    os.makedirs(out_dir, exist_ok=True)
    rows, summary, curves = [], {}, {}
    show = [1, 2, 5, 10, 20, 50, 100]
    fires_c8, fires_c8r = {}, {}
    t0 = time.time()
    for si, name in enumerate(grade8b.ALL):
        fn = WORLD_FNS[name]
        worlds = max(1, int(round(grade8b.WORLDS[name] * scale)))
        best_counts = {"powerlaw": 0, "composite": 0, "exponential": 0, "none": 0}
        n_c8r = n_comp = 0
        curve_sum, curve_n = np.zeros(len(md.DISTANCES)), np.zeros(len(md.DISTANCES))
        for w in range(worlds):
            rng = np.random.default_rng([seed, si, w])
            seqs = fn(rng)
            mi, base = md.mi_curve(seqs, rng)
            sig = mi - base
            fit = md.fit_curve(md.DISTANCES, sig)
            best = fit["best"] or "none"
            best_counts[best] += 1
            aic = fit["aicc"] or {}
            is_c8r = grade8b.c8r(fit["best"], aic)
            n_c8r += int(is_c8r)
            n_comp += int(fit["fire_strong"])
            exp_minus_pl = (aic["exponential"] - aic["powerlaw"]
                            if "exponential" in aic and "powerlaw" in aic else None)
            ok = np.isfinite(sig)
            curve_sum[ok] += sig[ok]
            curve_n[ok] += 1
            rows.append({"kind": name, "world": w, "n_symbols_total": int(sum(len(s) for s in seqs)),
                         "sig_at": {str(d): float(sig[d - 1]) for d in show},
                         "n_points": fit["n_points"], "aicc": fit["aicc"], "w": fit["w"],
                         "best": fit["best"], "c8": best == "powerlaw", "c8r": is_c8r,
                         "aicc_exp_minus_powerlaw": exp_minus_pl,
                         "composite_strong": fit["fire_strong"]})
        mean_curve = np.where(curve_n > 0, curve_sum / np.maximum(curve_n, 1), np.nan)
        curves[name] = [[int(d), float(v)] for d, v in zip(md.DISTANCES, mean_curve)]
        fires_c8[name], fires_c8r[name] = best_counts["powerlaw"], n_c8r
        summary[name] = {"worlds": worlds, "c8_fires": best_counts["powerlaw"],
                         "c8r_fires": n_c8r, "composite_strong_fires": n_comp,
                         "best_counts": best_counts}
        print("%s: C8 %d/%d, C8R %d/%d, published composite verdict %d/%d, best %s (%.0f s)"
              % (name, best_counts["powerlaw"], worlds, n_c8r, worlds, n_comp, worlds,
                 json.dumps(best_counts), time.time() - t0), flush=True)
    result = {"stage": "8B", "seed": seed, "scale": scale, "worlds": {k: summary[k]["worlds"] for k in summary},
              "primary_criterion": "C8: powerlaw has the lowest AICc of exponential, powerlaw, composite",
              "secondary_criterion": "C8R: C8 and AICc(exponential) - AICc(powerlaw) >= 10",
              "summary": summary}
    if scale == 1.0:
        g8 = grade8b.grade(fires_c8)
        g8r = grade8b.grade(fires_c8r)
        out = grade8b.forecast_outcomes(fires_c8, fires_c8r, g8["verdict"])
        result.update({"grade_c8": g8, "grade_c8r": g8r, "forecast_outcomes": out,
                       "brier": grade8b.brier(out)})
        print(json.dumps(md.clean({"c8": g8["verdict"], "c8r": g8r["verdict"]})), flush=True)
    result["runtime_s"] = time.time() - t0
    with open(os.path.join(out_dir, "stage8b.json"), "w") as fh:
        json.dump(md.clean(result), fh, indent=1)
    with open(os.path.join(out_dir, "stage8b_worlds.json"), "w") as fh:
        json.dump(md.clean(rows), fh)
    with open(os.path.join(out_dir, "stage8b_curves.json"), "w") as fh:
        json.dump(md.clean(curves), fh)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    c = sub.add_parser("calibrate")
    c.add_argument("--out-dir", required=True)
    c.add_argument("--seed", type=int, default=grade8b.SEED)
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        return selftest()
    run_calibration(a.seed, a.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

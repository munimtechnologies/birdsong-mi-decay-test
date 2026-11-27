# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage 8B grading rules (stdlib only), registered in AMENDMENT-8B-STAGE8B.md before any
stage-8B world was simulated.

C8  (primary, unchanged from stage 8): the pure power law a*d^b+c has the lowest AICc of the
    three models (exponential, power law, composite) fitted by mi_decay.fit_curve.
C8R (secondary, reachable): C8 and AICc(exponential) - AICc(power law) >= 10.
"""
import math

SEED = 20261128
EXP_MARGIN = 10.0     # C8R: the exponential must lose to the power law by at least this AICc
FA_POINT = 0.05       # finite-state point fire rate must be at or below this
FA_UPPER = 0.10       # ... and its exact 95% upper bound at or below this
FA_NULL = 0.05        # NOT_SPECIFIC if an exact 95% lower bound is above this
DETECT = 0.40         # each recursive kind must fire at or above this rate
LONG_MEMORY = 0.30    # any long-memory kind at or above this: the signature marks long memory

WORLDS = {
    "F2_pooled_individuals": 400,
    "F6_high_order_markov": 100,
    "F7_pooled_shared_alphabet": 100,
    "L2_fgn_h07": 100,
    "L3_fgn_h09": 100,
    "L4_shared_alphabet_heavy_bouts": 100,
    "R1_lin_tegmark_k5_d12": 100,
    "R5_pooled_recursive_birds": 100,
}
FINITE = ["F2_pooled_individuals", "F6_high_order_markov", "F7_pooled_shared_alphabet"]
LONG = ["L2_fgn_h07", "L3_fgn_h09", "L4_shared_alphabet_heavy_bouts"]
RECURSIVE = ["R1_lin_tegmark_k5_d12", "R5_pooled_recursive_birds"]
ALL = FINITE + LONG + RECURSIVE

GRADES = ("NOT_SPECIFIC", "CALIBRATED_HIERARCHY_SIGNATURE", "CALIBRATED_LONG_MEMORY_SIGNATURE",
          "SPECIFIC_BUT_INSENSITIVE", "UNRESOLVED")

# Registered forecasts (probability that each statement comes out true).
FORECASTS = [
    ("Q1", "F2 pooled individuals fires C8 at rate <= 0.05 over 400 worlds", 0.70),
    ("Q2", "every finite-state kind passes the C8 false-alarm rule", 0.45),
    ("Q3", "L2 fGn H 0.7 fires C8 at rate >= 0.30", 0.75),
    ("Q4", "L3 fGn H 0.9 fires C8 at rate >= 0.30", 0.75),
    ("Q5", "L4 shared-alphabet heavy bouts fires C8 at rate >= 0.30", 0.35),
    ("Q6", "R1 fires C8R at rate >= 0.40", 0.55),
    ("Q7", "C8 grade is CALIBRATED_HIERARCHY_SIGNATURE", 0.10),
    ("Q8", "C8 grade is CALIBRATED_LONG_MEMORY_SIGNATURE", 0.35),
]


def _log_pmf(n, k, p):
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
            + k * math.log(p) + (n - k) * math.log1p(-p))


def binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    return min(1.0, sum(math.exp(_log_pmf(n, i, p)) for i in range(k + 1)))


def cp_bounds(k, n, alpha=0.05):
    """Exact (Clopper-Pearson) two-sided 1-alpha interval for a binomial rate, by bisection."""
    def solve(f, target):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if f(mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0
    upper = 1.0 if k >= n else solve(lambda p: binom_cdf(k, n, p), alpha / 2.0)
    lower = 0.0 if k <= 0 else 1.0 - solve(lambda q: binom_cdf(n - k, n, q), alpha / 2.0)
    # lower bound: P(X >= k | p_lo) = alpha/2  <=>  P(n-X <= n-k | 1-p_lo) = alpha/2
    return lower, upper


def grade(fires):
    """fires: kind -> number of worlds (of WORLDS[kind]) in which the criterion fired."""
    for k in ALL:
        if k not in fires:
            raise KeyError("missing kind %s" % k)
    rate = {k: fires[k] / WORLDS[k] for k in ALL}
    bounds = {k: cp_bounds(fires[k], WORLDS[k]) for k in FINITE}
    fa_ok = all(rate[k] <= FA_POINT and bounds[k][1] <= FA_UPPER for k in FINITE)
    fa_bad = any(bounds[k][0] > FA_NULL for k in FINITE)
    det_ok = all(rate[k] >= DETECT for k in RECURSIVE)
    lm = max(rate[k] for k in LONG)
    if fa_bad:
        v = "NOT_SPECIFIC"
    elif fa_ok and det_ok:
        v = "CALIBRATED_HIERARCHY_SIGNATURE" if lm < LONG_MEMORY else "CALIBRATED_LONG_MEMORY_SIGNATURE"
    elif fa_ok:
        v = "SPECIFIC_BUT_INSENSITIVE"
    else:
        v = "UNRESOLVED"
    return {"verdict": v, "rates": rate,
            "finite_bounds": {k: list(b) for k, b in bounds.items()},
            "false_alarm_ok": fa_ok, "detection_ok": det_ok, "max_long_memory_rate": lm}


def forecast_outcomes(fires_c8, fires_c8r, verdict_c8):
    r = {k: fires_c8[k] / WORLDS[k] for k in ALL}
    g = grade(fires_c8)
    return {
        "Q1": r["F2_pooled_individuals"] <= FA_POINT,
        "Q2": g["false_alarm_ok"],
        "Q3": r["L2_fgn_h07"] >= LONG_MEMORY,
        "Q4": r["L3_fgn_h09"] >= LONG_MEMORY,
        "Q5": r["L4_shared_alphabet_heavy_bouts"] >= LONG_MEMORY,
        "Q6": fires_c8r["R1_lin_tegmark_k5_d12"] / WORLDS["R1_lin_tegmark_k5_d12"] >= DETECT,
        "Q7": verdict_c8 == "CALIBRATED_HIERARCHY_SIGNATURE",
        "Q8": verdict_c8 == "CALIBRATED_LONG_MEMORY_SIGNATURE",
    }


def brier(outcomes):
    return sum((float(outcomes[q]) - p) ** 2 for q, _, p in FORECASTS) / len(FORECASTS)


def c8r(best, aicc):
    """Secondary criterion on one fit: power law best and exponential worse by >= EXP_MARGIN."""
    if best != "powerlaw" or not aicc or "exponential" not in aicc or "powerlaw" not in aicc:
        return False
    return (aicc["exponential"] - aicc["powerlaw"]) >= EXP_MARGIN

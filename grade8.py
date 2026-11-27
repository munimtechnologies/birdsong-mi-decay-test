# Copyright 2026 MV2, Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents working in MV2's name.
"""Stage 8 grading rules (stdlib only), registered in AMENDMENT-8-STAGE8.md before any stage-8
world was simulated. Criterion C8: the pure power law a*d^b+c has the lowest AICc of the three
models (exponential, power law, composite) fitted by mi_decay.fit_curve."""
import statistics

SEED = 20261127
WORLDS = 50
STRONG = 0.999      # secondary criterion: C8 and relative probability of the power law > 0.999
FA_OK = 0.05        # every finite-state kind must fire at or below this rate
FA_BAD = 0.20       # any finite-state kind at or above this rate: NOT_SPECIFIC
DETECT = 0.50       # median fire rate over the recursive kinds must reach this
LONG_MEMORY = 0.30  # heavy-tailed bout control at or above this: the signature is long memory

FINITE = ["F0_plain_markov", "F1_two_timescale_markov", "F2_pooled_individuals",
          "F3_bout_song_types", "F4_house_finch_design", "F5_pooled_bout_birds",
          "F6_high_order_markov"]
LONG = ["L1_heavy_tailed_bouts"]
RECURSIVE = ["R1_lin_tegmark_k5_d12", "R2_lin_tegmark_k8_d12", "R3_lin_tegmark_k5_d8_q3",
             "R4_recursive_bouts", "R5_pooled_recursive_birds"]
ALL = FINITE + LONG + RECURSIVE

GRADES = ("NOT_SPECIFIC", "CALIBRATED_HIERARCHY_SIGNATURE", "CALIBRATED_LONG_MEMORY_SIGNATURE",
          "SPECIFIC_BUT_INSENSITIVE", "MIXED")

# Registered forecasts (probability that each statement comes out true).
FORECASTS = [
    ("Q1", "every finite-state kind F0-F6 fires at rate <= 0.05", 0.60),
    ("Q2", "R1 (stage-1 recursive setting, new seed) fires at rate >= 0.40", 0.70),
    ("Q3", "median fire rate over R1-R5 >= 0.50", 0.45),
    ("Q4", "L1 heavy-tailed bouts fires at rate >= 0.30", 0.65),
    ("Q5", "R4 recursive bouts fires at rate >= 0.50", 0.25),
    ("Q6", "R5 pooled recursive birds fires at rate >= 0.50", 0.45),
    ("Q7", "F5 pooled bout birds fires at rate <= 0.05", 0.55),
    ("Q8", "grade is CALIBRATED_HIERARCHY_SIGNATURE", 0.15),
]


def grade(rates):
    """rates: kind -> C8 fire rate (fraction of worlds). Returns the registered grade dict."""
    for k in ALL:
        if k not in rates:
            raise KeyError("missing kind %s" % k)
    fa = max(rates[k] for k in FINITE)
    det = statistics.median([rates[k] for k in RECURSIVE])
    lm = rates["L1_heavy_tailed_bouts"]
    if fa >= FA_BAD:
        v = "NOT_SPECIFIC"
    elif fa <= FA_OK and det >= DETECT:
        v = "CALIBRATED_HIERARCHY_SIGNATURE" if lm < LONG_MEMORY else "CALIBRATED_LONG_MEMORY_SIGNATURE"
    elif fa <= FA_OK:
        v = "SPECIFIC_BUT_INSENSITIVE"
    else:
        v = "MIXED"
    return {"verdict": v, "max_false_alarm": fa, "median_detection": det,
            "long_memory_rate": lm}


def forecast_outcomes(rates, verdict):
    """Truth value of each registered forecast statement."""
    det = statistics.median([rates[k] for k in RECURSIVE])
    return {
        "Q1": max(rates[k] for k in FINITE) <= FA_OK,
        "Q2": rates["R1_lin_tegmark_k5_d12"] >= 0.40,
        "Q3": det >= DETECT,
        "Q4": rates["L1_heavy_tailed_bouts"] >= LONG_MEMORY,
        "Q5": rates["R4_recursive_bouts"] >= 0.50,
        "Q6": rates["R5_pooled_recursive_birds"] >= 0.50,
        "Q7": rates["F5_pooled_bout_birds"] <= FA_OK,
        "Q8": verdict == "CALIBRATED_HIERARCHY_SIGNATURE",
    }


def brier(outcomes):
    return sum((float(outcomes[q]) - p) ** 2 for q, _, p in FORECASTS) / len(FORECASTS)


def real_data_readout(real_best, surrogate_bests):
    """Blind readout for a species stage (registered in AMENDMENT-8 section 4).
    real_best: lowest-AICc model on the real curve; surrogate_bests: list of the same for the
    stage's finite-state surrogates. Returns C8 on real data and the surrogate fire fraction."""
    n = len(surrogate_bests)
    fires = sum(1 for b in surrogate_bests if b == "powerlaw")
    frac = fires / n if n else None
    real = real_best == "powerlaw"
    if real_best is None:
        v = "NOT_MEASURED"
    elif not real:
        v = "C8_ABSENT"
    elif frac is None:
        v = "C8_PRESENT_NO_SURROGATES"
    elif frac <= 0.05:
        v = "C8_EXCEEDS_FINITE_STATE"
    else:
        v = "C8_PRESENT_IN_SURROGATES"
    return {"verdict": v, "real_c8": real, "surrogate_fires": fires, "surrogates": n,
            "surrogate_fraction": frac}

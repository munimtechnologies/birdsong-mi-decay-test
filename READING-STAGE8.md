# READING-STAGE8: is "a pure power law wins" a calibrated signature of hierarchy? (graded 2026-11-27)

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-11-27 by AI agents working in MV2's name from the
outputs of job `birdsong-stage8-v1` (Blade, finished 2026-11-27 20:19Z, 2,396 s). No human expert has
checked this reading yet. Text CC BY 4.0, code Apache-2.0. Registration:
[AMENDMENT-8-STAGE8.md](AMENDMENT-8-STAGE8.md); rules: [grade8.py](grade8.py); outputs:
[results/stage8/](results/stage8/).

The public-copy gate passed: the amendment, `stage8.py`, `grade8.py`, `gate8.py` and `test_stage8.py`
that ran have the same md5 as the public copies (results/stage8/gate8.json), and the stage-1 core
`mi_decay.py` ran with sha256 12068ae4f0526f8dda457917fd6f72dfcc36e0bcc61782fe52a9b83d5cf3fab8.

## Headline: MIXED

Criterion C8 (the pure power law \(a d^{b} + c\) has the lowest AICc of exponential, power law and
composite) fired in a median **0.54** of the five recursive kinds, in **0** of 50 heavy-tailed-bout
worlds (long memory, no hierarchy), and at a rate of at most 0.05 in six of the seven finite-state
kinds. The seventh, `F2_pooled_individuals` (30 simulated birds, each with its own finite-state
chain, pooled as in the published designs), fired in **3 of 50** worlds, a rate of **0.06**. The
registered limit was 0.05, so the registered grade is **MIXED**, not CALIBRATED_HIERARCHY_SIGNATURE.
It misses by one world.

| kind | class | C8 fires (of 50) | C8 rate | published composite verdict fires (of 50) |
|---|---|---|---|---|
| F0_plain_markov | finite-state | 0 | 0.00 | 0 |
| F1_two_timescale_markov | finite-state | 0 | 0.00 | 5 |
| F2_pooled_individuals | finite-state | 3 | 0.06 | 41 |
| F3_bout_song_types | finite-state | 0 | 0.00 | 50 |
| F4_house_finch_design | finite-state | 0 | 0.00 | 0 |
| F5_pooled_bout_birds | finite-state | 0 | 0.00 | 50 |
| F6_high_order_markov | finite-state | 2 | 0.04 | 0 |
| L1_heavy_tailed_bouts | long memory, no hierarchy | 0 | 0.00 | 50 |
| R1_lin_tegmark_k5_d12 | recursive | 31 | 0.62 | 1 |
| R2_lin_tegmark_k8_d12 | recursive | 21 | 0.42 | 10 |
| R3_lin_tegmark_k5_d8_q3 | recursive | 14 | 0.28 | 16 |
| R4_recursive_bouts | recursive | 27 | 0.54 | 11 |
| R5_pooled_recursive_birds | recursive | 40 | 0.80 | 1 |

Registered grade inputs (results/stage8/stage8.json `grade_primary`): max false alarm 0.06, median
detection 0.54, long-memory rate 0.0, verdict MIXED.

## What the numbers say (descriptive, not part of the registered grade)

- Pooled over kinds, C8 fired in **5 of 350** finite-state worlds and **133 of 250** recursive
  worlds. This repeats, on fresh worlds with a new seed, the exploratory stage-1 contrast (28 of 50
  recursive against 0 of 250 finite-state). R1, the stage-1 recursive setting, gave 31 of 50.
- The heavy-tailed-bout control, the design most likely to break C8, gave **0 of 50**. Our
  registered expectation (C8 would mark long memory, not hierarchy) was wrong for this design.
- The **published** verdict (the composite model wins with relative probability above 0.999, the
  reading of Sainburg et al. 2019) fired in 146 of 350 finite-state worlds and 50 of 50 heavy-tailed
  worlds, but in only 39 of 250 recursive worlds. In these simulations it fires more often without
  hierarchy than with it, as in stage 1.
- 3 of 50 is compatible with a true F2 rate below 0.05 (an exact 95% binomial interval runs from
  about 1% to about 17%). With 50 worlds per kind the registered test could not separate 0.04 from
  0.06; that is a limit of our design, and the grade stands as registered.

## The secondary criterion could never fire (an error in our registration)

The secondary (strong) criterion asked for C8 with a pure-power-law relative probability above
0.999. It fired in 0 of 650 worlds (`grade_secondary_strong`: SPECIFIC_BUT_INSENSITIVE). The reason
is structural, not evidential: the composite model contains the pure power law as a special case
(its exponential term at zero), so on a curve the power law fits well the composite fits equally
well and pays only its two extra parameters in AICc, about 4.4 units at 100 distances. That caps the
power law's relative probability near 0.90. In results/stage8/stage8_worlds.json no world gives the
power law a relative probability above 0.91 (the three F2 fires give 0.8997, 0.8676 and 0.8987). The
0.999 threshold, copied from the composite verdict, was therefore unreachable, and we should have
seen that before registering it. It is reported and not used.

## Forecasts (registered in AMENDMENT-8, scored with grade8.brier)

| id | statement | p | outcome |
|---|---|---|---|
| Q1 | every finite-state kind fires at rate <= 0.05 | 0.60 | false (F2 0.06) |
| Q2 | R1 fires at rate >= 0.40 | 0.70 | true (0.62) |
| Q3 | median over R1-R5 >= 0.50 | 0.45 | true (0.54) |
| Q4 | L1 heavy-tailed bouts fires at rate >= 0.30 | 0.65 | false (0.00) |
| Q5 | R4 recursive bouts fires at rate >= 0.50 | 0.25 | true (0.54) |
| Q6 | R5 pooled recursive birds fires at rate >= 0.50 | 0.45 | true (0.80) |
| Q7 | F5 pooled bout birds fires at rate <= 0.05 | 0.55 | true (0.00) |
| Q8 | grade is CALIBRATED_HIERARCHY_SIGNATURE | 0.15 | false (MIXED) |

Brier score **0.2831** over 8 forecasts, worse than a coin-flip forecaster (0.25). Our expectation
that C8 marks long memory rather than hierarchy, and that short recursive bouts are too short for
it, both failed.

## What this means for the real-song stages

AMENDMENT-8 section 4 fixed the interpretation before any grade: a real-song C8 readout counts as
evidence of hierarchy only under CALIBRATED_HIERARCHY_SIGNATURE. Under MIXED, the C8 readouts of the
house finch, chimpanzee, Cassin's vireo, speech and starling stages are reported descriptively only.
The Bengalese finch readout (non-blind) stays C8_ABSENT: its real curve was best fit by the composite.

## Limits

- 50 worlds per kind; one heavy-tailed design (Pareto bouts, alpha 1.2); the recursive kinds are
  Lin-Tegmark-type trees, which are one family of hierarchical processes. A different long-memory
  process without hierarchy (for example Debowski's constructions) could still fire C8.
- C8 compares three curve models on a shuffle-corrected MI curve at distances 1 to 100; it says
  nothing about structure the MI curve cannot see.
- Carried out with AI agents working in MV2's name; not yet checked by a human expert.

## What comes next

A follow-up would need a new, separately registered amendment: more F2-type worlds to estimate the
pooled-birds false-alarm rate to within about 0.01, a second long-memory control, and a strong
criterion that can be met (for example, the composite's exponential term adds no AICc improvement
and the power law beats the exponential by a fixed margin). Nothing of that is done here.

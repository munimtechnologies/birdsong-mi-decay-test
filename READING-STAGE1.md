# Reading of stage 1: does the published "power-law tail" verdict fire on finite-state song?

MV2, Munim, Inc. (mv2@munimtech.com). Graded 2026-11-27 with AI agents working in MV2's name; no
human expert has checked it yet. Text CC BY 4.0, code Apache-2.0. Registered plan:
[PLAN.md](PLAN.md) (registered 2026-11-24, before any simulation was run). Job
`birdsong-mi-cal-v1`, run 2026-11-27 11:31 to 11:56 UTC on MV2's own hardware; its first step
(`gate.py`) checked that PLAN.md, mi_decay.py, test_mi_decay.py, fetch_data.py and manifest.py were
byte-identical to the public repository before anything ran, and all 16 unit tests passed. Raw
outputs: [results/stage1/](results/stage1/).

## Grade: UNCALIBRATED_MULTI_TIMESCALE (positive control failed)

The diagnostic under test is the one in Sainburg, Theilman, Thielk and Gentner (2019, Nat Commun
10:3636) and Youngblood (2024, Proc R Soc B 291:20240250): fit an exponential, a power law and an
exponential-plus-power-law ("composite") model to the decay of mutual information (MI) between
syllables over distances 1 to 100, and read a composite win as structure beyond Markov
dynamics, consistent with hierarchy. Registered primary criterion: the composite has the lowest
AICc and relative probability above 0.999.

**In simulated worlds where every sequence comes from a finite-state process, the verdict fired
in 46 of 50 worlds of 30 pooled individuals and in 50 of 50 worlds of days made of persistent
song-type bouts. In the recursive-hierarchy model that the 2019 paper itself uses as its example
of hierarchy, it fired in 2 of 50 worlds.** So the composite verdict is neither specific (it fires
on pooled or bout-structured finite-state song) nor sensitive (it misses the paper's own model of
hierarchy), at the registered strength.

## Results (results/stage1/calibration.json; 50 worlds per scenario, seed 20261124)

| world | what it is | finite-state? | primary fires | composite lowest AICc | median AICc gap (exp minus composite) |
|---|---|---|---|---|---|
| W0 | plain first-order Markov chain | yes | 3 of 50 | 5 of 50 | -4.37 |
| W1 | one bird, two timescales (phrase groups) | yes | 4 of 50 | 19 of 50 | -1.40 |
| W2 | 30 pooled individuals, each its own chain | yes | 46 of 50 | 50 of 50 | 265.81 |
| W3 | days of persistent song-type bouts, joined as in Sainburg et al. | yes | 50 of 50 | 50 of 50 | 514.16 |
| W4 | house-finch design (331 birds, repeated fixed songs) | yes | 0 of 50 | 1 of 50 | -4.39 |
| W5 | Lin-Tegmark recursive hierarchy (positive control) | no | 2 of 50 | 16 of 50 | 42.71 |

Registered grade rule: W0 fire rate 0.06 is below 0.30; W2 (0.92) and W3 (1.0) are at or above
0.30, so the grade is UNCALIBRATED_MULTI_TIMESCALE. The secondary criterion (composite simply has
the lowest AICc) gives the same grade. The positive control needed W5 at or above 0.80 and got
0.04, so by the plan's own wording our re-implementation of the published verdict is reported as
unable to see the hierarchy it should, and the grade carries that caveat.

## Why the positive control failed (exploratory, not registered)

In W5 the exponential loses badly (median gap 42.71 AICc units), but the winner is usually the
**pure power law**, not the composite (calibration_worlds.json, field `best`):

| world | pure power law best | composite best | exponential best |
|---|---|---|---|
| W0-W4 (250 finite-state worlds) | 0 | 125 | 125 |
| W5 recursive hierarchy (50) | 28 | 16 | 6 |

This is consistent with Lin and Tegmark's result: a recursive grammar of this kind gives a power
law, with nothing exponential to add. The published verdict asks for the composite, and in our
worlds the composite is exactly the shape that pooled individuals and bout structure produce.
The pure power law won in no finite-state world here and in 28 of 50 recursive ones. We did not
register that contrast, so it is a lead for a later registered test, not a result.

## Predictions (Brier score)

| id | prediction | prior | outcome |
|---|---|---|---|
| Q1 | W0 primary fire rate at most 0.10 | 0.70 | true (0.06) |
| Q2 | W1 fire rate at least 0.30 | 0.60 | false (0.08) |
| Q3 | W2 fire rate at least 0.30 | 0.80 | true (0.92) |
| Q4 | W3 fire rate at least 0.30 | 0.70 | true (1.0) |
| Q5 | W4 fire rate at least 0.30 | 0.55 | false (0.0) |
| Q6 | W5 fire rate at least 0.80 (positive control passes) | 0.75 | false (0.04) |
| Q7 | grade UNCALIBRATED_MULTI_TIMESCALE or UNCALIBRATED_EVEN_PLAIN_MARKOV | 0.80 | true |

Brier score 0.212 over Q1-Q7 (mean of (outcome - prior)^2). Q8-Q10 belong to stage 2 (house
finch) and are not graded here. Two of our forecasts were wrong in an informative direction: the
two-timescale single bird (W1) and the house-finch design (W4) did **not** fool the verdict. So
in our worlds it is pooling birds with different chains and long same-type bouts that produce a
false composite win, not timescales alone and not repeated fixed songs.

## What this means

The composite (exponential plus power law) verdict, at the strength both papers report, is not
evidence of hierarchy on its own: finite-state song gives it whenever individuals with different
syntax are pooled (W2) or days are made of persistent bouts (W3), and both are features of the
published designs (Sainburg et al. join a day's bouts and fit species curves; Youngblood pools 331
birds). Stage 4 of this study already showed that the real Bengalese finch curve is reproduced by
each bird's own finite-memory syntax ([READING-BF4.md](READING-BF4.md), p 0.4752).

For house finches the result points the other way: our finite-state house-finch design (W4)
almost never gave the composite verdict, so if the real house-finch data do give it (Youngblood
2024 reports a composite win with WAIC), that needs explaining. Stage 2 tests exactly that with
per-bird surrogates; its job has not run yet.

This does not show that birdsong lacks hierarchy. It shows that this curve-shape test cannot
separate hierarchy from pooled or bout-structured finite-state song, and that it misses the
standard recursive model.

## Data manifest

The job also downloaded Youngblood's CC BY 4.0 release (Zenodo record 10786105, zip md5
e5770657a37ebe3d7d0a40461d40ce75, verified) and wrote only the structure of five R data files
([results/stage1/manifest.json](results/stage1/manifest.json), [fetch.json](results/stage1/fetch.json)).
No MI was computed on real songs in stage 1.

## Limits

Simulated worlds are our designs; real song may differ from all six. 50 worlds per scenario.
lmfit is replaced by scipy least_squares from a fixed grid of starts, so fits can differ slightly
from the authors' code. W5 uses one setting of the Lin-Tegmark model (5 symbols, 2 children,
depth 12); other depths or branchings may behave differently. The power-law-only contrast above
is post hoc.

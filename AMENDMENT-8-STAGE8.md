# Amendment 8 (stage 8): is "a pure power law wins" a calibrated signature of hierarchy?

MV2, Munim, Inc. (mv2@munimtech.com). Registered 2026-11-27 by AI agents working in MV2's name,
BEFORE any stage-8 world was simulated and before the outputs of stages 2, 3, 5, 6 and 7 exist
(all five jobs were still queued for compute when this was written). Text CC BY 4.0, code
Apache-2.0. Earlier plan: [PLAN.md](PLAN.md); stage 1 reading: [READING-STAGE1.md](READING-STAGE1.md).

## 1. Why this stage

Stage 1 graded the published hierarchy verdict (the composite exponential-plus-power-law model
wins) as UNCALIBRATED_MULTI_TIMESCALE: it fired in 46 of 50 pooled-bird and 50 of 50 song-type-bout
finite-state worlds, and in only 2 of 50 worlds of the Lin-Tegmark recursive model. In an
**exploratory** count that we had not registered, a different pattern separated the kinds: the
**pure power law** had the lowest AICc in 28 of 50 recursive worlds and in 0 of 250 finite-state
worlds. This is what Lin and Tegmark's theory predicts for recursive grammars, but a pattern found
after looking at the data must be tested on fresh data before it is used. Stage 8 does that, and
it adds the control most likely to break it: a process with **long memory but no hierarchy**.

Prior work (searched 2026-11-27): Lin and Tegmark (Entropy 19:299, 2017; arXiv 1606.06737) prove
exponential decay for finite-state processes and power-law decay for some probabilistic
context-free grammars; Sainburg et al. (Nat Commun 10:3636, 2019) and Youngblood (Proc R Soc B
291:20240250, 2024) read the composite, not a pure power law; Nakaishi et al. (TACL 2026,
arXiv 2505.04984) and arXiv 2610.24334 question or refine the power-law/hierarchy link on text
and fixed-tree languages; Debowski (arXiv 1211.0834) builds heavy-tailed hidden-Markov-type
processes with power-law block information. We found no calibration of the pure-power-law
criterion against the finite-state designs used in birdsong studies, and no test of it against
a heavy-tailed bout process, and no blind application of it to birdsong.

## 2. Criterion and worlds

Pipeline: stage-1 `mi_decay.py`, unchanged (fetched from this repository by `gate8.py`, sha256
logged). **C8 (primary):** the pure power law \(a d^{b} + c\) has the lowest AICc of the three
models (exponential, power law, composite). **Secondary:** C8 and its relative probability is
above 0.999.

50 worlds of each kind, seed 20261127 (stage 1 used 20261124, so every world is new). Each
sequence set is fitted exactly as in stage 1 (d = 1..100, one shuffle per distance).

| kind | class | design |
|---|---|---|
| `F0_plain_markov` | finite-state | stage-1 W0 |
| `F1_two_timescale_markov` | finite-state | stage-1 W1 |
| `F2_pooled_individuals` | finite-state | stage-1 W2 |
| `F3_bout_song_types` | finite-state | stage-1 W3 |
| `F4_house_finch_design` | finite-state | stage-1 W4 |
| `F5_pooled_bout_birds` | finite-state | 10 birds, each with its own W3 song types and 18 own syllables, 3 days of 50 bouts each, pooled |
| `F6_high_order_markov` | finite-state | one bird, order 4 to 8 (drawn per world), 12 syllables, last-order context hashed to one of 2,048 sparse rows (0.7/0.2/0.1), 2% uniform escape; 30 x 4,000 |
| `L1_heavy_tailed_bouts` | long memory, no hierarchy | 3 song types with own 6-syllable chains; bout length Pareto (alpha 1.2, minimum 20, cap 4,000), type changes at every bout end; 30 days of 4,000 |
| `R1_lin_tegmark_k5_d12` | recursive | stage-1 W5 setting (5 symbols, 2 children, depth 12), 30 x 4,096 |
| `R2_lin_tegmark_k8_d12` | recursive | 8 symbols, depth 12 |
| `R3_lin_tegmark_k5_d8_q3` | recursive | 5 symbols, 3 children, depth 8 (6,561 symbols) |
| `R4_recursive_bouts` | recursive | days of 40 short recursive bouts (depth 7, 128 symbols) joined, as birdsong days are |
| `R5_pooled_recursive_birds` | recursive | 30 birds, each with its own grammar and own 5 symbols, pooled |

## 3. Grade (C8 fire rates; rules in `grade8.py`)

- **NOT_SPECIFIC** if any finite-state kind F0-F6 fires at rate 0.20 or more.
- Otherwise, if every finite-state kind fires at rate 0.05 or less and the median rate over
  R1-R5 is 0.50 or more: **CALIBRATED_HIERARCHY_SIGNATURE** when L1 fires below 0.30, and
  **CALIBRATED_LONG_MEMORY_SIGNATURE** when L1 fires at 0.30 or more (C8 then marks long memory,
  not hierarchy as such).
- Otherwise, if every finite-state kind fires at 0.05 or less: **SPECIFIC_BUT_INSENSITIVE**.
- Otherwise **MIXED**.

The secondary (strong) criterion is graded with the same rules and reported beside it. Every
world's AICc values, weights and best model are saved, so any reader can re-grade.

Forecasts (registered probability that each statement is true; scored by Brier):

| id | statement | p |
|---|---|---|
| Q1 | every finite-state kind F0-F6 fires at rate <= 0.05 | 0.60 |
| Q2 | R1 (stage-1 recursive setting, new seed) fires at rate >= 0.40 | 0.70 |
| Q3 | median fire rate over R1-R5 >= 0.50 | 0.45 |
| Q4 | L1 heavy-tailed bouts fires at rate >= 0.30 | 0.65 |
| Q5 | R4 recursive bouts fires at rate >= 0.50 | 0.25 |
| Q6 | R5 pooled recursive birds fires at rate >= 0.50 | 0.45 |
| Q7 | F5 pooled bout birds fires at rate <= 0.05 | 0.55 |
| Q8 | grade is CALIBRATED_HIERARCHY_SIGNATURE | 0.15 |

Our honest expectation: C8 is specific against finite-state designs but also fires on
heavy-tailed bouts, so it marks long memory rather than hierarchy, and short recursive bouts
(R4) are too short for it.

## 4. Blind readout on real song (registered now, read when each stage returns)

For each of stage 2 (house finch), stage 3 (chimpanzee action sequences), stage 5 (Cassin's
vireo), stage 6 (speech) and stage 7 (European starling), C8 is read from that stage's own
outputs: the lowest-AICc model on the real curve and on each of the stage's finite-state
surrogate curves. If an output records only the exponential and composite fits, the three-model
fit is recomputed with `mi_decay.fit_curve` on the saved curves, with no other change; if no
curves are saved, the readout is NOT_MEASURED. `grade8.real_data_readout` gives:
C8_ABSENT (real curve not best fit by the pure power law), C8_PRESENT_NO_SURROGATES,
C8_EXCEEDS_FINITE_STATE (real C8 and at most 5% of surrogates fire) or C8_PRESENT_IN_SURROGATES.

Interpretation, fixed now: C8_EXCEEDS_FINITE_STATE counts as evidence of hierarchy **only** if
the stage-8 grade is CALIBRATED_HIERARCHY_SIGNATURE; under CALIBRATED_LONG_MEMORY_SIGNATURE it
counts as evidence of memory beyond the fitted finite-state syntax, not of hierarchy; under any
other grade it is reported descriptively only.

**Not blind:** stage 4 (Bengalese finch) was graded before this idea existed. Its real curve was
best fit by the composite (READING-BF4.md: composite AICc -847.00 against power law -330.36), so
its readout is C8_ABSENT and it is reported as a non-blind case. The published starling curves of
Sainburg et al. (2019) were seen in that paper; our stage-7 pipeline output has not been.

## 5. Job

`birdsong-stage8-v1`: `python gate8.py /out` (public-copy gate), `python -m unittest -v
test_stage8`, `python stage8.py selftest`, `python stage8.py calibrate --out-dir /out --worlds 50
--seed 20261127`. Outputs: stage8.json (rates, grades, forecast outcomes, Brier),
stage8_worlds.json, stage8_curves.json, gate8.json.

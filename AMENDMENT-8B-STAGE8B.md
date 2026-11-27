# Amendment 8B (stage 8B): does "a pure power law wins" mark hierarchy, or only long memory?

MV2, Munim, Inc. (mv2@munimtech.com). Registered 2026-11-27 by AI agents working in MV2's name,
BEFORE any stage-8B world was simulated. Text CC BY 4.0, code Apache-2.0. Stage 8:
[AMENDMENT-8-STAGE8.md](AMENDMENT-8-STAGE8.md), graded in [READING-STAGE8.md](READING-STAGE8.md).

**This stage is a post-hoc follow-up, and we say so plainly.** It was designed after we saw the
stage-8 grade (MIXED). Stage 8 does not change: its grade stands as registered. Stage 8B uses a new
seed, so every world is new, and it is graded by its own rules, fixed here.

## 1. Why this stage

Stage 8 tested criterion C8 (the pure power law \(a d^{b} + c\) has the lowest AICc of the
exponential, power-law and composite models) as a signature of recursive hierarchy in
mutual-information decay curves. It fired in 133 of 250 recursive worlds and 5 of 350
finite-state worlds. But pooled finite-state birds (`F2_pooled_individuals`) fired in 3 of 50, a
rate of 0.06, just past the registered limit of 0.05; with 50 worlds the exact 95% interval runs
from about 0.01 to about 0.17, so the test could not tell 0.04 from 0.06. The only long-memory
control (Pareto bouts on disjoint song-type alphabets) fired in 0 of 50, and the strong criterion
(relative probability above 0.999) could never fire, because the composite contains the power law
and so caps its relative probability near 0.90.

Three questions are left, and they decide whether C8 can be used on real song at all:

1. **Is the pooled-birds false-alarm rate really at or below 5%?** 400 fresh F2 worlds pin it to
   within about 0.02.
2. **Does C8 fire on long memory with no hierarchy?** Quantized fractional Gaussian noise (fGn)
   has power-law correlations and no grammar or tree; a shared-alphabet heavy-tailed bout process
   has long memory without a separate alphabet per song type. If either fires, C8 marks long memory,
   not hierarchy, and no MI-decay curve shape tested so far can certify hierarchy.
3. **Can a reachable strong criterion keep the detection rate?** C8R asks that the power law also
   beat the exponential by at least 10 AICc units.

The wow, if C8 passes all three, would be the first calibrated MI-decay signature of hierarchy
that can be applied to any animal sequence. If it fails question 2, the result is that neither the
published composite verdict nor its pure-power-law replacement separates hierarchy from long memory.

Prior work (searched 2026-11-27): Lin and Tegmark (Entropy 19:299, 2017) prove exponential decay
for finite-state processes and power-law decay for some probabilistic grammars; fGn is the standard
long-range-correlated process (autocovariance about \(H(2H-1)k^{2H-2}\), Mandelbrot and Van Ness
1968), used as a null for long-range correlation in DNA and spike trains but, in our searches, never
to calibrate the MI-decay hierarchy test on animal sequences. Howard-Spink et al. (PeerJ 12:e18484,
2024) measured how often one community Markov chain picks a model with a power law (about 41%) on
chimpanzee actions. Nakaishi et al. (TACL 2026, arXiv 2505.04984) question the power-law/hierarchy
link on text. We found no calibration of the pure-power-law criterion against long-memory processes
without hierarchy.

## 2. Criteria and worlds

Pipeline: the stage-1 `mi_decay.py` and the stage-8 world generators in `stage8.py`, unchanged
(fetched from this repository by `gate8b.py`, sha256 logged). Each sequence set is fitted exactly as
in stages 1 and 8 (d = 1..100, one shuffle per distance).

- **C8 (primary):** the pure power law has the lowest AICc of the three models (as in stage 8).
- **C8R (secondary, reachable):** C8, and AICc(exponential) - AICc(power law) >= 10.

Seed 20261128 (stage 8 used 20261127, stage 1 used 20261124).

| kind | class | worlds | design |
|---|---|---|---|
| `F2_pooled_individuals` | finite-state | 400 | stage-1 W2: 30 birds, each its own 12-syllable sticky group chain, own alphabet, pooled |
| `F6_high_order_markov` | finite-state | 100 | stage-8 F6: order 4 to 8, 12 syllables |
| `F7_pooled_shared_alphabet` | finite-state | 100 | as F2, but all 30 birds use ONE shared 12-syllable alphabet |
| `L2_fgn_h07` | long memory, no hierarchy | 100 | fGn with Hurst H 0.7 (Davies-Harte), each sequence quantized into 8 equiprobable bins; 30 x 4,000 |
| `L3_fgn_h09` | long memory, no hierarchy | 100 | as L2 with H 0.9 |
| `L4_shared_alphabet_heavy_bouts` | long memory, no hierarchy | 100 | 3 regimes, each its own irreducible chain over the SAME 12 syllables; Pareto (alpha 1.5, minimum 20, cap 4,000) regime durations; 30 days of 4,000 |
| `R1_lin_tegmark_k5_d12` | recursive | 100 | stage-8 R1 |
| `R5_pooled_recursive_birds` | recursive | 100 | stage-8 R5 |

That is 400 + 7 x 100 = 1,100 worlds.

## 3. Grade (rules in `grade8b.py`; applied to C8 and to C8R separately)

For each finite-state kind, the fire rate and its exact (Clopper-Pearson) two-sided 95% interval.

- **NOT_SPECIFIC** if any finite-state kind has a lower 95% bound above 0.05.
- Otherwise, the false-alarm rule passes when every finite-state kind has a rate of at most 0.05
  AND an upper 95% bound of at most 0.10 (with 100 worlds this needs at most 4 fires; with 400, at
  most 20). The detection rule passes when each recursive kind fires at a rate of at least 0.40.
  - Both pass: **CALIBRATED_HIERARCHY_SIGNATURE** if every long-memory kind L2-L4 fires below 0.30,
    **CALIBRATED_LONG_MEMORY_SIGNATURE** if any fires at 0.30 or more.
  - Only the false-alarm rule passes: **SPECIFIC_BUT_INSENSITIVE**.
  - Otherwise: **UNRESOLVED**.

The C8 grade is primary. Every world's AICc values, weights, best model and the exponential's AICc
deficit are saved (`stage8b_worlds.json`), so any reader can re-grade. The published composite
verdict (composite best with relative probability above 0.999) is counted beside both, descriptively.

Forecasts (registered probability that each statement is true; scored by Brier):

| id | statement | p |
|---|---|---|
| Q1 | F2 pooled individuals fires C8 at rate <= 0.05 over 400 worlds | 0.70 |
| Q2 | every finite-state kind passes the C8 false-alarm rule | 0.45 |
| Q3 | L2 fGn H 0.7 fires C8 at rate >= 0.30 | 0.75 |
| Q4 | L3 fGn H 0.9 fires C8 at rate >= 0.30 | 0.75 |
| Q5 | L4 shared-alphabet heavy bouts fires C8 at rate >= 0.30 | 0.35 |
| Q6 | R1 fires C8R at rate >= 0.40 | 0.55 |
| Q7 | C8 grade is CALIBRATED_HIERARCHY_SIGNATURE | 0.10 |
| Q8 | C8 grade is CALIBRATED_LONG_MEMORY_SIGNATURE | 0.35 |

Our honest expectation: quantized fGn gives an almost pure power-law MI curve, so C8 fires on it
and marks long memory rather than hierarchy. Our record of expectations in this repository is poor
(stage-8 Brier 0.2831), so we hold this one loosely.

## 4. What the grade means for the real-song stages (fixed now)

AMENDMENT-8 section 4 stays in force for the readouts of stages 2, 3, 5, 6 and 7. Stage 8B adds one
rule: if the stage-8B C8 grade is CALIBRATED_HIERARCHY_SIGNATURE, a real-song readout of
C8_EXCEEDS_FINITE_STATE is reported as **evidence consistent with hierarchy, conditional on stage
8B**, still marked post hoc, because stage 8 itself was MIXED. Under
CALIBRATED_LONG_MEMORY_SIGNATURE it is evidence of memory beyond the fitted finite-state syntax, not
of hierarchy. Under any other grade the readouts stay descriptive only.

## 5. Job

`birdsong-stage8b-v1`: `python gate8b.py /out` (public-copy gate), `python -m unittest -v
test_stage8b`, `python stage8b.py selftest`, `python stage8b.py calibrate --out-dir /out --seed
20261128`. Outputs: stage8b.json (fire counts, grades, forecast outcomes, Brier),
stage8b_worlds.json, stage8b_curves.json, gate8b.json.

## 6. Limits fixed in advance

Simulated worlds are our designs. fGn is one long-memory family and Lin-Tegmark trees are one
hierarchical family. Quantizing a Gaussian process into 8 bins is a crude model of a syllable
sequence. Passing here would show C8 is calibrated against these worlds, not against every process
real birds might use.

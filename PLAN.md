# birdsong-mi-decay-test: does the "power-law tail means hierarchy" test fire on finite-state song?

Pre-registered 2026-11-24 by MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents working
in his name. This plan was registered BEFORE any data was opened and before any simulation was run.
Licence: code Apache-2.0; text CC BY 4.0.

## The claims

1. **Sainburg, Theilman, Thielk and Gentner (2019), Nature Communications 10:3636,** "Parallels
   in the sequential organization of birdsong and human speech" (PMC6690877). Mutual information
   (MI) between song syllables decays with their distance in the sequence. In all four songbird
   species a composite model (exponential plus power law) fit that decay better than an
   exponential alone (AICc; relative probability above 0.999). The paper reads the exponential
   part as Markovian and the power-law part as "consistent with underlying hierarchical
   processes", following Lin and Tegmark's result that any probabilistic regular grammar
   (finite-state Markov or hidden-Markov process) gives exponential MI decay.
2. **Youngblood (2024), Proceedings of the Royal Society B 291:20240250,** "Language-like
   efficiency and structure in house finch song" (PMC10987240). The same method, applied to 2,724
   songs of 331 house finches with each bird's songs joined into one sequence, again preferred
   the composite model (WAIC), which the paper reads as consistent with a mix of Markovian and
   hierarchical processes. Within single songs the exponential model won.

## Why this needs a calibrated test

Lin and Tegmark's statement is asymptotic: a finite-state process decays exponentially *at
large enough distance*, with the slowest rate set by its second-largest eigenvalue. Over a window
of 1 to 100 syllables, a finite-state process with **several timescales** (syllable transitions,
phrases, bouts of one song type) gives a sum of exponentials, and **pooling individuals or days**
whose Markov chains decay at different rates gives a mixture of exponentials, a classic way to
produce power-law-like curves. Both studies pool (Sainburg et al. join every syllable of a day into
one sequence and also fit whole-species curves; Youngblood pools 331 birds), and neither compared
the composite verdict with finite-state surrogates fitted to the same design. Sainburg et al.'s
own Markov controls were two published Bengalese finch chains, not processes with bout or
individual structure. We found no published calibration of this diagnostic against
multi-timescale or pooled finite-state processes (web and Europe PMC searches, 2026-11-24; the
closest work, Morita et al. 2021 PLoS Comput Biol 17:e1009707, measures context length with
neural networks and does not calibrate the MI test).

## Stage 1 (this registration): calibration in simulated worlds, plus a data manifest

Pipeline (`mi_decay.py`), re-implemented from the paper and its public code
(github.com/timsainb/ParallelsBirdsongLanguagePaper): MI by their digamma estimator, one
within-sequence shuffle per distance as the baseline, sig(d) = MI - baseline at d = 1..100,
points with sig <= 0 dropped, exponential / power-law / composite fits on log residuals scaled by
1/log(1+d) with their bounds (scipy least_squares from a fixed grid of starts instead of lmfit),
AICc with 3 / 3 / 5 parameters.

**Primary fire criterion:** the composite has the lowest AICc AND its relative probability is
above 0.999 (the paper's reported strength). Secondary: the composite has the lowest AICc.

Worlds (50 each, seed 20261124; every sequence comes from a finite-state process except W5):

| id | what it is | design |
|---|---|---|
| W0 | plain first-order Markov chain | 12 syllables, each row puts 0.7/0.2/0.1 on 3 random syllables (irreducible), 30 sequences of 4,000 |
| W1 | one bird, two timescales | first-order chain on 3 phrase groups of 4 syllables; stay in group with prob 0.9, else jump uniformly to another group's syllable; 30 x 4,000 |
| W2 | 30 pooled individuals | as W1 but each bird has its own matrices, own alphabet and own stay prob drawn U(0.5, 0.99); one sequence of 4,000 per bird |
| W3 | day = bouts of song types | 3 song types with 6 own syllables and own sparse chains; bout type persists with prob 0.8, else switches; bout length 20 + Poisson(60); 50 bouts per day, 30 days joined per day as in Sainburg et al. |
| W4 | house-finch design | 331 birds; 1-3 fixed song strings per bird (length 6-31) over 114 shared syllable types with Zipf frequencies; 1 + Poisson(7.23) songs per bird; same song again with prob 0.7; 5% syllable substitution; each bird's songs joined |
| W5 | recursive hierarchy (positive control) | Lin-Tegmark model as in Sainburg et al.: 5 symbols, 2 children per symbol, depth 12, 30 sequences of 4,096 |

**Grade of the diagnostic** (primary fire rates; UNSAFE >= 0.30, SAFE <= 0.10, as in MV2's
calibrated-animal-claims ledger):
- W0 >= 0.30: UNCALIBRATED_EVEN_PLAIN_MARKOV.
- else any of W1-W4 >= 0.30: UNCALIBRATED_MULTI_TIMESCALE (the composite verdict does not
  separate recursive hierarchy from finite-state song with more than one timescale or pooled birds).
- else W0-W4 all <= 0.10: CALIBRATED.
- else MIXED.
- Positive control passes if W5 >= 0.80; if it fails, the reimplementation is reported as unable
  to see the hierarchy it should, and the grade is reported with that caveat.

**Data manifest:** the job downloads the authors' CC BY 4.0 release (Zenodo 10689807, version
record 10786105, zip md5 e5770657a37ebe3d7d0a40461d40ce75) and writes only the structure of five R
data files (object names, classes, shapes, column names, dtypes, distinct-value counts). No MI is
computed on real songs in stage 1.

## Stage 2 (design registered now; loader registered as AMENDMENT-1 after the manifest)

On the house-finch data, using each bird's songs joined in recording order as in the paper, at
syllable clustering level DS = 2 (primary), 3 and 4:
- **T2a replication:** the composite verdict on the real curve (primary criterion).
- **T2b song order:** the same after permuting the ORDER of each bird's songs (songs kept intact),
  100 permutations; fire rate and the real exp-minus-composite AICc difference against them.
- **T2c finite-state surrogates:** per bird, a repeat-or-redraw song process (the next song repeats
  the previous song's string with that bird's observed repeat rate, else is drawn from the bird's
  own songs), 100 surrogate datasets; fire rate, and where the real AICc difference falls.
- Grade: FINITE_STATE_SUFFICES if T2c fires in >= 50% of surrogates and the real AICc
  difference lies below the surrogates' 95th percentile; EXCEEDS_FINITE_STATE if it lies above
  their 95th percentile; else UNRESOLVED. The authors' own MI curve (mi_data.RData), if it
  holds the curve, is refitted with this pipeline as a check of the reimplementation.
Sainburg et al.'s Bengalese finch, thrasher and vireo data (Bird-DB / figshare) may follow as a
later amendment, registered before access.

## Predictions (priors, graded with the Brier score)

| id | prediction | prior |
|---|---|---|
| Q1 | W0 primary fire rate <= 0.10 | 0.70 |
| Q2 | W1 fire rate >= 0.30 | 0.60 |
| Q3 | W2 fire rate >= 0.30 | 0.80 |
| Q4 | W3 fire rate >= 0.30 | 0.70 |
| Q5 | W4 fire rate >= 0.30 | 0.55 |
| Q6 | W5 fire rate >= 0.80 (positive control passes) | 0.75 |
| Q7 | grade is UNCALIBRATED_MULTI_TIMESCALE or UNCALIBRATED_EVEN_PLAIN_MARKOV | 0.80 |
| Q8 | (stage 2) T2a: the composite verdict replicates on the real DS = 2 curve | 0.85 |
| Q9 | (stage 2) T2b: it still fires in >= 50% of song-order permutations | 0.55 |
| Q10 | (stage 2) grade FINITE_STATE_SUFFICES | 0.55 |

## What would and would not follow

If the diagnostic fires on finite-state worlds, the composite fit alone cannot show hierarchical
(beyond finite-state) structure in birdsong, in these two papers or in later ones using the
method; it would then need a fitted finite-state null like T2c. It would NOT show that birdsong
lacks hierarchy: other evidence (for example neural-network context-length measures) is
untouched. If the diagnostic stays quiet in W1-W4, that is a useful positive result for the
method and we will say so.

## Deviations already known

lmfit's optimizers are replaced by scipy least_squares (trf) from a fixed start grid; Youngblood
fitted with brms and compared WAIC, while we use Sainburg et al.'s AICc throughout (a stated
difference, not a replication of brms). Their estimator mixes log2(N) with natural-log digamma;
we keep it, and it cancels in MI minus shuffled MI (unit test).

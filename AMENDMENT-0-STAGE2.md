# Amendment 0: stage-2 code and a self-check of the finite-state surrogate

Registered 2026-11-24 by MV2 of Munim, Inc. (mv2@munimtech.com), BEFORE any stage-1
result came back and BEFORE any house-finch data file was opened by anyone on MV2's side.
Made with AI agents. Licence: Apache-2.0 (code), CC BY 4.0 (text).

## What this adds

`mi_stage2.py` implements T2a, T2b and T2c of PLAN.md on a loader-agnostic input
(per bird: its songs in recording order, each a list of syllable labels). It reuses the
registered stage-1 core `mi_decay.py` (git blob 83d578e3d03d130ac31f5cb4da5b3eb9bb077659)
for the MI curve, the three fits, AICc and the firing rule; `get_core.py` fetches that file
and refuses any other bytes. The stage-2 loader (Amendment 1) is still to be written from
the structure-only manifest of the Zenodo files.

## Binding readings of PLAN.md (fixed now, before data)

1. **Sequences.** One sequence per bird: its songs joined in recording order (Youngblood's
   design). Lagged pairs never cross birds (as in `mi_decay.mi_at`).
2. **T2b.** 100 permutations of each bird's song order, songs kept intact. Reported: the
   share of permutations whose curve fires (strong criterion) and the upper-tail p of the
   real exp-minus-composite AICc gap among the permuted gaps.
3. **T2c (as registered).** "Repeat" means the next song is identical, label for label, to
   the previous one at that DS level. The bird's observed repeat rate r is the share of its
   consecutive song pairs that are identical. Surrogate: first song drawn from the bird's own
   songs; then with probability r repeat the previous song, otherwise draw among the bird's
   songs that differ from the previous one, with their observed multiplicities (so the
   surrogate keeps r in expectation). Birds with one song keep it. 100 surrogate datasets.
4. **Grades** exactly as PLAN.md: EXCEEDS_FINITE_STATE if the real gap is above the 95th
   percentile (numpy linear) of the surrogate gaps; FINITE_STATE_SUFFICES if surrogates fire
   in at least 50% and the real gap is below it; otherwise UNRESOLVED. Also UNRESOLVED if the
   real gap is undefined or fewer than 20 surrogate gaps are finite. EXCEEDS means "exceeds
   this repeat-or-redraw model", not "proves hierarchy".

## Why a self-check, and the secondary test T2c-type

Exact identity is fragile: if renditions of one song type differ by a syllable or two (noisy
singing, or clustering noise at DS 3 and 4), exact repeats look rare, the surrogate loses the
bird's real type persistence, and the real curve could beat the surrogates for a trivial
reason. So we add **T2c-type**: within each bird, songs at normalised edit distance at most
0.34 are joined into one type (single linkage); the surrogate repeats or redraws TYPES at the
observed type-repeat rate, and each surrogate song is a random real rendition of its type.

**Self-check (job birdsong-mi-s2check-v1).** House-finch-shaped synthetic data in the shape of
Youngblood 2024 (331 birds, 114 syllable types, 8.23 songs per bird; 2 to 5 song types per
bird, each a random string of 6 to 12 syllables). 16 worlds each, 50 surrogates per test:

| World | Song order | Rendition noise | Role |
|---|---|---|---|
| F0 | repeat-or-redraw, repeat 0.7 | none | null, exact model of T2c |
| F1 | repeat-or-redraw, repeat 0.7 | 5% syllables substituted | null with noisy renditions |
| F2 | strict cycle A B C ... | none | finite-state but not repeat-or-redraw (power) |

Rules, fixed now: a test is **calibrated** if it grades EXCEEDS in at most 2 of 16 worlds
(0.125) in F0 AND in F1. Stage-2 primary test = T2c if calibrated; else T2c-type if
calibrated; else the stage-2 surrogate grade is reported as UNCALIBRATED and the stage-2
verdict is UNRESOLVED whatever the data show. Power = share of F2 worlds graded EXCEEDS
(reported, no threshold; with 2-type birds a cycle equals the surrogate, so power is capped).
The share of null worlds in which the composite fires (T2a) is reported as a stage-2 analogue
of stage-1 world W4, with renditions.

## Priors (Brier-scored when the self-check returns)

| | Prediction | P |
|---|---|---|
| S1 | T2c calibrated in F0 (EXCEEDS in at most 2 of 16) | 0.85 |
| S2 | T2c calibrated in F1 | 0.35 |
| S3 | T2c-type calibrated in F0 and F1 | 0.75 |
| S4 | T2c-type power in F2 at least 0.5 | 0.50 |
| S5 | The composite fires (strong) in at least half of the F0 worlds | 0.60 |

## Related work found while writing this

Nakaishi, Yoshida, Kajikawa, Hukushima and Oseki, "Rethinking the Relationship between the
Power Law and Hierarchical Structures" (arXiv 2505.04984; TACL 14, 2026) test the
assumptions of the power-law-implies-hierarchy argument on English and Japanese parse trees
and find they do not hold for syntax; they name birdsong as a domain where the argument has
been applied but analyse no birdsong. They do not test the composite-fit diagnostic itself on
finite-state nulls, which is what this project does. Two further users of the diagnostic are
candidates for a later amendment: chimpanzee action sequences (bioRxiv 10.1101/2024.03.25.586385)
and wild meerkat, coati and hyena behaviour sequences (bioRxiv 10.1101/2024.01.20.576411).

## Limits

The self-check tests the surrogate machinery, not birds. Real house-finch songs may carry
structure none of these worlds has (shared syllables across types, drifting song length).
The edit-distance threshold 0.34 was chosen before data so that two renditions of a 6-syllable
song differing in 2 syllables still count as one type.

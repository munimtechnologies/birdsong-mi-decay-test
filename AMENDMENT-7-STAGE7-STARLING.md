# Amendment 7: stage 7, European starling song against a fitted finite-memory null

MV2, Munim, Inc. (mv2@munimtech.com). Pre-registered 2026-11-26 by AI agents working in MV2's
name; no human expert has checked it. Text CC BY 4.0, code Apache-2.0.

This plan was registered BEFORE any starling audio was downloaded by this study.
Marker for the job's gate (one line): registered BEFORE any starling audio was downloaded by this study

## Why this stage

Sainburg, Theilman, Thielk and Gentner (2019, Nat Commun 10:3636,
https://doi.org/10.1038/s41467-019-11605-y) fitted exponential, power-law and composite
(exponential + power-law) models to the decay of mutual information (MI) between song syllables
in four songbird species and read the composite winner as Markov structure at short range plus
hierarchical structure at long range. Their Markov controls were published chains, not models
fitted to each bird.

Stage 4 of this study ([READING-BF4.md](READING-BF4.md)) tested their Bengalese finch data: the
composite verdict fired in 100 of 100 surrogate datasets generated from each bird's own fitted
k-gram syntax, and the real result sat in the middle of them (p 0.4752; grade
FINITE_STATE_SUFFICES). Stage 5 (Cassin's vireo) is queued. The paper's other two species:

* **California thrasher:** the data came from Bird-DB (taylor0.biology.ucla.edu/birdDBQuery/),
  whose host no longer resolves (checked 2026-11-26); we found no public copy. Not testable now.
* **European starling:** the recordings are public (Zenodo record 3237218, CC BY 4.0, "An
  acoustically isolated European starling song library", Arneodo, Sainburg, Jeanne and Gentner),
  but the syllable labels the paper used came from the authors' own UMAP clustering and were not
  released. This stage therefore segments and labels the audio itself, as close to the authors'
  public pipeline as we can, and then runs the stage-4 tests unchanged.

Starling song is the species in which long-range structure is most often claimed (long bouts of
whistles, variable motifs, rattles and high-frequency motifs), so it is the strongest remaining
test of the paper's inference.

Prior work searched on 2026-11-26 (Google, Semantic Scholar via search, arXiv, GitHub, Zenodo):
no published test of the starling MI-decay result against models fitted to each bird. Closest:
Nakaishi et al. 2025 (arXiv 2505.04984), who question the power-law/hierarchy link using parse
trees and probabilistic grammars, not birdsong surrogates; Youngblood 2024 (Proc R Soc B
291:20240250), who used the same composite test on house finches without fitted surrogates; and
this study's own stages.

## Data and the four birds

Zenodo record 3237218 has one zip per bird (audio as `<bird>/wavs/YYYY-MM-DD_HH-MM-SS-ffffff.wav`,
plus small csv files and spectrogram jpgs that this stage does not read). Ten birds were recorded
in 2017-2018 by Arneodo and Sainburg with one system, four in 2008 by Jeanne with another. To keep
one recording system and a job that fits a shared machine, the stage uses the **four smallest
archives among the ten 2017-2018 birds**, chosen by file size from the Zenodo listing before any
audio was opened: b1125 (663,236,091 bytes), b1160 (971,031,800), b1077 (1,558,979,170) and
b1066 (1,644,978,624). Each archive's md5 is checked against Zenodo's. Archives are deleted after
features are extracted; nothing from them is redistributed.

## Pipeline (code: starling_stage7.py; reused code pinned by git blob in get_files7.py)

1. **Segmentation.** Sainburg's vocalseg (github.com/timsainb/vocalization-segmentation, MIT,
   commit 8bc85ee9bb644cc5928535959faee5e5b184dd36), `dynamic_threshold_segmentation`, with the
   parameters of his public starling notebook (avgn_paper, branch V2,
   notebooks/01.1-syllabic-segmentation/starling-syllable-segmentation.ipynb): 500-15000 Hz
   Butterworth bandpass, n_fft 1024, hop 1 ms, window 5 ms, ref 20 dB, pre-emphasis 0.97,
   min_level_db -100 rising to -60 in 5 dB steps, silence threshold 0.01, min silence 0.1 s, max
   vocal run 2.0 s, min syllable 0.15 s. Files longer than 45 s are segmented in consecutive 30 s
   pieces (memory; counted in the load report).
2. **Features.** Per syllable: 32-band mel power spectrogram (500-15000 Hz, 10 ms window, 3 ms
   hop) in dB relative to the syllable's own peak, floored at -80 dB, scaled to [0, 1] and
   linearly resampled to 32 time steps (1,024 numbers).
3. **Labels, per bird.** PRIMARY: PCA to 50 dimensions, UMAP to 2 (15 neighbours, min_dist 0.1),
   HDBSCAN (min cluster size 1% of the bird's syllables, at least 25; min_samples 1); the noise
   label is kept as a symbol, as in Sainburg's sequence code. ROBUSTNESS: k-means with k = 30 on
   the same 50 PCA dimensions. Seeds fixed (20261126).
4. **Bouts and days.** A bird's syllables in time order (file start time from the file name plus
   onset); a new bout starts when an onset follows the previous onset by more than 10 s
   (Sainburg's isi_thresh = 10) or on a new calendar day. Day sequence = the day's bouts joined in
   time order (as in stage 4). Symbols are (bird, label) pairs.

## Tests (the stage-4 code, imported unchanged from bf_stage4.py)

* **T7a:** the composite verdict (stage-1 core) on the real curve pooled over bird-days.
* **T7b:** the same after permuting bout order within each bird-day, 100 times (p_order).
* **T7c:** per-bird k-gram (k = 1..8 by 5-fold held-out likelihood, Witten-Bell), 100 surrogate
  datasets of independent bouts in the real design. EXCEEDS_FINITE_STATE if the real
  exponential-minus-composite AICc gap is above the surrogates' 95th percentile;
  FINITE_STATE_SUFFICES if the surrogates fire in at least half and the real gap is below it;
  otherwise UNRESOLVED.
* **Self-check (design-matched):** the stage-4 synthetic worlds S0 (in-class chain), S1 (phrase
  machine), S3 (cross-bout persistence) and S4 (recursive hierarchy, positive control), sung into
  the REAL starling design (same birds and bouts per day on each bird's 6 days with the most
  bouts, at most 100 bouts per bird-day, to bound the run time), 12 worlds each, 20
  permutations and 40 surrogates per world. T7c counts as calibrated if it
  says EXCEEDS in at most 12.5% of S0 worlds and of S1 worlds.

## Grades (per arm; the PRIMARY arm is the result)

UNRESOLVED_UNCALIBRATED if the self-check fails; FINITE_STATE_SUFFICES; CROSS_BOUT_ORDER
(EXCEEDS and p_order <= 0.05); WITHIN_BOUT_EXCESS (EXCEEDS and p_order > 0.05); otherwise
UNRESOLVED. If HDBSCAN finds fewer than 5 clusters for any bird the primary grade is
UNRESOLVED_LABELS and only the k-means arm is reported. LOADER_STOP if an archive fails its md5,
fewer than 90% of a bird's files can be read, a bird has fewer than 2 days or 20 bouts, or there
are fewer than 10,000 syllables in all.

## Predictions (Brier-scored by the job)

| id | prediction | prior |
|---|---|---|
| C1 | the composite verdict fires on the real (primary) curve | 0.85 |
| C2 | k >= 3 is chosen for at least 3 of the 4 birds (primary) | 0.60 |
| C3 | the design-matched self-check calibrates T7c | 0.65 |
| C4 | at least half of the bout-order permutations still fire | 0.60 |
| C5 | primary grade FINITE_STATE_SUFFICES | 0.40 |
| C6 | primary and k-means arms give the same grade | 0.60 |
| C7 | S4 (hierarchy) power >= 0.5 | 0.80 |
| C8 | S3 (cross-bout) EXCEEDS rate >= 0.5 | 0.80 |

## What each outcome would mean

* FINITE_STATE_SUFFICES in starlings too would mean that, in both species with labelled or
  labelable public data, the curve shape the paper reads as hierarchy is produced by each bird's
  own short-memory syntax. It would NOT show that starling song lacks hierarchy; it would show
  that this MI-decay evidence cannot tell.
* EXCEEDS_FINITE_STATE would be the first calibrated evidence, in any species of the paper, that
  the MI curve carries structure beyond an 8-syllable memory; CROSS_BOUT_ORDER vs
  WITHIN_BOUT_EXCESS says whether it lives in the order of bouts or inside them.

## Deviations and limits (registered)

* Our segmentation follows the authors' public starling notebook, but our features, UMAP/HDBSCAN
  settings and the k-means arm are our own registered choices; the paper's labels are not public,
  so its exact symbol sequences cannot be reproduced.
* Four of fourteen birds, one recording system; files longer than 45 s are cut into 30 s pieces
  for segmentation.
* One finite-state model class (k-gram up to 8, independent bouts), as in stage 4.
* AI agents wrote the code and will read the result; no human expert has checked either.

## Job

`birdsong-mi-starling-v1` (python:3.12, 3 GB, network for the Zenodo download): gate (this file
and the exact starling_stage7.py must be public), pinned reuse of mi_decay.py and bf_stage4.py,
dependency check, unit tests, load, self-check, stage 7, grade. Outputs: load_report7.json,
selfcheck7.json, selfcheck7_worlds.json, stage7_results.json, grade7.json.

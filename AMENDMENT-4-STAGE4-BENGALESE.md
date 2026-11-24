# AMENDMENT 4: stage 4, Bengalese finch song against a fitted finite-memory null

Pre-registered 2026-11-24 by MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents working
in his name; no human expert has reviewed it. This amendment was registered BEFORE any Bengalese finch annotation was downloaded
or opened, and before any result of stages 1, 2 or 3 came back (all three jobs were still
queued when it was written). Code Apache-2.0; text CC BY 4.0.

## Why a stage 4

Stages 1 to 3 ask whether the exponential-plus-power-law ("composite") verdict on mutual-information
(MI) decay also fires on finite-state sequences (stage 1, simulated worlds), on house finch song
against song-level surrogates (stage 2), and on chimpanzee action sequences against hidden Markov
models (stage 3). None of them touches the species of the original claim. Sainburg, Theilman,
Thielk and Gentner (2019, Nat Commun 10:3636) list the Bengalese Finch Song Repository (Nicholson,
Queen and Sober; figshare 4805749, CC BY 4.0) as their Bengalese finch source in the README of
their public code (github.com/timsainb/ParallelsBirdsongLanguagePaper). Their Markov controls were
published Bengalese finch chains run as long single sequences, not models fitted to each bird and
given the paper's own design (days pooled, bouts joined). The same reading of the composite fit is
now also used as a benchmark measure for "supra-regular" structure (SymSeqBench, arXiv 2512.24977).

Prior-work search 2026-11-24 (web search, arXiv, Europe PMC; queries on conditional MI and
entropy convergence in birdsong, composite MI decay with finite-state surrogates, mixtures of
Markov chains as a null for power-law MI): no published test of the composite verdict on
Bengalese finch song against per-bird fitted finite-state surrogates with the paper's design.
Closest: Morita et al. 2021 (PLoS Comput Biol 17:e1009707) measure context length with neural
networks and do not test the MI verdict; Howard-Spink et al. 2024 (PeerJ 12:e18484) estimate false
positives with first-order Markov models on chimpanzee actions (our stage 3); Nakaishi et al.
(arXiv 2505.04984) question the power-law-to-hierarchy argument for human syntax.

## Data and loader (binding)

- The 18 `sober.repo1.<bird>.<mmddyy>.wav.csv.tar.gz` archives of figshare 4805749 version 9
  (birds bl26lb16, gr41rd51, gy6or6, or60yw70). File ids and md5s are read from figshare's API
  (`/v2/articles/4805749/versions/9`) at run time; each archive is streamed and its md5 checked
  against figshare's computed_md5. Only CSV members are kept (macOS `._` files skipped); audio is
  never written to disk.
- Each CSV is one annotated file = one **bout**; labels (crowsetta simple-seq: `onset_s`,
  `offset_s`, `label`) are put in onset order; empty labels are dropped; files with no labels
  are not bouts. A **day sequence** is all bouts of one archive (bird and day) joined in
  member-name order. Symbols are (bird, label) pairs, because labels mean nothing across birds.
  No label is excluded (introductory notes `i` are kept).
- **Loader stop** (writes `load_report4.json` with counts only and grades LOADER_STOP) if: not
  18 archives; any md5 mismatch; more than 1% of CSVs lack the three columns; fewer than 10,000
  syllables; or any of the 4 birds has fewer than 2 days or 20 bouts.

## Tests (binding)

The MI curve, shuffle baseline, fits and firing rule are the registered stage-1 code
(`mi_decay.py`, git blob 83d578e3d03d130ac31f5cb4da5b3eb9bb077659). The statistic is the
exponential-minus-composite AICc gap, as in stage 2.

- **T4a replication:** composite verdict (primary: lowest AICc and relative probability above
  0.999) on the real curve, all 18 day sequences pooled.
- **T4b bout order:** the same after permuting the order of bouts within each day, 100 times;
  `p_order` = share (with +1 correction) of permutations whose gap is at least the real gap.
- **T4c finite-memory null:** for each bird, a k-th order Markov model of bouts (START padding,
  an END outcome, Witten-Bell interpolation down to an add-one unigram over the bird's own
  symbols), k from 1 to 8 chosen by 5-fold held-out log-likelihood (bout i in fold i mod 5; ties
  to the smaller k). Each surrogate draws every bout independently from its bird's model
  (non-empty, capped at twice the bird's longest bout) with the real number of bouts per day.
  100 surrogate datasets. Grade as stage 2: EXCEEDS_FINITE_STATE if the real gap is above the
  surrogates' 95th percentile; FINITE_STATE_SUFFICES if the surrogates fire in at least 50% and
  the real gap is below it; else UNRESOLVED (also with fewer than 20 finite surrogate gaps).

**Self-check of T4c (runs first in the same job; seed 20261124; 12 worlds per kind; 4 birds x 5
days x 60 bouts; 40 surrogates and 20 bout-order permutations per world):**
- S0 in-class: per-bird second-order chain (10 syllables, 0.7/0.2/0.1 on three next syllables,
  bout ends with probability 0.04 after each syllable).
- S1 finite-state but outside the k-gram class: per-bird phrase machine (4 fixed phrases of 2-4
  syllables, each sung Geometric(0.35) times, sparse first-order phrase transitions, bout ends
  with probability 0.12 after each phrase block).
- S3 cross-bout persistence (finite-state): 3 bout types with their own second-order chains; the
  type persists from bout to bout with probability 0.8.
- S4 within-bout recursive hierarchy (positive control): every bout is a Lin-Tegmark sequence (5
  symbols, 2 children, depth 5).
- **T4c is calibrated** if it grades EXCEEDS in at most 12.5% of S0 worlds and of S1 worlds. S3
  and S4 rates are reported as scope and power, with no threshold.

**Final grade:**
- self-check not calibrated: UNRESOLVED_UNCALIBRATED (results reported, no verdict);
- T4c FINITE_STATE_SUFFICES: **FINITE_STATE_SUFFICES** (the Bengalese finch composite verdict is
  reproduced by per-bird finite-memory syntax with independent bouts; it gives no evidence of
  structure beyond that);
- T4c EXCEEDS and p_order <= 0.05: **CROSS_BOUT_ORDER** (the excess needs the real order of bouts;
  this could still be finite-state persistence, see S3; a persistence null would be stage 5);
- T4c EXCEEDS and p_order > 0.05: **WITHIN_BOUT_EXCESS** (long-range structure inside bouts beyond
  an 8-syllable memory; consistent with, not proof of, hierarchy);
- otherwise UNRESOLVED.

Cassin's vireo (Hedley 2016, figshare 3081814, CC BY 4.0): the same job writes only a structure
manifest of `Textgrids.zip` (file count, first names, tier names, interval and label counts,
number of distinct labels; no sequences), so that a vireo loader can be registered later.

## Predictions (priors, graded with the Brier score)

| id | prediction | prior |
|---|---|---|
| B1 | T4a: the composite verdict fires on the real pooled curve | 0.80 |
| B2 | the chosen k is at least 3 for at least 3 of the 4 birds | 0.70 |
| B3 | the self-check calibrates T4c | 0.65 |
| B4 | T4b: at least 50% of bout-order permutations still fire | 0.60 |
| B5 | final grade FINITE_STATE_SUFFICES | 0.40 |
| B6 | S4 power (T4c EXCEEDS rate) at least 0.5 | 0.50 |
| B7 | S3 T4c EXCEEDS rate at least 0.5 | 0.75 |

## Code

`bf_stage4.py` (loader, k-gram null, tests, self-check, grade), `test_bf_stage4.py`,
`gate_s4.py` (refuses to run until this file is public), `get_core.py` (stage-1 core pinned by
git blob). Job: `gate_s4.py`, `get_core.py`, unit tests, `selfcheck`, `stage4`, `grade`.
Outputs: selfcheck4.json, selfcheck4_worlds.json, load_report4.json, stage4_results.json,
vireo_manifest.json, grade4.json.

## Known limits

Member-name order is assumed to follow recording time within a day. A k-gram with k up to 8 is one
finite-state class; HMM-type nulls (stage 3) are not repeated here. Independent bouts ignore
finite-state structure across bouts (T4b and S3 show how much that matters). This tests one
species of the four in the 2019 paper.

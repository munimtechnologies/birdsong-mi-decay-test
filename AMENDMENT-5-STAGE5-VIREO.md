# AMENDMENT 5: stage 5, Cassin's vireo song against a fitted finite-memory null

Pre-registered 2026-11-24 by MV2 of Munim, Inc. (mv2@munimtech.com), made with AI agents working
in his name; no human expert has reviewed it. This amendment was registered BEFORE any Cassin's vireo annotation was downloaded
or opened (no file of figshare 3081814 has been read; only its public file list and sizes), and
before any result of stages 1 to 4 came back (all four jobs were still queued when it was
written). Code Apache-2.0; text CC BY 4.0.

## Why a stage 5

Sainburg, Theilman, Thielk and Gentner (2019, Nat Commun 10:3636) read the exponential-plus-power-law
("composite") decay of mutual information (MI) between song elements as evidence of hierarchical,
non-Markovian organisation in four songbirds, Cassin's vireo among them. Stage 4 tests their
Bengalese finch data against per-bird fitted finite-memory surrogates. Cassin's vireo is the
sharpest second case, because its syntax has been measured directly: Hedley (2016, PLoS ONE
11:e0150822) fitted zero-, first- and second-order Markov models to the song of 14 wild males and
found it "intermediate in complexity between a first- and second-order model", with some
transitions depending on up to three earlier phrases. If the composite verdict still fires on vireo
song, and per-bird k-gram models (memory up to 8 phrases) given the paper's own design reproduce
it, then the verdict cannot separate hierarchy from the short memory this species is known to have.

Sainburg et al.'s public code (github.com/timsainb/ParallelsBirdsongLanguagePaper,
`parallelspaper/birdsong_datasets.py`, `prep_CAVI_CATH`) took the vireo TextGrids from the Bird-DB
transcripts; Hedley's figshare item 3081814 (CC BY 4.0; "Textgrid files ... containing annotations
identifying phrase-types") is the public release of the same population's annotations. If the two
differ, this stage tests the public release, and says so.

Prior-work search 2026-11-24 (web search on Cassin's vireo MI decay and hierarchical vs Markov
models; composite MI decay in birdsong with finite-state surrogates 2025-2026; re-analyses of
Sainburg 2019 with Markov nulls; Europe PMC full text of Hedley 2016): no published test of the
composite verdict on Cassin's vireo song against per-bird fitted finite-state surrogates. Closest:
Hedley 2016 (Markov order, not MI decay); Youngblood 2024 (Proc R Soc B, house finch; composite fit
without fitted finite-state surrogates; our stage 2); Nakaishi et al. (arXiv 2505.04984) and arXiv
2610.24334 (power laws without the hierarchy reading, language and formal languages, not birdsong).

## Data and loader (binding)

- `Textgrids.zip` of figshare 3081814 version 1. Its id, download URL and md5 are read from
  figshare's API (`/v2/articles/3081814`) at run time and the zip's md5 is checked against
  figshare's computed_md5. The 696-byte `Textgrids ReadMe.txt` is copied to the outputs unread by
  any rule. The audio (.rar, 12 GB) is never downloaded.
- Every `*.TextGrid` in the zip (and in zips inside it, one level) is read; macOS `._` and
  `__MACOSX` entries are skipped. Text TextGrids in the long or short Praat format, UTF-8, UTF-16
  or Latin-1, are parsed by our own tokenizer; anything else counts as unparsed.
- **Sainburg et al.'s rules:** tier 0 must be an interval tier with at least 3 intervals (else the
  file is unusable); its first and last intervals are dropped; a blank interval longer than **60 s**
  ends a bout; a bout is the list of non-blank labels (whitespace stripped) in time order. A
  recording whose bird id is `?` is dropped.
- **Bird id:** the deepest folder in the file's path that is not `TextGrids`, a number or a date;
  for a file at the top level, the leading letters and digits of its name.
- **Day:** the first `YYYY-MM-DD` / `YYYYMMDD` / `YYYY_MM_DD` date in the file name, else in its
  folders. **Day sequence** = all bouts of one bird and day, joined in path order (time order for
  date-time file names), as in the paper. **Fallback (registered):** if fewer than 90% of usable
  recordings carry a date, each recording is its own group (Hedley's unit of analysis); the report
  says which grouping ran.
- **Symbols** are the labels themselves, shared across birds, because vireo phrase types are
  population-wide two-letter codes (Hedley 2016: 126 types in the population) and the paper used
  them that way.
- **Birds kept** for analysis: at least 5 bouts and 300 phrases.
- **Loader stop** (writes `load_report5.json` with counts only, no analysis, grade LOADER_STOP) if:
  md5 mismatch; fewer than 150 TextGrids; fewer than 90% of TextGrids with a usable tier 0; kept
  birds not between 10 and 20; or fewer than 30,000 phrases in kept birds. A loader stop is followed
  by a new amendment that fixes the loader from the counts, never from label sequences.

## Tests (binding)

Identical to stage 4 (AMENDMENT-4-STAGE4-BENGALESE.md) and run by the registered stage-4 code,
`bf_stage4.py` (git blob 0a58a89e4f7b7c4ceb327d12b71ac0dd65f8ae4e), which imports the registered
stage-1 core `mi_decay.py` (git blob 83d578e3d03d130ac31f5cb4da5b3eb9bb077659). MI at distances 1 to
100 minus a within-sequence shuffle baseline; statistic = exponential-minus-composite AICc gap.
Output JSON keeps the stage-4 keys: T4a = T5a, T4b = T5b, T4c = T5c.

- **T5a replication:** the composite verdict (lowest AICc and relative probability above 0.999) on
  the real curve, all kept day sequences pooled.
- **T5b bout order:** the same after permuting bouts within each day sequence, 100 times; `p_order`
  with +1 correction.
- **T5c finite-memory null:** per bird, a k-th order Markov model of bouts (START padding, END
  outcome, Witten-Bell interpolation down to an add-one unigram over the bird's own types), k from 1
  to 8 by 5-fold held-out log-likelihood (ties to the smaller k); every bout drawn independently,
  real number of bouts per day; 100 surrogate datasets. EXCEEDS_FINITE_STATE if the real gap is
  above the surrogates' 95th percentile; FINITE_STATE_SUFFICES if the surrogates fire in at least
  50% and the real gap is below it; else UNRESOLVED (also with fewer than 20 finite gaps).

**Vireo-shaped self-check of T5c (same job; seed 20261124; 12 worlds per kind; 14 birds x 4 days x 4
bouts; shared symbols from 126 types; 40 surrogates and 20 bout-order permutations per world):**
- S0 in-class: per bird, a first-order chain over 50 types (0.7/0.2/0.1 on three next types) with a
  second-order override on 20% of (previous, current) pairs; bout ends with probability 0.005
  after each phrase.
- S1 finite-state outside the k-gram class: a 10-state hidden Markov model with sparse
  transitions, each state emitting one of its own 5 of the bird's 50 types.
- S3 cross-bout persistence: 3 bout types with their own chains over 17 types; the type persists
  from bout to bout with probability 0.8.
- S4 within-bout recursive hierarchy (positive control): Lin-Tegmark sequences (5 types, 2
  children, depth 7 = 128 phrases per bout).
- **T5c is calibrated** if it grades EXCEEDS in at most 12.5% of S0 worlds and of S1 worlds. S3 and
  S4 rates are reported as scope and power.

**Final grade** (as stage 4): UNRESOLVED_UNCALIBRATED if not calibrated; FINITE_STATE_SUFFICES;
CROSS_BOUT_ORDER (T5c EXCEEDS and p_order <= 0.05); WITHIN_BOUT_EXCESS (T5c EXCEEDS and p_order >
0.05); else UNRESOLVED.

## Predictions (priors, graded with the Brier score)

| id | prediction | prior |
|---|---|---|
| V1 | T5a: the composite verdict fires on the real pooled curve | 0.75 |
| V2 | the chosen k is at most 2 for at least 75% of kept birds | 0.70 |
| V3 | the self-check calibrates T5c | 0.60 |
| V4 | T5b: at least 50% of bout-order permutations still fire | 0.65 |
| V5 | final grade FINITE_STATE_SUFFICES | 0.50 |
| V6 | S4 power (T5c EXCEEDS rate) at least 0.5 | 0.50 |
| V7 | the loader passes on the first run | 0.55 |

## Code and job

`vireo_stage5.py` (loader, vireo-shaped worlds, grading), `test_vireo_stage5.py`, `gate_s5.py`
(refuses to run until this file is public), `get_deps.py` (fetches `mi_decay.py` and `bf_stage4.py`
by pinned blob). Job order: gate, get_deps, unit tests, `stage5` (loader, then T5a-T5c), `selfcheck`
(skipped after a loader stop), `grade`. Outputs: load_report5.json, vireo_readme.txt,
stage5_results.json, selfcheck5.json, selfcheck5_worlds.json, grade5.json.

## Known limits

Path order is assumed to be time order within a day. The figshare annotations may differ from
the Bird-DB copy the paper used. The k-gram class is one finite-state family; Hedley found mild
syntax shifts within and across seasons, which a per-bird model pooled over days does not
reproduce (a real EXCEEDS could reflect such drift and would not by itself show hierarchy). This
is the second of the paper's four species.

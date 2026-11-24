# AMENDMENT-1: house-finch loader and real-data job for stage 2

birdsong-mi-decay-test. MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in
MV2's name; no human expert has checked it yet. Text CC BY 4.0, code Apache-2.0.

**Registered 2026-11-24, before anyone on MV2's side opened any house-finch data file, before
any stage-1 or stage-2 self-check result came back, and before the stage-1 structure manifest
existed.**

## Why now, and the one deviation

PLAN.md said the stage-2 loader would be written "after the manifest" that the stage-1 job
(birdsong-mi-cal-v1) writes. That job is still waiting for compute. Instead of guessing, this
loader is pinned by the authors' own public analysis code (docs/index.Rmd of
github.com/masonyoungblood/linguistic_efficiency at tag v1.0.1-zenodo; code read, no data
opened), and it **proves itself on the data before any test runs** (check C0 below). If the
data are not what the code says, the loader stops and nothing is graded. This is the only
change to the registered design: the loader comes before the manifest, with a hard self-check
in place of the manifest's eyes.

## What the authors' code does (read 2026-11-24)

- `load("data_models/processed_data.RData"); data <- processed_data$data`. The `preparation`
  chunk adds `cluster_0` .. `cluster_4` (`as.numeric(hybrid_cut[[k + 1]])`, deep split k)
  to `data` before `save(processed_data, ...)`, next to `individual` and `song`.
- MI chunk: `mi_data <- parallel::mclapply(1:3, ...)`, with `data$syls <- data$cluster_2`,
  `cluster_3`, `cluster_4` for i = 1, 2, 3. For each individual, `seq <-
  data$syls[which(data$individual == r)]`: the rows in file order, songs joined, no sorting,
  no row dropped. Pairs d apart are taken inside each individual with more than d syllables.
- Entropy `s_calc <- log(sum(vals)) - (1/sum(vals))*sum(vals*digamma(vals))` (natural log);
  MI = s_x + s_y - s_xy. Saved per level as `data.frame(dist, mi = actual - shuffled,
  mi_raw = actual, mi_base = shuffled)` in `data_models/mi_data.RData`.
- Fits on `mi_data[[g]][1:100, ]` (brms, WAIC). We use Sainburg et al.'s AICc throughout, as
  PLAN.md already states.

## Loader (export_finch.R, then finch_load.py)

1. `export_finch.R` (base R, R from Debian's r-base-core) loads the two R files and writes
   `individual, song, cluster_2, cluster_3, cluster_4` in row order, plus each `mi_data[[g]]`
   (dist, mi_raw, mi_base, 17 significant digits). Only column names and row counts go to the
   job's output.
2. `finch_load.py` builds, for deep split 2 (primary), 3 and 4: birds in order of first
   appearance; each bird's rows in file order; a **song is a maximal run of consecutive rows
   with the same `song` value**, so the songs joined in order are exactly the authors' sequence.
   Output: the `{"levels": {"2": [{"bird", "songs"}], ...}}` file that `mi_stage2.py`
   (AMENDMENT-0) reads.

**Check C0 (hard).** From its own sequences the loader recomputes the raw MI with the authors'
natural-log estimator at d = 1..100 and compares it with their saved `mi_raw` for items 1, 2, 3
(deep split 2, 3, 4). It passes only if max |ours - theirs| < 1e-6 for all three. This proves the
labels and order are the authors' own. (The registered core `mi_decay.py` keeps Sainburg's
log2(N) term; that shifts raw MI by log2(N) - ln(N) at each d and cancels in MI minus baseline,
so the stage-2 tests run on the core unchanged.)

**Stops** (exit 1, no stage-2 run, `load_report.json` with counts and check values only): the
export failed; any NA label; a `song` value that comes back in a second, non-adjacent run within
a bird (songs would be cut); birds or songs more than 5% from the paper's 331 and 2,724; C0
failed. A stop leads to AMENDMENT-1b (structure only) and a new job version.

## Job birdsong-mi-finch-v1

python:3.12 plus r-base-core; 2 CPU, 2 GB; data volume shared with the stage-1 job.
`gate_a1.py` (this file public and identical to the job's copy) -> `test_finch_load` ->
`get_files.py` (mi_decay.py, mi_stage2.py, fetch_data.py pinned by git blob SHA) ->
`fetch_data.py` (zip md5 e5770657a37ebe3d7d0a40461d40ce75) -> `export_finch.R` ->
`finch_load.py` -> `mi_stage2.py stage2 --perm 100 --surr 100 --seed 20261124`.

## Grading (unchanged rules, one clarification)

`mi_stage2.py` computes T2a, T2b, T2c and T2c-type at every level and writes
`grade_primary` for T2c. **The primary test is the one the self-check job
(birdsong-mi-s2check-v1) selects**, as AMENDMENT-0 says: T2c if calibrated, else T2c-type if
calibrated, else UNCALIBRATED and the stage-2 verdict is UNRESOLVED whatever the data. If the
self-check selects T2c-type, the grade is read from `levels["2"]["T2c_type"]["grade"]`. No grade
is reported before the self-check result exists. Deep splits 3 and 4 are secondary.

## New predictions (Brier-scored with Q8-Q10)

| id | prediction | prior |
|---|---|---|
| L1 | C0 passes (our sequences reproduce the authors' raw MI within 1e-6 at all three levels) | 0.75 |
| L2 | The loader counts 331 birds and 2,724 songs exactly | 0.60 |
| L3 | Mean exact song-repeat rate per bird (deep split 2) is above 0.3 | 0.50 |

## Prior work checked 2026-11-24

Searches (web, arXiv, Google Scholar-style queries) for a test of the house-finch power-law MI
result against finite-state or repetition surrogates found none. Closest: Nakaishi et al.,
"Rethinking the Relationship between the Power Law and Hierarchical Structures" (arXiv
2505.04984, TACL), which questions the power-law-means-hierarchy inference on English corpora and
cites Youngblood 2024 without re-testing it; Sainburg et al. 2019 (Nat Commun 10:3636), who
checked repeated syllables by collapsing them but not repeated songs; Lin and Tegmark 2017
(Entropy 19:299), on why regular grammars give exponential decay.

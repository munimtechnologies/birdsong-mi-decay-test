# AMENDMENT-6B: how much speech does the hierarchy verdict need? (registered 2026-11-28)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; not yet checked
by a human expert. Text CC BY 4.0, code Apache-2.0.

Written on 2026-11-28 (about 10:00 UTC), after stage 6 was graded
([READING-STAGE6.md](READING-STAGE6.md)) and **before any file of the LibriSpeech training
subsets was opened by any MV2 job or agent**. It adds stage 6B; it changes nothing in stage 6 or in
any other stage.

## Why

In stage 6 the composite (exponential plus power-law) MI-decay verdict did not fire on read English
at bird-data size (dev-clean 193,644 phones, test-clean 189,327; a plain exponential won all four
analyses). Sainburg et al. 2019 (Nature Communications 10:3636) found the composite in 4,379,552
phones of conversational speech. Two readings are open: (a) the verdict needs much more data than
the bird studies have before it can see the long-range structure of human speech, or (b) read
speech, phones from forced alignment, or our pipeline do not give the composite at any size. Stage
6B measures the verdict as a function of sample size on the same kind of data, up to about 60
times the stage-6 size.

## Data

The same Zenodo zip as stage 6 (LibriSpeech Alignments, Lugosch 2019, record 2619474, CC BY 4.0;
md5 read from Zenodo's API and checked). Subsets **train-clean-100 (primary)** and
**train-clean-360 (large, secondary)**. Loader rules exactly as AMENDMENT-6 (phone tier, stress
digits removed, silence and spoken-noise intervals dropped, speaker and chapter from the file name,
utterances in number order within each chapter). Phones are coded as integers in first-seen order
(the MI estimator does not depend on the codes).

Loader gate (else LOADER_STOP, nothing graded): zip md5 equals Zenodo's; train-clean-100 has at
least 200 speakers and 2,500,000 phones; at most 1% of its TextGrids lack a phone tier; 30-50
distinct phone labels.

## Tests (pinned code: mi_decay.py blob 83d578e3, bf_stage4.py blob 0a58a89e, speech_stage6.py blob ce357898)

The verdict is the registered one: `bf_stage4.curve_and_fit` on chapter sequences (each chapter's
utterances joined in order, `bf_stage4.day_sequences`), distances 1-100, fire = composite lowest
AICc with relative probability above 0.999 (`fire_strong`).

* **D1 (primary), size series.** From train-clean-100, whole chapters drawn in random order until
  the sample has at least N phones, for N = 200,000, 500,000, 1,000,000 and 2,000,000; 5 independent
  draws per size (seed 20261128, generator `[seed, 1, size index, draw]`). For each draw: fire,
  best model, exponential-minus-composite AICc gap, AICc weights.
* **D2, all of train-clean-100.** The verdict on the whole subset, and the stage-4 finite-memory
  test: per-speaker k-gram models (k 1-8 by 5-fold held-out likelihood, `bf_stage4.fit_models`),
  40 surrogate datasets (`bf_stage4.kgram_surrogate`), graded by `bf_stage4.grade_null`
  (EXCEEDS_FINITE_STATE / FINITE_STATE_SUFFICES / UNRESOLVED). No new self-check is run at this
  size; the stage-6 self-check (1 of 8) is the only calibration, which is a limit.
* **D3, all of train-clean-360.** The verdict once on the whole subset, run last. If it does not
  finish (memory or time), D3 is reported as not run and nothing else changes.

Runs: `python get_deps6b.py` (fetches and checks the pinned code, and checks that this amendment
and `stage6b.py` on GitHub equal the job's copies), `python -m unittest -v test_stage6b`,
`python stage6b.py run --data-dir /data --out-dir /out`, `python stage6b.py grade --out-dir /out`.

## Registered headline

Let F(N) be the number of the 5 draws at size N in which the verdict fires; a size "fires" if
F(N) >= 3. D2 and D3 fire if their single verdict fires.

| Condition | Headline |
|---|---|
| loader gate fails | LOADER_STOP |
| F(200,000) >= 3 | FIRES_AT_BIRD_SIZE |
| F(200,000) = 2 | MIXED |
| F(200,000) <= 1 and any of 500k, 1M, 2M, D2, D3 fires | FIRES_ABOVE_BIRD_SIZE (reported with the smallest size that fires) |
| none fires, D3 ran | NEVER_FIRES |
| none fires, D3 did not run | NEVER_FIRES_TO_TRAIN_CLEAN_100 |

Under FIRES_ABOVE_BIRD_SIZE the reading states the smallest firing size as the sample size the
verdict needs on read English, and compares it with the sizes of the bird data sets of stages 2-5
as their loaders report them (Bengalese finch, stage 4: 215,740 syllables). Under NEVER_FIRES the reading says the verdict did not see hierarchy in read
English at up to the size of train-clean-360, and that the 2019 speech result then rests on
conversational speech or on details of the original pipeline, which this stage cannot separate.
D2's T6c grade is secondary: it says whether, at the largest primary size, the real curve goes
beyond what each speaker's finite memory produces.

## Forecasts (probabilities, scored by Brier when graded)

| id | statement | p |
|---|---|---|
| Q1 | F(200,000) <= 1 | 0.85 |
| Q2 | F(1,000,000) >= 3 | 0.35 |
| Q3 | the verdict fires on all of train-clean-100 (D2) | 0.50 |
| Q4 | the verdict fires on all of train-clean-360 (D3; ungraded if D3 did not run) | 0.60 |
| Q5 | headline FIRES_ABOVE_BIRD_SIZE | 0.55 |
| Q6 | headline NEVER_FIRES or NEVER_FIRES_TO_TRAIN_CLEAN_100 | 0.30 |
| Q7 | D2 T6c grade EXCEEDS_FINITE_STATE | 0.30 |
| Q8 | mean gap at 2,000,000 phones is larger than mean gap at 200,000 | 0.80 |

## Limits known now

Read audiobook speech with dictionary pronunciations, not conversation. Draws are whole chapters, so
the larger samples hold more speakers as well as more phones. Five draws per size. D2's finite-memory
test has 40 surrogates and no self-check at its size. One registered verdict and one estimator (the
stage-1 core, Sainburg et al.'s entropy estimator, log2) are tested.

# AMENDMENT-6: stage 6, a human-speech control (registered 2026-11-24)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; not yet checked
by a human expert. Text CC BY 4.0, code Apache-2.0.

Written on 2026-11-24 (about 22:00 UTC) **before any speech alignment file was downloaded or
opened, and before any result of stages 1-5 existed** (all of their jobs are still queued). It adds
a stage; it changes nothing in stages 1-5.

## Why this stage

Stages 2-5 ask whether the composite (exponential + power-law) decay of mutual information (MI)
between song elements, read as evidence of hierarchy by Sainburg et al. 2019 (Nat Commun 10:3636)
and Youngblood 2024 (Proc R Soc B 291:20240250), is more than per-animal finite-memory models
produce. A verdict "finite state suffices" on a bird can mean two things: the song has no
structure beyond finite memory, **or** the diagnostic cannot see such structure at this sample
size. The two can only be told apart on a sequence that is known to be hierarchical. Human
language is. Sainburg et al. 2019 themselves found the composite decay in all four phone-level
speech corpora they analysed. This stage runs **exactly the registered stage-4 pipeline** on
read English speech:

* If per-speaker finite-memory surrogates do **not** reproduce the real speech curve
  (POSITIVE_CONTROL_PASSES), the bird verdicts of stages 2-5 can be read at face value.
* If they **do** (POSITIVE_CONTROL_FAILS), the diagnostic cannot separate human speech from
  finite-memory processes at this size, and any bird "finite state suffices" verdict will be
  reported as "not detectable", never as "absent".

Closest prior work (searched 2026-11-24): Nakaishi, Yoshida, Kajikawa, Hukushima and Oseki 2026
(TACL 14:1917-1935, arXiv:2505.04984) test the *assumptions* behind the power-law-hierarchy
argument on English and Japanese parse trees and find they fail; they do not fit finite-state
surrogates to speech. Takahashi and Tanaka-Ishii 2017 (arXiv:1707.04848) question pairwise MI as
a measure of long memory in text. Lin and Tegmark 2017 prove exponential MI decay for finite
Markov processes in the limit. Howard-Spink et al. 2024 (PeerJ 12:e18484) check power-law
detection on Markov chains with fixed parameters. We found no study that fits finite-memory models
to speech and asks whether they reproduce the composite verdict.

## Data

LibriSpeech Alignments, Lugosch 2019, Zenodo record 2619474 (CC BY 4.0): Montreal Forced Aligner
TextGrids for LibriSpeech (Panayotov et al. 2015, CC BY 4.0). The zip's md5 is read from Zenodo's
API at run time and checked. Subsets: **dev-clean (primary, 40 speakers)** and **test-clean
(replicate, 40 speakers)**. No training subset is used.

Loader rules (fixed now): the phone tier ("phones", or MFA's "<speaker> - phones"), intervals in
onset order; stress digits removed (AH0 -> AH); intervals labelled "", sil, sp, spn, <eps>, <unk>,
<sil>, sil0 or noise dropped. Speaker and chapter from the file name
(speaker-chapter-utterance.TextGrid), the subset from the folder name; utterances in number order
within each chapter. Phones share one code across speakers.

Loader gate (else LOADER_STOP, nothing graded, a dated amendment fixes the loader): zip md5 equals
Zenodo's; per subset at least 35 speakers, 2,000 utterances and 100,000 phones; at most 1% of
TextGrids without a phone tier; 30-50 distinct phone labels.

## Tests (the stage-4 code, `bf_stage4.py` and `mi_decay.py`, fetched by pinned git blob)

Mapping: speaker = bird, chapter = day, utterance = bout.

* **T6a** composite verdict (relative probability of the composite model > 0.999, the stage-1
  primary criterion) on the chapter sequences (each chapter's utterances concatenated in order).
* **T6b** the same after permuting utterance order within each chapter (100 permutations);
  upper p of the real exponential-minus-composite AICc gap.
* **T6c** per-speaker k-gram surrogates (k = 1..8 by 5-fold held-out likelihood, Witten-Bell,
  START/END; each utterance generated independently, chapters keep their number of utterances;
  100 surrogates), graded by `bf_stage4.grade_null`: EXCEEDS_FINITE_STATE if the real gap is
  above the surrogates' 95th percentile; FINITE_STATE_SUFFICES if the surrogates fire in at least
  half and the real gap is below it; else UNRESOLVED.
* **T6u** (secondary) T6a and T6c with single utterances as the sequences (Sainburg et al.'s speech
  unit), 100 surrogates, no permutation.
* **Self-check** (before any grade counts): 8 in-class worlds, each a k-gram surrogate of
  dev-clean (from the k-grams fitted to dev-clean) treated as data and put through T6c with 40
  surrogates. Calibrated if at most 1 of 8 (0.125, the stage-4 limit) is graded
  EXCEEDS_FINITE_STATE.

Seed 20261124. Runs: `python speech_stage6.py stage6 --data-dir /data --out-dir /out`, then
`python speech_stage6.py grade --out-dir /out` (writes grade6.json).

## Registered headline

From the chapter-level T6c grades of dev-clean and test-clean:

| Condition | Headline |
|---|---|
| self-check not calibrated | UNRESOLVED_UNCALIBRATED |
| either subset FINITE_STATE_SUFFICES | POSITIVE_CONTROL_FAILS |
| both subsets EXCEEDS_FINITE_STATE | POSITIVE_CONTROL_PASSES |
| anything else | SPLIT_OR_UNRESOLVED |

How it is used: the stage 2-5 readings will quote this headline next to every bird verdict. Under
POSITIVE_CONTROL_FAILS, a bird FINITE_STATE_SUFFICES is reported as "the diagnostic cannot detect
hierarchy here", and the arc's article says the diagnostic failed on human speech.

## Forecasts (probabilities, scored by Brier when graded)

| id | statement | p |
|---|---|---|
| P1 | T6a fires on dev-clean chapters | 0.80 |
| P2 | T6a fires on test-clean chapters | 0.80 |
| P3 | self-check calibrated | 0.80 |
| P4 | dev-clean chapter T6c = EXCEEDS_FINITE_STATE | 0.70 |
| P5 | headline POSITIVE_CONTROL_PASSES | 0.60 |
| P6 | headline POSITIVE_CONTROL_FAILS | 0.15 |
| P7 | dev-clean T6b upper p <= 0.05 (utterance order matters) | 0.55 |
| P8 | dev-clean utterance-level T6c = EXCEEDS_FINITE_STATE | 0.45 |
| P9 | median chosen k across the 80 speakers >= 3 | 0.70 |

## Limits known now

Read audiobook speech, phones from forced alignment (pronunciations come from a dictionary, so the
phone string follows the transcript); about 40 speakers and roughly 200,000 phones per subset,
close to the size of the bird data sets, far smaller than the speech corpora of Sainburg et al.
A per-speaker k-gram of at most 8 phones is one finite-state null, not all of them.

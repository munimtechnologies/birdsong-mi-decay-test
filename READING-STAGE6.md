# READING-STAGE6: the human-speech control (graded 2026-11-28)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; not yet checked
by a human expert. Text CC BY 4.0, code Apache-2.0.

Registration: [AMENDMENT-6-STAGE6-SPEECH.md](AMENDMENT-6-STAGE6-SPEECH.md), public on 2026-11-24
before any speech alignment file was downloaded. Job `speech-mi6-v1` (MV2-Compete, the Blade):
started 2026-11-28 05:28:17Z, finished 06:45:56Z, every step exit 0, peak memory 0.2 GB. Unit tests
passed in the job before the analysis ran. Files: [results/stage6/](results/stage6/)
(`grade6.json`, `stage6_summary.json`, `selfcheck6.json`, `load_report6.json`). Nothing in the
registration or code was changed after the data were seen.

## Headline: SPLIT_OR_UNRESOLVED

**The registered hierarchy verdict did not fire on human speech.** On read English (LibriSpeech
dev-clean: 40 speakers, 2,703 utterances, 193,644 phones; test-clean: 40 speakers, 2,620 utterances,
189,327 phones), the composite exponential-plus-power-law model never won. A plain exponential had
the lowest AICc in all four analyses (chapters and single utterances, both subsets). The composite
got at most 20.3% of the AICc weight, against the 99.9% the verdict requires. With the same code,
real Bengalese finch song (215,740 syllables, stage 4) gave the composite a margin of 138.84 AICc
units.

The registered headline is SPLIT_OR_UNRESOLVED, not POSITIVE_CONTROL_FAILS. POSITIVE_CONTROL_FAILS
needs the finite-memory surrogates to fire in at least half their runs, and here neither the
speech nor its surrogates fired (0 of 100 in every unit). The chapter-level T6c grades are
UNRESOLVED in both subsets. In plain words: at bird-data size, this diagnostic would have said
"no hierarchy shown" about human language.

## Loader gate and self-check

- Loader: Zenodo md5 2bab567d0ace651a4ba254e813629f46 matched; 0 bad TextGrids in either subset;
  39 phone labels; no gate failures (`load_report6.json`).
- Self-check (registered limit 1 of 8 in-class worlds graded EXCEEDS_FINITE_STATE): **1 of 8**
  (world 5, p 0.0488), so the test is calibrated. No self-check world fired the composite verdict.

## Results by unit

gap = AICc(exponential) - AICc(composite); the composite verdict needs a positive gap and composite
weight above 99.9%. "Surrogates firing" is the share of the 100 per-speaker k-gram surrogate datasets
in which the verdict fired; p_upper is the share of surrogates with a gap at or above the real one.

| subset | unit | fit points | best model | gap | composite weight % | surrogates firing | surrogate gap p95 | p_upper | T6c grade |
|---|---|---|---|---|---|---|---|---|---|
| dev-clean | chapter | 71 | exponential | -2.73 | 20.3 | 0/100 | -2.32 | 0.0792 | UNRESOLVED |
| test-clean | chapter | 72 | exponential | -3.21 | 16.7 | 0/100 | -0.39 | 0.2871 | UNRESOLVED |
| dev-clean | utterance | 53 | exponential | -4.24 | 10.7 | 0/100 | -4.77 | 0.0099 | EXCEEDS_FINITE_STATE |
| test-clean | utterance | 44 | exponential | -4.77 | 8.4 | 0/100 | -4.75 | 0.0792 | UNRESOLVED |

- **T6b** (utterance order permuted within chapters, 100 permutations): the verdict fired in 0 of
  100 in both subsets; p_upper 0.4455 (dev-clean) and 0.9010 (test-clean). Utterance order adds
  nothing this statistic can see.
- **T6u** (single utterances, secondary): in dev-clean the real curve is a little less exponential
  than the surrogates' (p_upper 0.0099), graded EXCEEDS_FINITE_STATE, but the composite still
  loses (gap -4.24) and test-clean does not replicate it (p_upper 0.0792). We do not read it as a
  detection.
- **Chosen memory:** held-out likelihood picked k = 2 for all 40 dev-clean speakers; in test-clean
  36 speakers k = 2, 2 speakers k = 1, 2 speakers k = 3. Median k over the 80 speakers is **2**.
  At about 4,800 phones per speaker, a phone bigram predicts held-out speech best.

## Why: the speech curve is gone after about ten phones

Mutual information minus the shuffled baseline, dev-clean chapters: 0.5535 at distance 1, 0.0539
at 3, 0.0074 at 5, 0.0011 at 8 and 0.00009 at 10. After that the values scatter around zero:
every value from distance 11 to 100 lies between -0.00044 and 0.00076. It falls by about a factor
of three per phone, which is what an exponential is. The finch curve from stage 4 is still 0.5719
at distance 10 and 0.0124 at 100. Whatever long-range information read English carries between
phones is below this sample's noise floor, so no curve-shape test on data this size can see it.

Sainburg et al. 2019 (Nature Communications 10:3636, PMC6690877) found the composite in speech
with 4,379,552 phones from 394 speakers in four conversational corpora, about 23 times the phones
of one subset here. The bird data sets the verdict is applied to are near our size. This stage
does not contradict their speech result. It shows that the verdict needs far more data than the
bird studies have before it can see hierarchy in a sequence known to have it.

## Forecasts (registered 2026-11-24)

| id | statement | p | outcome |
|---|---|---|---|
| P1 | T6a fires on dev-clean chapters | 0.80 | false |
| P2 | T6a fires on test-clean chapters | 0.80 | false |
| P3 | self-check calibrated | 0.80 | true |
| P4 | dev-clean chapter T6c = EXCEEDS_FINITE_STATE | 0.70 | false |
| P5 | headline POSITIVE_CONTROL_PASSES | 0.60 | false |
| P6 | headline POSITIVE_CONTROL_FAILS | 0.15 | false |
| P7 | dev-clean T6b upper p <= 0.05 | 0.55 | false |
| P8 | dev-clean utterance-level T6c = EXCEEDS_FINITE_STATE | 0.45 | true |
| P9 | median chosen k across the 80 speakers >= 3 | 0.70 | false |

Brier score **0.3653** over 9 forecasts. This is our worst forecast in the project: we expected
the verdict to fire on speech (0.80) and it did not.

## What this changes for the bird stages

AMENDMENT-6 says every bird verdict is quoted next to this headline. The headline is
SPLIT_OR_UNRESOLVED, and the plain fact behind it is that the composite verdict missed a
hierarchical sequence (human speech) at bird-data size, just as it missed the Lin-Tegmark
recursive worlds in stage 1 (2 of 50). So:

- A bird FINITE_STATE_SUFFICES verdict (Bengalese finch, stage 4) means this statistic gives no
  evidence of hierarchy there. It cannot mean hierarchy is absent.
- Where the composite verdict does fire on birds (Bengalese finch: margin 138.84), its source is
  something finite memory already makes: each bird's own k-gram syntax with bouts reproduces it
  (100 of 100 surrogates). Human speech, which is hierarchical, does not fire at all. At equal
  sample size, the curve that "parallels" birdsong and speech is present in the finch and absent
  in the speech.

## Limits

Read audiobook speech, not conversation; phones come from forced alignment with a pronouncing
dictionary, so phone strings follow the transcript. Two subsets of about 190,000 phones each.
Our pipeline is a scipy re-implementation (the authors used lmfit), with the stage-4 MI estimator
and baseline. A per-speaker k-gram is one finite-state null. The statement "the verdict needs more
data" is an inference from the noise floor; we did not run a larger LibriSpeech subset, which
would be the direct test (train-clean-100 has 28,538 utterances).

## Prior work (searched 2026-11-24 before registration and again 2026-11-28)

Closest: Nakaishi et al. 2026 (TACL, arXiv 2505.04984) test the assumptions behind the
power-law-to-hierarchy argument on parse trees; Howard-Spink et al. 2024 (PeerJ 12:e18484) measure
false alarms from one Markov chain on chimpanzee actions; Sainburg et al. 2019 and Sainburg, Mai and
Gentner 2022 (Proc R Soc B 289:20212657) report composite decay in large speech corpora;
Mikhaylovskiy 2026 (arXiv 2610.05466) studies power-law autocorrelation in written text. None of
them runs the bird-study pipeline on speech at bird-data size or fits per-speaker finite-memory
surrogates to speech.

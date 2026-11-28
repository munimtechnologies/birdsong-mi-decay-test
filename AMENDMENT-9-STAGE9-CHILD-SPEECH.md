# AMENDMENT-9: stage 9, children's speech before syntax (registered 2026-11-28)

MV2, Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; not yet checked
by a human expert. Text CC BY 4.0, code Apache-2.0.

Written on 2026-11-28 (about 07:30 UTC) **before any child-speech transcript was downloaded or
opened**. MV2 has no TalkBank account today, so no PhonBank file can have been seen. The
stage-6 human-speech control (AMENDMENT-6) is running but has not returned. This amendment adds a
stage; it changes nothing in stages 1-8B.

## The claim

Sainburg, Mai and Gentner 2022, "Long-range sequential dependencies precede complex syntactic
production in language acquisition", Proc R Soc B 289:20212657
(https://doi.org/10.1098/rspb.2021.2657, CC BY 4.0; code github.com/timsainb/LongRangeSequentialOrgPaper,
BSD-3). They fit exponential, power-law and composite (exponential + power-law) models to the
mutual information (MI) between phones as a function of distance in PhonBank transcripts of
children aged 6 months to 4 years, pooled by age bin. The composite model won in all 6 phone age
bins (relative probability 0.897 to >0.999). They conclude that "adult-like power-law statistical
dependencies are present in human vocalizations at the earliest detectable ages", so that
linguistic structure cannot be the only source of long-range dependency in language. Their
controls were shuffles, a first-order Markov transition-entropy check and length-matched
first-order Markov sequences for compressibility. **No higher-order or per-child finite-memory
model was fitted and put through the same MI-decay verdict.**

Stages 1, 4 and 8 of this study showed that the composite verdict can be produced by finite-memory
models alone (stage 1 UNCALIBRATED_MULTI_TIMESCALE; stage 4 Bengalese finch FINITE_STATE_SUFFICES,
p 0.4752; stage 8 MIXED, the published composite reading firing in 196 of 400 worlds without
hierarchy). Stage 9 asks the same question of the child data.

Prior work searched 2026-11-28 (web: the paper's title with "reanalysis", "critique",
"replication", "Markov null"; "mutual information decay child speech Markov"; Europe PMC citing
works): no reanalysis or critique of the 2022 paper was found. It is cited in support by
Howard-Spink et al. 2024 (PeerJ 12:e18484, the "statistical scaffolding hypothesis"). The general
critiques (Nakaishi et al. TACL 2026, arXiv 2505.04984; Takahashi and Tanaka-Ishii 2017,
arXiv 1707.04848; Lin and Tegmark 2017) do not fit finite-state models to child speech.

## Data (fixed now)

PhonBank (TalkBank), **English corpora of typically developing children whose CHAT files have a
%pho (actual production) tier**, downloaded as the corpus zip files under PhonBank's
"Eng-NA" and "Eng-UK" folders. Before any %pho line is analysed, `manifest9.py` lists every
corpus, child, session file name, the age in the @ID header and whether a %pho tier exists, and
writes manifest9.json. That list, not a choice made after seeing results, decides what is used.
Corpora flagged in their PhonBank page as clinical (phonological disorder, hearing loss, late
talkers) are excluded by name in the manifest step. TalkBank's Ground Rules apply; transcripts
are never committed or redistributed, and only counts and MI curves are published.

The three English corpora the 2022 paper used are the **primary replication set** if they can be
identified from its references 78-80 (Davis and MacNeilage 1995; Parsons 2006; Song, Demuth,
Evans and Shattuck-Hufnagel 2013). The full eligible English set is the **secondary** set.

Loader rules: the child's own utterances only (speaker code CHI); the %pho tier of each; utterance
order as in the file; sessions ordered by file name within each child. IPA is cut into segments:
one base letter plus its combining diacritics and tie-bars; then all combining diacritics,
stress marks, syllable dots, length marks and tone letters are removed, so each segment becomes
its base IPA letter (affricates written with a tie-bar stay one segment). Word spaces, pauses,
"xxx", "yyy", "www", "*" and bracketed codes are dropped. Labels share one code across children.

Age bins (months, from @ID; as in the paper): 6-12, 12-18, 18-24, 24-30, 30-36, 36-48.

Loader gate (else LOADER_STOP, nothing graded, a dated amendment fixes the loader): at least
3 eligible corpora; at most 2% of the child's utterances with a %pho tier that cannot be cut into
segments; 20-150 distinct segment labels overall. A bin is INSUFFICIENT (graded neither way) if it
has fewer than 3 children, 20 sessions or 5,000 segments.

## Tests (the stage-4 code, `bf_stage4.py` and `mi_decay.py`, by pinned git blob)

Mapping as in stage 6: child-within-bin = bird, session = day, utterance = bout.

* **T9a** composite verdict (relative probability of composite > 0.999) on session sequences
  (each session's utterances concatenated in order), per age bin.
* **T9b** the same after permuting utterance order within each session (100 permutations);
  upper p of the real exponential-minus-composite AICc gap.
* **T9c** per-child (within bin) k-gram surrogates, k = 1..8 by 5-fold held-out likelihood,
  Witten-Bell, START/END; each utterance generated independently, sessions keep their number of
  utterances; 100 surrogates; graded by `bf_stage4.grade_null` (EXCEEDS_FINITE_STATE /
  FINITE_STATE_SUFFICES / UNRESOLVED), per bin.
* **T9p** (secondary) T9a with the paper's own unit, every session of a bin pooled, to check our
  loader reproduces the published composite verdict.
* **Self-check** (before any grade counts): 8 in-class worlds, k-gram surrogates of the 18-24
  bin, put through T9c with 40 surrogates; calibrated if at most 1 of 8 is EXCEEDS_FINITE_STATE.

Seed 20261128.

## Registered headline

Early = bins 6-12 and 12-18; late = bins 30-36 and 36-48. Conditions are read in this order:

| Condition | Headline |
|---|---|
| self-check not calibrated | UNRESOLVED_UNCALIBRATED |
| both early bins EXCEEDS_FINITE_STATE | EARLY_LONG_RANGE_SURVIVES |
| both early FINITE_STATE_SUFFICES and both late EXCEEDS_FINITE_STATE | ONSET_WITH_SYNTAX |
| both early FINITE_STATE_SUFFICES | EARLY_FINITE_STATE_SUFFICES |
| anything else (including INSUFFICIENT early bins) | SPLIT_OR_UNRESOLVED |

How it is read: EARLY_LONG_RANGE_SURVIVES supports the 2022 conclusion with a stronger null.
EARLY_FINITE_STATE_SUFFICES means the early power-law signal is what each child's own
short-memory phonotactics already produce. ONSET_WITH_SYNTAX would reverse the paper's conclusion:
dependency beyond finite memory would appear only once children combine words. If stage 6 ends
POSITIVE_CONTROL_FAILS (the diagnostic cannot separate adult read speech from finite memory),
every FINITE_STATE_SUFFICES here is reported as "not detectable", never "absent".

## Forecasts (Brier-scored when graded)

| id | statement | p |
|---|---|---|
| Q1 | T9a fires in at least 5 of the sufficient bins' 6 | 0.70 |
| Q2 | T9p reproduces the composite verdict in every sufficient bin | 0.75 |
| Q3 | self-check calibrated | 0.80 |
| Q4 | the 6-12 bin is sufficient | 0.55 |
| Q5 | headline EARLY_LONG_RANGE_SURVIVES | 0.25 |
| Q6 | headline EARLY_FINITE_STATE_SUFFICES | 0.30 |
| Q7 | headline ONSET_WITH_SYNTAX | 0.10 |
| Q8 | median chosen k across children >= 3 | 0.55 |

## Blocked on

A free TalkBank account (registration needs an email and password, which MV2's agents may not
create or hold), asked of Sheehan on 2026-11-28. The loader, manifest step and job will be written
and committed before any file is opened, and this amendment will not be edited; any change is a
new dated amendment.

## Limits known now

Transcribed IPA, not acoustic units; transcription conventions differ across corpora; few
children per bin at the youngest ages; babble at 6-12 months may have very few distinct segments.
A per-child k-gram of at most 8 segments is one finite-state null, not all of them.

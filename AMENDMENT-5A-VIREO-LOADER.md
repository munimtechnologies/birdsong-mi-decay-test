# AMENDMENT 5A: stage 5 loader fix (bird and day of each Cassin's vireo recording from S1 Table)

MV2, Munim, Inc. (mv2@munimtech.com). Registered 2026-11-27 by AI agents working in MV2's name,
BEFORE any cell of S1 Table of Hedley (2016) was read by us and before any vireo phrase label or
label sequence was seen. Code Apache-2.0; text CC BY 4.0. It changes only the loader of
[AMENDMENT-5-STAGE5-VIREO.md](AMENDMENT-5-STAGE5-VIREO.md); tests T5a-T5c, the self-check, the
grade and the predictions V1-V6 are unchanged.

## What happened

Job `birdsong-mi-vireo5-v1` (2026-11-27, 18:38-18:56Z) graded **LOADER_STOP**, as Amendment 5
required when the loader fails. From its counts-only report (`load_report5.json`): figshare 3081814
v1 downloaded with a matching md5 (443655cbd17ee4134cd63c4d427a91f4); 221 TextGrids, all UTF-8,
all parsed, all with a usable tier 0; but **0 of 221 had a bird id** under the registered rule
(deepest folder, else the leading letters-and-digits of the file name), and **0 of 221 carried a
date**. Each file's tier 0 is named after its recording (`Cavi1113` ... `Cavi1841`, 221 distinct
names). The data set's ReadMe (copied unread by any rule) says: "Metadata for all wav files are
listed in S1 Table, which contains information about the individual in the recording, the number of
phrases in the recording, recording length, recording date and recording time." Prediction V7 (the
loader passes on the first run) is therefore false.

## The fix (binding)

- **S1 Table** of Hedley 2016 (PLoS ONE 11:e0150822, file `pone.0150822.s002.xlsx`, "Metadata for
  sound recordings") is downloaded at run time from
  `https://journals.plos.org/plosone/article/file?type=supplementary&id=10.1371/journal.pone.0150822.s002`;
  its sha256 and size are logged. It is read with the Python standard library (zip + XML): the
  worksheet with the most non-empty cells, shared and inline strings, numbers as written.
- **Recording key.** For a TextGrid: the last run of digits in its tier-0 name, else in its file
  name. For a table cell: the integer itself if the cell is a whole number, else the last run of
  digits after removing a `.wav`/`.textgrid`/`.txt` ending.
- **Recording column:** the column whose cells match the most TextGrid keys; it must match at least
  90% of the usable TextGrids (else loader stop). **Data rows** are the rows whose key matches; if a
  key appears twice, the first row counts and the duplicate is reported. **Header row:** the
  nearest non-empty row above the first data row.
- **Bird column:** among the other columns, those non-empty in at least 90% of data rows with 5 to
  40 distinct values. The leftmost whose header matches `individual|bird|subject|identity|male|band|
  \bid\b|name` (case-insensitive) is chosen; if none matches, the leftmost that is not entirely
  numeric; if there is none, loader stop. Values are stripped; `?` stays "unknown bird" and is
  dropped, as before.
- **Day:** the leftmost column whose header contains `date`. Whole numbers 20,000-80,000 are Excel
  serial dates (day 0 = 1899-12-30); text is read as `YYYY-MM-DD` (and the registered variants) or
  as month/day/year (day/month/year if the first number exceeds 12; two-digit years are 20xx). The
  registered fallback is unchanged: if fewer than 90% of usable recordings get a day, each recording
  is its own group.
- Order within a bird-day stays path order (as registered); the recording numbers are assumed to
  run in recording order. Every other loader rule, gate and threshold of Amendment 5 is unchanged
  (10-20 birds kept, at least 30,000 phrases, at least 5 bouts and 300 phrases per bird).
- `load_report5.json` gains an `s1` section with counts only: sheet size, chosen columns and
  headers, matches, duplicates, distinct birds and the share of recordings dated. If this loader
  stops too, the next amendment again fixes it from counts, never from label sequences.

## Code and job

`vireo_s5a.py` imports the registered `vireo_stage5.py` unchanged and replaces only the assignment
of bird and day (`build5a`); `stage5` runs T5a-T5c through the registered code, `selfcheck` and
`grade` are passed to the registered `vireo_stage5.main`. `gate_s5a.py` refuses to run until this
file and `vireo_s5a.py` are public with the same content, then fetches the registered
`vireo_stage5.py`, `test_vireo_stage5.py` and `get_deps.py` from this repository (sha256 logged) and
runs `get_deps` (pinned blobs of `mi_decay.py` and `bf_stage4.py`). `test_vireo_s5a.py` checks the
reader on a small synthetic workbook and TextGrids. Job `birdsong-mi-vireo5-v2`: gate, unit tests,
`stage5`, `selfcheck`, `grade`, with the registered seeds and counts (100 permutations, 100
surrogates; self-check 12 worlds, 20 permutations, 40 surrogates; seed 20261124).

## Known limits added

Bird and day now come from the authors' table, not from the annotation files, so an error in the
table would carry over. The table may list recordings that have no TextGrid; those rows are ignored.

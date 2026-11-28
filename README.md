# birdsong-mi-decay-test

A pre-registered, calibrated test of a widely used argument about animal sequences: that the
mutual information (MI) between elements d places apart falls off as an **exponential plus a
power law**, and that the power-law part is evidence of hierarchy beyond any Markov (finite-state)
process. The argument comes from Sainburg, Theilman, Thielk and Gentner 2019 (Nature
Communications 10:3636) and is used by Youngblood 2024 (Proc. R. Soc. B 291:20240250),
Howard-Spink et al. 2024 (PeerJ 12:e18484, chimpanzee actions) and SymSeqBench (arXiv 2512.24977).

By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no human
expert has checked it yet. Code Apache-2.0, text CC BY 4.0. Data stay with their authors.

## Results so far

| stage | question | registered grade | reading |
|---|---|---|---|
| 1 | How often does the composite verdict fire in simulated worlds without hierarchy, and does it catch a recursive model? | UNCALIBRATED_MULTI_TIMESCALE: fires in 46 of 50 pooled-bird worlds and 50 of 50 song-type-bout worlds, but only 2 of 50 Lin-Tegmark recursive worlds | [READING-STAGE1.md](READING-STAGE1.md) |
| 4 | Does real Bengalese finch song beat surrogates from each bird's own fitted finite-memory syntax? | FINITE_STATE_SUFFICES: all 100 surrogates fire; real margin 138.84 AICc, 47 surrogates at or above it (p 0.4752) | [READING-BF4.md](READING-BF4.md) |
| 8 | Is "pure power law wins" a calibrated signature of recursion (650 fresh worlds)? | MIXED: recursive 133 of 250, heavy-tailed bouts 0 of 50, but pooled birds 3 of 50, past the 5% false-alarm limit | [READING-STAGE8.md](READING-STAGE8.md) |

Article: [Finch song's power-law signal is reproduced by finite memory alone](https://www.munimtech.com/research/bengalese-finch-power-law-finite-memory-test)
(goes live when the site's daily article limit allows). The claims are rows in MV2's
[ledger of calibrated re-tests](https://github.com/munimtechnologies/calibrated-animal-claims).

## Registered and waiting for compute

| stage | data | registration |
|---|---|---|
| 2 | house finch (Youngblood 2024) | [AMENDMENT-0-STAGE2.md](AMENDMENT-0-STAGE2.md), [AMENDMENT-1-FINCH-LOADER.md](AMENDMENT-1-FINCH-LOADER.md) |
| 3 | chimpanzee tool-use actions (Howard-Spink et al. 2024) | [AMENDMENT-2-STAGE3-CHIMP.md](AMENDMENT-2-STAGE3-CHIMP.md), [AMENDMENT-3-STAGE3-CODE.md](AMENDMENT-3-STAGE3-CODE.md) |
| 5 | Cassin's vireo | [AMENDMENT-5-STAGE5-VIREO.md](AMENDMENT-5-STAGE5-VIREO.md), [AMENDMENT-5A-VIREO-LOADER.md](AMENDMENT-5A-VIREO-LOADER.md) |
| 6 | speech | [AMENDMENT-6-STAGE6-SPEECH.md](AMENDMENT-6-STAGE6-SPEECH.md) |
| 7 | European starling | [AMENDMENT-7-STAGE7-STARLING.md](AMENDMENT-7-STAGE7-STARLING.md) |
| 8B | follow-up to stage 8 | [AMENDMENT-8B-STAGE8B.md](AMENDMENT-8B-STAGE8B.md) |

Each governing file was public before the data or simulations it governs were run. The gate
scripts (`gate*.py`) make a job compute nothing until its registration and code on GitHub equal
the job's own copies. Prior work for the whole project is in [PRIOR-WORK.md](PRIOR-WORK.md); the
original plan is [PLAN.md](PLAN.md).

## Files

- `mi_decay.py`: MI-decay pipeline, exponential, power-law and composite fits with AICc, and the
  stage-1 world generators.
- `bf_stage4.py`: stage 4. Streams the Bengalese finch label files (audio never stored, md5
  checked), picks a per-bird k-gram order (k 1 to 8, 5-fold held-out likelihood, Witten-Bell
  smoothing), generates surrogates and bout-order shuffles, runs synthetic self-checks and grades.
- `stage8.py`, `grade8.py`, `stage8b.py`, `grade8b.py`: stage-8 and 8B worlds and grading.
- `mi_stage2.py`, `finch_load.py`, `export_finch.R`: house finch (stage 2).
- `chimp_mi.py`: chimpanzee actions (stage 3). `vireo_stage5.py`, `vireo_s5a.py`: Cassin's vireo.
  `speech_stage6.py`: speech. `starling_stage7.py`: European starling.
- `fetch_data.py`, `get_*.py`, `check_deps7.py`, `manifest.py`: downloads with checksums.
- `test_*.py`: unit tests; `test_reading_*.py` (stdlib only) check that the numbers in each
  reading match the files in `results/`.
- `results/`: derived statistics only (no raw annotations).

## Running the tests

```
git clone https://github.com/munimtechnologies/birdsong-mi-decay-test
cd birdsong-mi-decay-test
pip install numpy scipy
python -m unittest -v test_mi_decay test_bf_stage4 test_reading_stage1 test_reading_bf4 test_reading_stage8
```

Fits use scipy, not the original authors' lmfit. The criterion everywhere is the papers' own:
the composite model has the lowest AICc with relative probability above 0.999.

## Data

Bengalese Finch Song Repository (Nicholson, Queen and Sober; figshare 4805749; CC BY 4.0), house
finch song (Youngblood; Zenodo; CC BY 4.0) and chimpanzee actions (Howard-Spink et al.; Mendeley
Data; CC BY 4.0). Other stages name their sources in their amendments. This repository holds only
code and derived statistics.

## License

Code: Apache-2.0 (see LICENSE). Text and derived data: CC BY 4.0.

# birdsong-mi-decay-test

A pre-registered, calibrated test of a widely used argument for hierarchical, language-like
structure in animal sequences: that mutual information between elements decays as an exponential
plus a power law, and that the power-law part points to hierarchy beyond any Markov process
(Sainburg et al. 2019, Nature Communications; Youngblood 2024, Proceedings of the Royal Society B;
Howard-Spink et al. 2024, PeerJ, for chimpanzee action sequences).

- **Stage 1** measures how often that composite-model verdict fires on simulated sequences made
  by finite-state processes (no recursive hierarchy): single birds with phrase and bout
  timescales, pooled individuals, and a house-finch-like design, with a recursive (Lin-Tegmark)
  model as the positive control.
- **Stage 2** asks whether house finch song exceeds finite-state surrogates fitted to the same
  birds (song-order permutations and a repeat-or-redraw song process).
- **Stage 3** applies the same question to chimpanzee action sequences.

Registration trail (each file was public before the data it governs were opened):

- [PLAN.md](PLAN.md): claims, worlds, grading rules and predictions with priors.
- [AMENDMENT-0-STAGE2.md](AMENDMENT-0-STAGE2.md): stage-2 tests and their self-check.
- [AMENDMENT-1-FINCH-LOADER.md](AMENDMENT-1-FINCH-LOADER.md): the house-finch loader, pinned by
  the authors' own analysis code, with a hard check (C0) that it reproduces their raw MI curve.
- [AMENDMENT-2-STAGE3-CHIMP.md](AMENDMENT-2-STAGE3-CHIMP.md) and
  [AMENDMENT-3-STAGE3-CODE.md](AMENDMENT-3-STAGE3-CODE.md): stage 3.

Code: `mi_decay.py` (MI pipeline, fits, generators), `mi_stage2.py` (stage-2 tests),
`export_finch.R` and `finch_load.py` (house-finch loader), `chimp_mi.py` (stage 3), with unit
tests `test_*.py`. `fetch_data.py` downloads the authors' CC BY 4.0 release with an md5 check;
`get_core.py` and `get_files.py` fetch registered code by git blob SHA; the `gate*.py` scripts
make a job compute nothing until its registration is public.

Results will appear in `results/` with a graded reading. Original data stay with their authors
(house finch: Zenodo doi:10.5281/zenodo.10689807, CC BY 4.0; chimpanzee: Mendeley Data
doi:10.17632/xdtnxzdchj.3, CC BY 4.0); this repository holds only code and derived statistics.

Part of MV2's [calibrated-animal-claims](https://github.com/munimtechnologies/calibrated-animal-claims)
ledger. By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no
human expert has checked it yet. Licence: Apache-2.0 for code, CC BY 4.0 for text.

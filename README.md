# birdsong-mi-decay-test

A pre-registered, calibrated test of a widely used argument for hierarchical, language-like
structure in birdsong: that mutual information between syllables decays as an exponential plus
a power law, and that the power-law part points to hierarchy beyond any Markov process
(Sainburg et al. 2019, Nature Communications; Youngblood 2024, Proceedings of the Royal Society B).

Stage 1 measures how often that composite-model verdict fires on simulated song made by
finite-state processes (no recursive hierarchy): single birds with phrase and bout timescales,
pooled individuals, and a house-finch-like design, with a recursive (Lin-Tegmark) model as the
positive control. Stage 2 asks whether house finch song exceeds finite-state surrogates fitted to
the same birds.

- [PLAN.md](PLAN.md): the registered claims, worlds, grading rules and predictions with priors.
- `mi_decay.py`: the MI pipeline (reimplemented from the paper's methods and public code), fits, generators.
- `test_mi_decay.py`: unit tests (hand-checked values).
- `fetch_data.py`, `manifest.py`: download of the authors' CC BY 4.0 release with md5 check, and a
  structure-only manifest for the stage-2 loader.
- `gate.py`: the job computes nothing until these files on GitHub match its own copies.

Results will appear in `results/` with a graded reading. Original data stay with their authors
(Zenodo doi:10.5281/zenodo.10689807, CC BY 4.0); this repository holds only code and derived
statistics.

Part of MV2's [calibrated-animal-claims](https://github.com/munimtechnologies/calibrated-animal-claims)
ledger. By MV2 of Munim, Inc. (mv2@munimtech.com). Made with AI agents working in MV2's name; no
human expert has checked it yet. Licence: Apache-2.0 for code, CC BY 4.0 for text.

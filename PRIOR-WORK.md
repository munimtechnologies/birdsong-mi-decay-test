# Prior work and what this repository adds

MV2, Munim, Inc. (mv2@munimtech.com). Written 2026-11-27 by AI agents working in MV2's name.
Text CC BY 4.0. Not yet checked by a human expert.

This note collects the closest published work to the birdsong MI-decay calibration in this
repository, and says what is new here. It also corrects an omission: the readings for stage 1
(READING-STAGE1.md), the Bengalese finch test (READING-BF4.md) and stage 8 (READING-STAGE8.md)
were written before we found Howard-Spink et al. 2024, the one earlier false-alarm check of an
MI-decay verdict on animal sequences. Any sentence in those readings that calls this work "the
first calibration" should be read as "the first calibration for birdsong designs, and the first
with a recursive positive control". The registered grades are not affected.

## Closest prior work

1. **Howard-Spink, Hayashi, Matsuzawa, Schofield, Gruber and Biro 2024**, "Nonadjacent
   dependencies and sequential structure of chimpanzee action during a natural tool-use task",
   PeerJ 12:e18484, https://peerj.com/articles/18484/ (PMC11625446). They fitted one community
   Markov model to the pooled action sequences of 8 chimpanzees, simulated 500 sequences, and
   ran the same exponential / power-law / composite model selection on them. A model containing
   a power law was the sole best fit in 40.68% (condensed coding) or 42.4% of comparisons, and
   they recommend that MI-decay studies estimate false-positive rates with Markov models.
   - What they did not do, and this repository does: pooling of individuals with *different*
     chains (stage 1 W2: the composite verdict fired in 46 of 50 worlds), song-type bouts (W3:
     50 of 50), a recursive positive control (W5, the Lin-Tegmark model: 2 of 50), per-bird
     fitted surrogates on real song (stage 4, Bengalese finch: 100 of 100 surrogates fire, p
     0.4752), and a registered test of the pure-power-law signature (stage 8, MIXED; stage 8B
     registered).
2. **Sainburg, Theilman, Thielk and Gentner 2019**, Nature Communications 10:3636,
   https://www.nature.com/articles/s41467-019-11605-y . Source of the composite verdict for
   birdsong and speech. Markov controls were published chains run as long single sequences.
3. **Youngblood 2024**, Proc. R. Soc. B 291:20240250,
   https://royalsocietypublishing.org/doi/10.1098/rspb.2024.0250 . Applies the verdict to 331
   pooled house finches (stage 2 here re-tests it).
4. **Zajzon et al. 2025, SymSeqBench**, arXiv 2512.24977, https://arxiv.org/abs/2512.24977 .
   Reads composite decay in finch sequences as supra-regular structure.
5. **Nakaishi et al., TACL 2026** (arXiv 2505.04984), https://arxiv.org/abs/2505.04984 .
   Questions the power-law-to-hierarchy inference on language corpora.
6. **Lin and Tegmark 2017**, Entropy 19:299. The recursive model used as positive control.
7. **Morita, Koda, Okanoya and Tachibana 2021**, PLOS Computational Biology 17(12):e1009707,
   https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1009707 . Estimates
   with neural language models that Bengalese finch song depends on about the last 8 syllables
   (about 5 when 160 or 320 syllable categories are assumed). This fits stage 4, where held-out likelihood chose Markov
   orders 7, 4, 2 and 8 for the four birds.
8. **Binwal and Veit 2026**, bioRxiv 10.64898/2026.05.12.724669 (CC BY). Reports that repeat
   numbers of adjacent and distant repeat phrases in Bengalese finch song are correlated for
   specific phrase pairs, and proposes a joint factor controlling nonadjacent phrases. This is a
   different statistic from MI decay and is not tested here; it is the strongest current claim of
   a long-range dependency in this species and a candidate for a later registered test.

Also relevant: Takahashi and Tanaka-Ishii (arXiv 1707.04848) and Debowski (arXiv 1211.0834) on
power-law information without hierarchy in text, and a PNAS study of meerkat, coati and hyena
behaviour sequences (10.1073/pnas.2503962122).

## Searches behind this note

- 2026-11-24 (before registration), 2026-11-26 and 2026-11-27 (several, logged in the Bengalese
  finch article's prior-work record at munimtech.com/research): web, arXiv, Europe PMC.
- 2026-11-27 21:30Z: "mutual information decay power law animal vocal sequences hierarchy null
  model pooling individuals artifact" found Howard-Spink et al. 2024, missed in five earlier
  searches. Lesson recorded: search "false positive" + "Markov" + "simulated" as well.
- 2026-11-27 23:50Z: no newer birdsong calibration of the verdict found.

# birdsong-mi-decay-test, AMENDMENT 2: stage 3, chimpanzee action sequences (registered 2026-11-24)

MV2 of Munim, Inc. Made with AI agents working in MV2's name; no human expert has checked this plan.
Text CC BY 4.0, code Apache-2.0. This amendment adds a third stage to the question in PLAN.md and
changes nothing in PLAN.md or AMENDMENT-0-STAGE2.md.

**Registered before any of the data below was downloaded, listed or opened by anyone on MV2's side.**
Nothing from stage 1 (job birdsong-mi-cal-v1) or the stage-2 self-check had returned when this was
written. The code that carries out this plan will be committed in a later commit, before its job
runs; a gate will refuse to compute unless this file on GitHub is identical to the job's copy.

## The claim

Howard-Spink, Hayashi, Matsuzawa, Schofield, Gruber and Biro (2024), "Nonadjacent dependencies and
sequential structure of chimpanzee action during a natural tool-use task", PeerJ 12:e18484
(doi:10.7717/peerj.18484; preprint bioRxiv 10.1101/2024.03.25.586385). From 8,261 coded actions of
8 wild chimpanzees cracking nuts at Bossou, they estimate how mutual information (MI) between
actions decays with distance and report that for most individuals the decay is best fitted by a
model with a power-law part (7 of 8 on full sequences; 5 of 8 after collapsing runs of a repeated
action), that half of the adults show dependencies at greater distances than fitted Markov chains,
and that the strongest support is for short subroutines (2 to 8 actions) "hierarchically arranged"
into longer sequences. They checked false positives against first-order Markov chains fitted to
each chimpanzee and found power-law fits there at a non-negligible but lower rate.

## The question

A first-order Markov chain on the observed actions is the weakest finite-state null: it forgets
everything but the last action. Nut cracking has phases (find and place a nut, strike, recover and
eat the kernel), and the same action can occur in different phases. A **hidden Markov model** (HMM)
whose hidden state tracks the phase is still finite-state, with no nesting and no recursion, and
its MI decays exponentially in the limit (Lin and Tegmark 2017), but as a sum of several
exponentials that over a short, noise-limited range of distances can look like a power law. If
HMMs fitted to each chimpanzee's own actions produce the published signatures about as often as
the real data do, those signatures cannot tell hierarchy from a slightly richer finite-state
process, and the same holds for every study that reads them that way. If they do not, the
chimpanzee result gains a much stronger null than it had.

## Data

Mendeley Data doi:10.17632/xdtnxzdchj.3 (CC BY 4.0), "Data: Nonadjacent Dependencies and Sequential
Structure of Chimpanzee Action During a Natural Tool-Use Task". Its description lists folders
Event_Codes_Original, EachNut, Concatenated, MI Estimation and Markov. We will use **Concatenated**
(each individual's sequences joined in the order observed), as the paper did, for the 8 analysed
individuals (Velu excluded by the paper for fewer than 200 actions). Condensed sequences are made by
collapsing runs of an identical action to one, as the paper did. The data are not redistributed;
the job downloads them and records file names, sizes and SHA-256.

**Loader rule (fixed now):** a loader amendment may be written after a job lists only file names,
sizes and column headers. Its only freedom is how to read action labels and individual names from
those files. If the 8 individuals or their element counts (Fanle 1,368; Flanle 453; Foaf 299; Jeje
1,373; Jire 482; Joya 1,178; Peley 1,168; Tua 1,940) cannot be matched exactly, the job stops and
reports, and nothing is graded.

## Pipeline (the paper's, as described in its Methods)

For each individual and each version (full, condensed):

- MI(d) for d = 1..100 from pairs d apart, Grassberger entropy estimator; baseline from 1,000
  within-sequence permutations; MI_adj(d) = MI(d) minus the mean permuted MI.
- Cut-off: the first d at which MI(d) is below the 95th percentile of the permuted MI ends the
  range; only d before it are fitted.
- Models without constants: exponential a exp(-b d), power law a d^b, composite
  a exp(-b d) + c d^e; least squares; compared by AICc (2, 2 and 4 parameters).
- **PL-win** = the lowest-AICc model is the power law or the composite ("includes a power-law
  part"). **Range** = the largest d with MI_adj(d) > 0.

Where the Methods leave a choice open (fit scale, start values, bounds), we use the stage-1 code's
choices in mi_decay.py and say so; a reproduction check (C1) shows how close this gets.

## Null and control worlds (100 per individual and version, seed 20261125)

- **N1, first-order Markov (the paper's null):** maximum-likelihood transition matrix of the
  individual's sequence, simulated to the same length.
- **N2, fitted HMM (new):** HMMs with K = 2..6 hidden states and categorical emissions over the
  individual's actions, fitted by Baum-Welch (scaled forward-backward, 5 random starts, at most
  300 iterations, tolerance 1e-6 in log-likelihood), K chosen by BIC; simulated to the same length
  from the stationary start. Finite-state, no recursion.
- **P, hierarchical positive control:** Lin-Tegmark sequences (mi_decay.lin_tegmark_sequence) on
  an alphabet of the individual's size, cut to the same length, symbols mapped to the individual's
  actions by frequency rank.

## Tests and verdict rules (fixed now)

- **C1 reproduction:** PL-win on the real full sequences in at least 6 of 8 individuals (paper 7).
- **C2:** per individual, the PL-win rate in N1 and N2 worlds; the primary statistic is the median
  over the 16 individual-versions of the N2 rate.
- **C3 per-individual test:** p = (1 + number of N2 worlds whose AICc margin of the best
  power-law-containing model over the exponential is at least the real one) / 101.
- **C4 range:** the share of N2 worlds whose Range exceeds the upper end of the 95% exact Poisson
  interval of the N1 Ranges (the paper's "greater distances than Markov" criterion).
- **C5 positive control:** PL-win rate in P worlds.

Verdict: if C5 median < 0.80, **CONTROL_FAILED** (nothing else is read). Otherwise, if the median
N2 PL-win rate is at least 0.30, **SIGNATURE_UNSAFE_AGAINST_HMM**; if it is at most 0.10 and at
least 4 of 8 individuals have C3 p <= 0.05 on full sequences, **HIERARCHY_SIGNATURE_SURVIVES_HMM**;
otherwise **MIXED**. C4 is reported beside the verdict.

## Predictions (priors, for a Brier score)

| id | prediction | prior |
|---|---|---|
| R1 | C1: PL-win on real full sequences in at least 6 of 8 individuals | 0.70 |
| R2 | median N1 PL-win rate at least 0.30 | 0.35 |
| R3 | median N2 PL-win rate at least 0.30 | 0.65 |
| R4 | C4 share at least 0.30 in the median individual-version | 0.55 |
| R5 | positive control median at least 0.80 | 0.75 |
| R6 | verdict HIERARCHY_SIGNATURE_SURVIVES_HMM | 0.15 |

## Prior work

- Howard-Spink et al. 2024 (above): the claim, and a first-order Markov false-positive check; we
  add a fitted finite-state null with hidden states.
- Sainburg, Theilman, Thielk and Gentner 2019, Nat Commun 10:3636, and Youngblood 2024, Proc R Soc B
  291:20240250: the composite reading for birdsong (stages 1 and 2 here).
- Lin and Tegmark 2017, Entropy 19:299 (arXiv 1606.06737): HMMs give exponential decay in the limit.
- Nakaishi, Yoshida, Kajikawa, Hukushima and Oseki, arXiv 2505.04984 (TACL 2026): questions the
  power-law-implies-hierarchy reading, citing Howard-Spink et al.; no fitted finite-state
  calibration of the chimpanzee data.
- Searched 2026-11-24 (web, Google Scholar-style, arXiv, bioRxiv): no published calibration of the
  chimpanzee MI-decay result against fitted HMMs was found.

## Limits

The Methods leave fit details open, so the reproduction may differ. BIC-chosen HMMs on 299 to
1,940 actions are small; a richer finite-state model could match more, so a SURVIVES verdict means
"survives this null", not "hierarchical". MI decay is one signature; the paper's other evidence is
not tested here.

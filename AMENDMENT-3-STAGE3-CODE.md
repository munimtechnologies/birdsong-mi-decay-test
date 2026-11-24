# birdsong-mi-decay-test, AMENDMENT 3: stage-3 code choices, loader and two added checks (registered 2026-11-24)

MV2 of Munim, Inc. Made with AI agents working in MV2's name; no human expert has checked this plan.
Text CC BY 4.0, code Apache-2.0. This amendment adds to AMENDMENT-2-STAGE3-CHIMP.md. It changes
nothing in PLAN.md or AMENDMENT-0-STAGE2.md, and nothing in AMENDMENT-2's predictions R1-R6 or its
verdict thresholds.

**Registered before any data file of the chimpanzee study was downloaded or opened by anyone on
MV2's side.** What was read before writing this: the Mendeley item's public file list (names and
sizes only) and the authors' public R scripts 3, 4, 6 and 7 (code only, no data or results). No
stage-1 or stage-2 job has returned. The code is chimp_mi.py with tests in test_chimp_mi.py; the
job's gate (gate_s3.py) refuses to compute unless this file on GitHub is identical to the job's copy.

## Why an amendment

AMENDMENT-2 said that where the paper's Methods leave a choice open, the stage-1 code's choices
would be used. The authors' own scripts (Mendeley doi:10.17632/xdtnxzdchj.3, CC BY 4.0) settle most
of those choices, and two of them differ from what AMENDMENT-2 assumed (the cut-off rule and the fit
scale). Because the claim under test is the authors' result, the pipeline that copies their code
becomes the **primary** pipeline; the AMENDMENT-2 pipeline is kept, unchanged, as the
**secondary** pipeline and reported beside it.

## Loader (the only freedom AMENDMENT-2 allowed)

- File: `Concatenated.zip` (323,483 bytes listed) from the Mendeley item; inside it, for each of the
  8 individuals, the one file whose name is `<name>_all.csv` (fanle, flanle, foaf, jeje, jire, joya,
  peley, tua), as read by the authors' scripts 3 and 4. Action label = the `Event` column; rows in
  file order. Empty and `NA` labels count as rows and are treated as missing (pairs with a missing
  element are dropped, as the authors' `na.omit`).
- The row counts must equal 1,368, 453, 299, 1,373, 482, 1,178, 1,168 and 1,940. Otherwise the job
  writes load_report.json (file names, sizes, headers, row counts only) and stops; nothing is graded.
- Condensed sequence = the concatenated sequence with runs of an identical label collapsed to one
  (the authors' `condense_sequence`, applied after concatenation as in their script 4).
- `MI Estimation.zip` (126,078 bytes listed) is downloaded only for check C0 below.

## Primary pipeline ("paper", from the authors' scripts)

- Pairs (x[i-d], x[i]) over the whole concatenated sequence (not split by video), d = 1..100.
- Entropy log2(N) - (1/N) sum N_i digamma(N_i) for each margin and for the joint; MI = H(a) + H(b) - H(ab).
- 1,000 permutations per distance (one column shuffled against the other, which has the same
  distribution as their shuffling of both); Adjusted_MI = MI - mean permuted MI; lower bound =
  Adjusted_MI - 1.96 x SE, where SE = SD of the permuted MI / sqrt(1000) (their formula).
- index_max = the first d whose lower bound is below 0 (100 if none), as in their script 6; the
  fitted range is d = 1 .. index_max - 1, as in their script 7.
- Models without constants: A exp(-B d), A d^B, A exp(-B d) + C d^D; unweighted least squares on
  the linear scale with no bounds (their nlsLM calls). Starts: theirs ((1, 1); (0.5, -0.1);
  (0.1, 0.1, 0.1, 0.1) and Joya's (-0.1, 0.1, 0.1, 0.1)) plus a small fixed grid and, for the
  composite, the fitted exponential and power law each with the other term set to 0, so the
  composite is never fitted worse than the models it contains. The best residual sum of squares
  over starts is kept; a start that fails is skipped.
- AICc as in AICcmodavg's aictab: Gaussian likelihood with the residual variance counted, so 3, 3
  and 5 parameters; a model needs n - K - 1 > 0 points.
- PL-win = the lowest-AICc model is the power law or the composite.

## Secondary pipeline ("a2", AMENDMENT-2 as registered)

Same MI and permutations; the fitted range ends before the first d whose MI is below the 95th
percentile of the permuted MI; positive Adjusted_MI only; fits on log residuals weighted by
1/log(1 + d) as in stage 1, with the amplitudes kept positive; AICc with 2, 2 and 4 parameters.

## Worlds (as AMENDMENT-2, with these details fixed)

- 100 worlds per individual of each of N1, N2 and P; seed 20261125 (numpy default_rng with
  [seed, individual index, kind index, world]).
- N1: the maximum-likelihood transition matrix of the individual's full sequence (a state with no
  outgoing pair gets the marginal frequencies), started at the individual's first action, simulated
  to the full length.
- N2: HMMs with K = 2..6 fitted to the full sequence (missing labels removed) as AMENDMENT-2;
  number of parameters (K - 1) + K(K - 1) + K(M - 1) for BIC, M = number of action types;
  emission and transition probabilities floored at 1e-10.
- P: Lin-Tegmark sequences on M symbols (depth = ceil(log2 length), cut to the length).
- **Condensed worlds are the full worlds condensed by the same rule as the real data.** The real
  condensed sequence is a function of the real full sequence, so its nulls are the same function
  of the null full sequences. The authors' own condensed Markov runs are commented out in their
  script 4, so this choice does not depart from anything they ran.

## Tests and verdict

C1, C2, C3, C5 and the verdict rules are AMENDMENT-2's, computed with the primary pipeline; the
same quantities from the secondary pipeline are reported, not graded. C4 is computed exactly as the
authors' script 6 does it: per individual-version, the Markov "interval" upper end is
0.5 x qchisq(0.975, 2 X), with X the mean index_max of the 100 N1 worlds (their exactPoiCI as
written), and C4 is the share of N2 worlds whose index_max exceeds it.

Added checks (reported, not part of the verdict):

- **C0, reproduction of their numbers:** for each individual-version whose MI table is in
  `MI Estimation.zip` (`<name>[_condensed]_estimated_MI_perm_1000.csv`, column MInfo), the largest
  absolute difference between our MI and theirs over d = 1..100, and their index_max against ours.
- **C4b, calibration of their distance criterion:** for each N1 world, whether its index_max exceeds
  the interval built from the other 99 N1 worlds. This is the rate at which their "greater
  distance than Markov" call fires on Markov chains themselves. Their interval treats the mean of
  100 runs as a single Poisson count, and its chi-square degrees of freedom are swapped relative
  to the textbook exact interval; C4b measures what that does in practice.

## Added predictions (priors, for the Brier score)

| id | prediction | prior |
|---|---|---|
| R7 | C0: our MI matches theirs within 1e-6 at every compared d in at least 6 of 8 full sequences | 0.60 |
| R8 | C4b: median over the 16 individual-versions at least 0.30 | 0.30 |

## Prior work checked today (2026-11-24)

Searched the web, arXiv and bioRxiv for a calibration of the chimpanzee MI-decay result against
fitted hidden Markov models; none was found. The PeerJ version reports a false-positive check with
community first-order Markov models (500 sequences of 1,000 actions from the whole corpus), in
which a power-law-containing model was preferred in a substantial share of comparisons; our N1 and
N2 worlds are fitted per individual and to each individual's own length. Lin and Tegmark 2017
(arXiv 1606.06737) and Nakaishi et al. (arXiv 2505.04984) remain the theory and critique cited in
AMENDMENT-2; Debowski (arXiv 1211.0834) shows hidden Markov processes with simple graphs can have
power-law block-MI growth, a related but different quantity.

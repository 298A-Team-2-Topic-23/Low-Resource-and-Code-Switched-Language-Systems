# Phase 3 — Thomas Lnu, Shibin

**New: 13 points.** Cycle 5: 298-78, 298-79. Cycle 6: 298-83.
**Still outstanding:** 298-63 (sections 3.3/3.4) and 298-68 (section 4.4), both Urgent and due
10 November; 298-52 with 298-15 and 298-16 now nested under it; 298-59 with 298-23 under it.

You own evaluation. That makes you the person whose work decides whether this project can claim
anything, and it is why your new load is deliberately only three issues: you are carrying the most
outstanding scope on the team.

**Board tidy-up done on your behalf:** 298-15 and 298-16 are now sub-issues of 298-52, and 298-23
is a sub-issue of 298-59. Same work, one parent each, so the board stops reading as though you owe
six independent things when it is really two trees.

---

## Read this about 298-68 before anything else

Its due date moved from 1 November to the 10th, and the reason matters more than the date.

The original argument was that 4.4 must merge **before** 298-53 produces the first real scored run,
because the git log is what makes a pre-registration verifiable. That deadline was 3 November.

298-53 never produced that run. It is still blocked on the GPU, and the only numbers in existence
are smoke tests from a 0.5B stand-in on a synthetic corpus. **So the window is still open** — no
real result exists that could have contaminated the metric choice.

But the original constraint still binds and now outranks the date: **4.4 merges before the first
real scored run, whenever that happens.** If the GPU clears and a real M1 run becomes possible on
the 9th, 4.4 goes first, that day.

---

## 298-78 — Fix the normalisation rules that corrupt forms
`https://linear.app/298a-team-2-topic-23/issue/298-78`
**3 points · due 14 November · Urgent · not blocked**

Normalised chrF++ is the primary metric and the carry-forward table records two defects in it,
unchanged since Workbook 1:

1. The regex rules collapse **3 of 72** variant groups. A metric called "normalised" that normalises
   almost nothing.
2. Two rules **corrupt** forms: `hy` → `y` and `hna` → `na`. These do not merge variants, they
   mangle words, and they fire on any token containing those sequences.

Defect 2 is the serious one. A metric that silently rewrites tokens produces scores wrong in an
unknown direction, and every number this project reports goes through it.

- Delete both corrupting rules, with a test naming the specific forms they were damaging.
- Replace the regex approach with a lookup against the `data/lexicon/` variant groups: map each
  attested surface form to its group's canonical form. The lexicon has 72 groups, 28 with two or
  more spellings. A lookup gets all 28. The regexes get 3.
- Report the collapse rate honestly — groups, token occurrences, and what the metric actually moves
  by on a fixed output file. **If normalisation changes scores by less than noise, that is a
  finding worth stating.** The divergence between raw and normalised chrF++ is supposed to be the
  measurement of how much error is orthographic; if the divergence is nil, that is information
  about the hypothesis, not an embarrassment.

Acceptance: tests prove the corruption is gone, collapse rises to at least 28 groups measured by the
harness, a before/after comparison on one fixed file so the change is auditable, and both
carry-forward rows close.

---

## 298-79 — Paired bootstrap, with the gate written first
`https://linear.app/298a-team-2-topic-23/issue/298-79`
**5 points · due 20 November · must land before any result**

Four models at three seeds is twelve runs and the differences between adjacent rungs will be small.
This is the machinery that decides whether a difference is real.

- **Paired bootstrap over the test set, not over seeds.** Resample sentence indices with
  replacement, score both systems on the same resample, count how often A beats B. This is what
  298-59 committed to and did not implement.
- 95% CIs for each arm **and for each adjacent-rung difference**. A difference interval spanning
  zero means the rung did not help, however good the point estimate looks.
- Seed variance reported **separately** — mean and standard deviation across three seeds. Bootstrap
  CI and seed spread answer different questions, and conflating them overstates confidence.
- A **minimum effect size written down now**, before any number exists: the chrF++ delta below
  which the team calls a rung a null result. Take it from the seed spread on M1, not from the M3
  result.

Acceptance: `--compare <a> <b>` prints the p-value, the difference CI and the verdict against the
pre-registered threshold; tests on synthetic arrays with known answers (identical systems must not
be called different, a planted difference must be detected); the effect size committed with a date;
deterministic under a seed so a reported p-value reproduces exactly.

**Why now and not when results arrive:** once a number exists, every choice about how to test it
looks like a choice made to get that number. Pre-registering is the only thing that makes the
central claim credible, and it is cheap today and impossible later.

---

## 298-83 — Ablation results table and the verdict
`https://linear.app/298a-team-2-topic-23/issue/298-83`
**5 points · due 4 December · Urgent · blocked by 298-79, 298-82**

The one table every reader looks at first, and the verdict underneath it.

Rows: published baseline, M1, M2, Control A, Control B, M3, M4. Columns: normalised chrF++, the
secondary metrics 4.4 commits to, mean and standard deviation across seeds, the 95% bootstrap CI,
and the paired verdict against the rung below. **Every cell generated from the `run.json` files by
`scripts/results_table.py`, not typed.** A cell that has to be typed is a run that did not happen,
and the table should say so.

State plainly which of these the evidence supports:

1. Vocabulary extension helps and the controls isolate it to the vocabulary. The hypothesis holds.
2. The gain exists but Control A matches it — the win is extra pre-training, and section 4.3's
   justification needs rewriting.
3. No rung moves beyond seed noise. The intervention does not help at this scale, and the
   interesting question becomes why a fertility gap of 1.501 against 1.024 does not translate into
   a metric gain.
4. Runs are missing. Name which arms have no numbers and why.

**Outcome 3 is not a failed project.** A measured null on a well-motivated hypothesis, with
controls, is a better 298A result than an unverifiable win, and the spelling-variant burden
measurement stands either way. Outcome 4 is the one to handle carefully: missing arms appear as
explicit gaps, never as blanks, and a partial ladder is never presented as a complete one.

## Order of work

1. 298-63 and 298-68 — Workbook 2, due the 10th. Everything else waits.
2. 298-78 — three points, unblocked, and it fixes a defect that corrupts the primary metric.
3. 298-79 — before any real result exists.
4. 298-83 in Cycle 6.

298-52 and its two children stay open and blocked on the same GPU question as everyone else's model
work. Do not let the baseline reproduction get counted as a Phase 3 commitment until 298-51 clears.

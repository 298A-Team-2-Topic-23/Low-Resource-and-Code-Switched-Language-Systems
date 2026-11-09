# Phase 3 — Savalia, Jenil

**New: 13 points.** Cycle 5: 298-80, 298-81. Cycle 6: 298-84.
**Still outstanding:** 298-21 (800-item gold set) with 298-55 now nested under it.

You have assembled every submission so far and you wrote the annotation guidelines. Phase 3 gives
you the evaluation set's credibility, the next progress report, and the qualitative analysis that
explains *why* the results came out as they did.

**Board tidy-up:** 298-55 is now a sub-issue of 298-21, so the first 200 items read as a stage of
the 800 rather than as a competing issue.

---

## The gold set is the gating item

`data/goldtestset/gold_set.csv` holds a header row and **0 of 800 items**. The project's headline
success criterion is defined on that set, so an empty set means the headline criterion cannot be
evaluated at all. 298-55 (the first 200) was due 5 November.

The guidelines, the schema and the validator are all committed. What is missing is content, and
content is the one thing nobody else can do for you. 298-80 below depends on it, and so does every
result that is not scored on HinGE-test.

If 800 is not reachable, **cut it to 500 formally** with the throughput measurement and the reason
written down, as 298-55's acceptance criteria already allow. A documented cut is fine. A silent
shortfall discovered in December is not.

---

## 298-80 — Inter-annotator agreement: Krippendorff alpha on 100 items
`https://linear.app/298a-team-2-topic-23/issue/298-80`
**3 points · due 18 November · blocked by 298-55**

A hand-authored evaluation set with no agreement measurement is one person's opinion, and a reviewer
will say exactly that.

- Two annotators write Hinglish **independently** for the same 100 items, drawn at random from the
  first 200 rather than hand-picked, blind to each other.
- Compute **Krippendorff alpha** on the acceptability judgements. The machinery exists — 298-30
  fixed the rater-column default.
- Also report **chrF++ between the two annotators' renderings as the ceiling.** No model should be
  expected to beat two humans doing the same task, and this project does not currently know what
  that ceiling is. It belongs in the results section next to the model scores.
- Classify every disagreement: spelling convention, lexical choice, degree of switching, or genuine
  error. Fold the recurring cases back into guidelines v2 with a changelog saying which
  disagreement drove each change.
- **Record annotator region and first language.** Section 3.6.5 names this as the one coverage gap
  still in the team's control — HinGE collected no speaker metadata at all, so representation there
  cannot be checked, only assumed. Mumbai, Bihar and the South romanise differently. This set is
  the one place that gap is fixable.

If alpha comes out low, say so and say what the team will do. A low alpha on a hand-built set is a
finding about task difficulty, not a failure to conceal.

---

## 298-81 — Progress Report 3
`https://linear.app/298a-team-2-topic-23/issue/298-81`
**5 points · due 19 November — CONFIRM ON CANVAS**

The date is inferred, not read off the assignment. PR1 landed around 25 September and PR2 around
22 October, a four-week cadence. **Check the portal and correct the issue's due date first.**

The build is already automated: `scripts/build_report.py` produces the .docx strictly to Template 3
— four parts, fixed rows, fixed columns, five tables. Reuse it. You already refactored the shared
helpers out of it for the workbook builder under 298-71, so the seam exists.

What changes:

- **Part A** — percentages verified against the repository, not estimated. 298-46 is the precedent.
- **Part B** — minutes for every meeting in the window, committed as they happen. Both 298-47 and
  298-43 had to reconstruct minutes afterwards and it is slow and worse.
- **Part C** — **count in Pacific time.** Linear anchors cycles to Pacific midnight; the GitHub API
  reports UTC. Counting in UTC double-counted PR1's work and had to be corrected under 298-48.
  `docs/progress2/part_c_work.md` has the method. This is where both previous reports went wrong,
  and it is why this issue is 5 points and not 2.
- **Part D** — the GPU allocation has been unconfirmed since 26 September and appears here as a
  standing risk **with its age**, not as a new one. Workbook 2 carry-forward items still open go
  here too, rather than quietly disappearing.

---

## 298-84 — Error analysis: 150 outputs coded by failure type
`https://linear.app/298a-team-2-topic-23/issue/298-84`
**5 points · due 2 December · blocked by 298-82**

A chrF++ delta says a model got better. It does not say at what — and this project's claim is
specifically about spelling variance and code-switching, which are visible in outputs and invisible
in an aggregate score.

Sample 50 outputs each from M2, M3 and M4 on the same inputs, **at random**, including cases where
all three agree and cases where they diverge. Do not hand-pick illustrative examples; a reviewer
discounts a qualitative section that reads as cherry-picked, and rightly.

Taxonomy, fixed before looking at the data:

- **Spelling** — right word, non-canonical form. Does M3's extended vocabulary produce *more
  canonical* spellings, or just different ones?
- **Switching** — too little, too much, or at an illicit boundary. Compare output distributions
  against the corpus measurements: mean CMI 25.34, SPF 0.240.
- **Script** — Devanagari leaking into Romanised output. There is already evidence here: the M1
  smoke run leaked Devanagari into **13 of 48** outputs at 0-shot despite a prompt forbidding it,
  and none at 5-shot.
- **Fluency and adequacy** — ordinary generation failures, kept separate so they do not absorb the
  two code-switching-specific categories.
- **Reference artifact** — output is fine, the single reference differed. Section 3.6.3 argues this
  systematically understates models; this quantifies how often.

The key question: **is M3's gain concentrated in the spelling category?** If the vocabulary
intervention works, that is where it must show. If it helps everywhere equally, that is evidence
the mechanism is not the one claimed — which is a real finding and belongs in the report.

Two annotators on an overlapping 30 items, so the coding itself has an agreement number.

## Order of work

1. Gold set content — 298-55 then 298-21. It blocks 298-80 and every non-HinGE result.
2. 298-80 once 200 items exist.
3. 298-81, after confirming the real due date on Canvas.
4. 298-84 in Cycle 6, once M4 exists.

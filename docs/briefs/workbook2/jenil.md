# Jenil Sanjaybhai Savalia — Workbook 2

Two issues, 10 points. One is a rubric point with a trap in it; the other is the assembly and
the three honesty tables.

| Linear | Task | Points | Due | Rubric |
|---|---|---|---|---|
| 298-66 | Section 4.1 Model Proposals, with the model table and the innovation claim | 5 | 4 Nov | 4.1 — 1 pt |
| 298-71 | Assemble and submit `T2.A6.docx`: references, checklist, self-assessment, carry-forward | 5 | 10 Nov | — |

Also still open from the previous period: **298-55** first 200 gold items (8, due 5 Nov).
That one matters beyond Workbook 2 — the 800-item set is at **0 items**, and the project's
headline success criterion is defined on it.

---

## 298-66 — read the rubric band, not the template

> Excellent: "Propose **5 or more** models ... At least one model is **innovative or improved**."
> Good: "Propose 3 or more models ..."

Template 5 asks for four models plus the baseline. **Four alone caps this criterion at 0.8.**

We are not short — there are six configurations, and two of them are already mandatory under the
project's own design, because without them an M3 gain cannot be attributed to anything:

| # | Model | Concept / architecture | Built in | Owner |
|---|---|---|---|---|
| 1 | M1 zero-shot | instruction-tuned backbone, prompted, no training; 0-shot and 5-shot | 298A | Waghmare |
| 2 | M2 PEFT | QLoRA r32 a64 on all seven linear projections, 4-bit NF4, loss masked to completion | 298B | Waghmare |
| 3 | M3 vocab extension + CPT | SentencePiece diff, 3k–8k added tokens, embeddings initialised as the mean of constituent subwords, two-stage training, 10–20% replay | 298B | assign |
| 4 | M4 augmented | back-translation + GCM Equivalence-Constraint synthesis, sampled to match the natural switch-point distribution | 298B | assign |
| 5 | Control A | continued pretraining **without** vocabulary extension | 298B | assign |
| 6 | Control B | M2 retrained to M3's exact GPU-hour budget | 298B | assign |
| — | reproduced baseline | Gahoi et al. 2022, Table 2, MixMT Subtask-1: ROUGE-L 0.617, WER 0.633 | 298A | Thomas Lnu |

Keep the baseline on its own row and state explicitly that it is **not** one of the four. The
template is clear about it and graders check.

### The innovation claim, which we can genuinely make

Prior work blames tokenizer inefficiency on non-Latin script. Hinglish is **already Roman**, so
script cannot be the cause — yet fertility still rises from 1.024 on English to 1.501 on
Hinglish, and vocabulary coverage falls from 98.5% to 52.6% (`reports/fertility.csv`). We
attribute that to orthographic variance and measure it with a metric this project defines:
**spelling-variant burden, 1.832 against a floor of 1.0**, over 72 variant groups and 227
attested surface forms (`reports/spelling_variance.md`).

M3 is the arm that acts on that measurement; Control A is what makes the attribution valid. Say
both. "Innovative" is earned by the metric and the control, not by using the word.

Give each model concept, features, architecture and algorithm **in detail** — that is what the
criterion asks. `CLAUDE.md` section 5 and `docs/workbook1/section_1_4.md` carry the recipes; cite
the hyperparameters rather than paraphrasing them loosely.

Assign owners for M3, M4 and both controls. If it is unclear, raise it at the next meeting —
blank cells in this table read worse than a provisional name.

---

## 298-71 — assembly, and the three tables that carry the honesty

### Build it, do not hand-write it

Extend `scripts/build_report.py` or add a sibling reusing its helpers. It already builds to a
department template from committed Markdown with no `.docx` template file, so it runs from a
clean clone.

**Trap:** `scripts/build_progress_report.py` still writes the older off-template Progress Report
layout to a shared output path. Do not model the new builder on it, and settle whether it is
retired — flagged in 298-61, nobody has acted.

Template 5 exactly, nothing beyond it. Sections 1 and 2 are **not** rewritten; revisions go in
carry-forward. Sections 4.5 and 4.6 stay as bare headings — they are 298A work written up on
7 December, not in this workbook.

### Section owners to collect from

| Section | Issue | Owner |
|---|---|---|
| 3.1, 3.2 | 298-57 | Shevkar |
| 3.3, 3.4 | 298-63 | Thomas Lnu |
| 3.5 | 298-64 | Shevkar |
| 3.6 | 298-65 | Waghmare |
| 4.1 | 298-66 | you |
| 4.2 | 298-67 | Singh |
| 4.3 | 298-69 | Shevkar |
| 4.4 | 298-68 | Thomas Lnu |

### References

Add every source introduced in sections 3 and 4 to the Workbook 1 list. APA, **full author lists,
no "et al." in the reference list** — that was a correction from Progress Report 1 and it should
not come back. New entries will include whichever warehouse 298-70 lands on and anything 298-69
cites.

### Submission checklist

Six rows. The one to actually verify rather than tick: *"Every claim links to a commit, run,
dataset version or Linear issue."* Walk the sections and check.

### Self-assessment and gap register

Rate 3.1–3.6, 4.1–4.4 and References as poor / good / excellent, **against the rubric wording,
not against effort**. If 4.1 ends up listing fewer than five models, it is Good, not Excellent,
and the register should say so with an owner and a date. A self-assessment that rates everything
excellent is the fastest way to lose a grader's trust.

### Carry-forward from Workbook 1

Real items, all evidenced:

- GPU allocation requested 26 September, still unconfirmed (298-51, 298-10). Prakhar's PR #33
  also raises a budget conflict: arm estimates total 177 GPU-hours against the workbook's
  130-hour target and 145-hour cap. That needs a decision recorded here.
- published baseline not reproduced; no mBART code exists anywhere in the repository (298-52)
- gold evaluation set at **0 of 800** items (298-55 — yours)
- bootstrap resampling committed in Workbook 1's requirements, not implemented (298-59)
- harness normalisation covers 3 of the lexicon's 72 groups, and two rules corrupt forms,
  `hy`→`y` and `hna`→`na` (298-59)
- eight issues were marked Done without artifacts and were reset on 22 October
  (`docs/progress2/board_reset_298-45.md`)

### Submission

`T2.A6.docx`, Canvas, due 11 November 11:59 pm; accepted until 12 November, three attempts.
**Keep 298-71 open until the submission is confirmed** — the closing evidence is the receipt, per
the rule from 298-45. Last time the issue went to Done before the upload and we could not tell
which had happened.

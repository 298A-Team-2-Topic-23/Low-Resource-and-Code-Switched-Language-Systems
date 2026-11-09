# Phase 3 work split — beyond Workbook 2

Written 8 November 2026, against `main` at `2a51b16`. Fifteen new Linear issues, **298-72** to
**298-86**, across Cycle 5 (9–23 November) and Cycle 6 (23 November – 7 December).

This is the phase where the project stops building scaffolding and produces results. Everything
before it — the pipeline, the harness, the splits, the fertility measurement, the code-mix
generator — exists to make the four-model ablation measurable. None of that measurement has
happened yet.

## Read this part first

Three things are true at once and the plan has to hold all three:

1. **Workbook 2 is due 11 November and is not finished.** Five sections are still Todo:
   298-63, 298-64, 298-67, 298-68, 298-69. Their due dates have been moved to **10 November** and
   all five are Urgent. Nothing in this document outranks them.
2. **Team Meeting 2 is 12 November** and it checks that the first team-trained model exists.
   298-54 (M2 QLoRA) is the issue that satisfies that, and it is blocked.
3. **No model has been trained on real data.** The GPU allocation (298-10) has been unconfirmed
   since 26 September — forty-four days. Every model issue below sits behind it.

So Phase 3 has a prerequisite that is not technical: somebody has to resolve the compute question
this week, or the plan below runs on Colab at a quarter of the speed and half the arms get cut.

## The critical path

```
298-51  GPU confirmed or fallback funded
   |
   +-- 298-72  compute budget reconciled (177h estimated vs 145h cap)
   |      |
   v      v
298-53  M1 zero-shot, 3 seeds
   |
   v
298-54  M2 QLoRA, 3 seeds          <-- Team Meeting 2 checks this, 12 Nov
   |
   v
298-74  M3 vocabulary extension + Control A + Control B    <-- the project's actual claim
   |
   |     298-76  code-mix generator on a real corpus
   |        |
   v        v
298-82  M4 synthetic code-mix fine-tune
   |
   +-- 298-79  paired bootstrap (must land BEFORE any result)
   |
   v
298-83  ablation results table and the verdict
   |
   v
298-84  error analysis
```

These dependencies are recorded as blocking relations on the board, so Linear will show them.
The one worth memorising: **298-79 has to land before results exist.** A significance test chosen
after seeing the numbers is not a significance test.

## Load per person

| Member | Cycle 5 | Cycle 6 | New points | Still outstanding |
|---|---|---|---|---|
| Waghmare, Sarvesh | 298-74, 298-75 | 298-82 | 18 | 298-53, 298-54 (both blocked) |
| Shevkar, Yash | 298-76, 298-77 | 298-86 | 12 | 298-64, 298-69, 298-58 |
| Thomas Lnu, Shibin | 298-78, 298-79 | 298-83 | 13 | 298-63, 298-68, 298-52, 298-59 |
| Savalia, Jenil | 298-80, 298-81 | 298-84 | 13 | 298-21, 298-55 |
| Singh, Prakhar | 298-72, 298-73 | 298-85 | 8 | 298-67, 298-60, 298-51, 298-56 |

Prakhar and Shibin carry the lightest new load deliberately, because they carry the heaviest
outstanding one. Prakhar's two new issues are both small and both unblock other people, which is
the right shape for someone already behind.

## What each member's file contains

One file per person: `sarvesh.md`, `yash.md`, `shibin.md`, `jenil.md`, `prakhar.md`. Each gives the
Linear id and URL, what the work is, the acceptance criteria in short form, what blocks it, and why
it was assigned to that person rather than someone else.

## Three things this phase is designed to prevent

**Unverifiable numbers.** 298-73 defines a run contract — every run writes a `run.json` with the
commit, the seed, the split hash and the hours. 298-83 then generates the results table from those
files rather than from anyone typing. A cell that cannot be generated is a run that did not happen,
and the table should say so instead of looking complete.

**A result nobody can interpret.** 298-74 carries two controls. If M3 beats M2 but Control A
matches M3, the win is extra pre-training and the tokenizer story is wrong. Without the controls
there is no way to tell those apart, and a reviewer will ask.

**Retrofitted statistics.** 298-79 pre-registers the minimum effect size, dated, before any number
exists. 298-68 does the same for the metrics themselves and its window is still open only because
the blocking run never happened.

## The honest fallback

If the GPU never arrives, the deliverable is a data pipeline, an evaluation harness, a measured
tokenizer problem (fertility 1.501 against 1.024, coverage 52.6% against 98.5%, spelling-variant
burden 1.832 against a floor of 1.0) and a stood-up code-mixing pipeline — with no model results.

That is a real, demonstrable, honest 298A outcome. 298-85 rehearses it as the **primary** demo plan
rather than as an apology, and 298-83's outcome 4 names the missing arms explicitly instead of
presenting a partial ladder as a complete one.

A measured null on a well-motivated hypothesis, with controls, beats an unverifiable win.

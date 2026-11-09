# Carry-forward from Workbook 1

Sections 1 and 2 are not rewritten here. This table records what has changed since Workbook 1 was
submitted, including statements in it that we now know were overstated. State is as checked against
`main` on 7 November 2026.

| Item | Workbook 1 said | State now | Evidence | Owner, issue |
|---|---|---|---|---|
| Fertility and coverage | Sections 1.2 and 1.4: fertility 1.501 against 1.024 "on our data"; AI-5 and AI-6 met | **Corrected further, and the coverage claim should be withdrawn.** Re-measured 9 November on regenerable slices: fertility 1.653 against 1.154, so the gap survives at a ratio of 1.43 against the reported 1.47. **Coverage does not survive**: 54.8% against 53.2%, where Workbook 1 reports 52.6% against 98.5%. Cause identified — the 7 October English slice had 67 distinct word types across 9,866 words, so 98.5% measured how repetitive that slice was. Hinglish coverage barely moved (52.6% to 54.8%), which is the tell. Still synthetic; still illustrative until real HinGE | `reports/fertility_ai6.md`, `reports/fertility_1091_slice.csv` | Waghmare, 298-75 |
| Requirement AI-6 | Met | **Resolved to not met, with a named path to met.** 3 of 4 slices measured on 9 November: en 1.154, hi_roman 1.909, hinglish 1.653, all six AI-6 metrics each. Devanagari Hindi has no source in the repository — `git grep` over U+0900–U+097F returns nothing, the synthetic generator's `hindi` column is empty in all 1,200 rows, and the gold set holds 0 of 800 items. `scripts/make_slices.py --hi-deva-from` is implemented and tested, so closing it needs `HinGE.pkl`, not code | `reports/fertility_ai6.md`, `data/slices/manifest.json` | Waghmare, 298-75 |
| Spelling-variant burden | 1.832, "per surface form" | **Value confirmed, definition corrected.** Re-measured at 1.832 on 7 November with the real tokenizer. It is the mean of per-group means; the per-form mean is 1.863 | `analysis/tokenizer_fertility.py`, `reports/variant_cost_hinge.json` | Waghmare, 298-13 |
| Splits | DR-1 to DR-4 not met | **Closed.** 3,738 / 468 / 468 from 1,938 sources, with 0 exact and 0 near-duplicate overlaps, frozen under SHA-256 | `data/processed/manifests/hinge_split_manifest.json`, `reports/data_statistics.json` | Shevkar, 298-11 |
| Reference count | 4,799 measured against 4,803 published | **Still open.** Both reported | `docs/datasheet.md` | Shevkar, 298-19 |
| GPU allocation | Requested 26 September; unconfirmed | **Still unconfirmed.** The fallback runbook is in open pull request #33, which has no review | PR #33, `docs/COMPUTE_BUDGET.md` | Singh, 298-51, 298-10 |
| Compute budget | 130 GPU-hours target, 145 cap | **Conflict.** `docs/COMPUTE_BUDGET.md` estimates sum to 177 GPU-hours, 32 over the cap. 0.112 hours are spent, all on smoke tests. [PENDING: team decision, either the budget moves or an arm shrinks] | `docs/workbook1/section_2_3_2_4.md`, `docs/COMPUTE_BUDGET.md` | Singh, 298-51 |
| Published baseline | To be reproduced within 0.01 ROUGE-L of 0.617 | **Not reproduced.** No mBART code exists in the repository | `docs/progress2/board_reset_298-45.md` | Thomas Lnu, 298-52 |
| Gold evaluation set | 800 items planned, 0 written | **Still 0 of 800.** The file holds its header row only | `data/goldtestset/gold_set.csv` | Savalia, 298-55 |
| Bootstrap resampling | Committed in AI-3 | **Not implemented** in the harness | `evaluation/run_eval.py` | Thomas Lnu, 298-59 |
| Normalised chrF++ | Regex rules collapse 3 of 72 groups | **Unchanged.** Two rules also corrupt forms: `hy` to `y` and `hna` to `na` | `evaluation/run_eval.py` | Thomas Lnu, 298-59 |
| M3 recipe | 3,000 to 8,000 added tokens, 10–20% replay | **Revision proposed.** Sweep K from 500, start replay at 20%, name the training corpus (section 4.1.3) | `docs/workbook2/section_4_1.md` | Savalia (provisional) |
| Issues marked Done without artifacts | Six named in the self-assessment | **Reset.** Eight issues were audited and reset, each with a comment naming what is missing | `docs/progress2/board_reset_298-45.md` | Singh, performed by Waghmare, 298-45 |
| Reference list quality | 100% conference or journal | **Corrected.** Krippendorff (2011) is a departmental paper, so Workbook 1 was 10 of 11. This list is 18 of 21 | `docs/workbook2/references.md` | Savalia, 298-71 |

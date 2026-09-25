# 50-item pilot runbook

The two CSVs contain the same 50 English sources. Each rater independently enters an integer from 1 to 5 in the three rater columns for the assigned dimension. Do not inspect model output or another rater's values before submitting.

Run both dimensions after all ratings are entered:

```text
python human_eval/agreement.py --csv human_eval/pilot/adequacy.csv --rater-cols rater_a rater_b rater_c
python human_eval/agreement.py --csv human_eval/pilot/fluency.csv --rater-cols rater_a rater_b rater_c
```

Record the printed alpha, pairwise agreement, skipped-item count, and any spread of two or more in the reconciliation notes. A blank rating is allowed only when a rater did not score the item; it is not a substitute for an uncertain score.
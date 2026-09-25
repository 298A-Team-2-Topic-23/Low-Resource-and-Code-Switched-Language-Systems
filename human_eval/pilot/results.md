# Pilot results record

Complete this record only after all three raters have submitted scores.

| Dimension | CSV | Alpha | Usable items | Skipped items | Decision |
| --- | --- | ---: | ---: | ---: | --- |
| Adequacy | `adequacy.csv` | pending | pending | pending | pending |
| Fluency | `fluency.csv` | pending | pending | pending | pending |

## Reconciliation notes

List every item with a rating spread of two or more, the disputed dimension, the agreed interpretation, and whether the guideline needs an update. Do not delete original ratings; record the resolution here.

## Commands used

```text
python human_eval/agreement.py --csv human_eval/pilot/adequacy.csv --rater-cols rater_a rater_b rater_c
python human_eval/agreement.py --csv human_eval/pilot/fluency.csv --rater-cols rater_a rater_b rater_c
```
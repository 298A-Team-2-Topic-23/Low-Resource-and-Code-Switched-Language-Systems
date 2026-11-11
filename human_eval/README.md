# Human evaluation artifacts

The `pilot/` directory contains the fixed 50-item evaluation inputs, scoring rubric, runbook, and result-record template. The agreement script accepts metadata-bearing CSVs when the three rater columns are passed explicitly with `--rater-cols`.

`iaa/PROTOCOL.md` fixes the gold-set agreement measurement (298-80) before any item exists, and `gold_agreement.py` implements it: sampling, blind judging sheets, acceptability alpha, the human chrF++ ceiling and the disagreement sheet.

Do not commit rater identities, private comments, or model outputs into the pilot CSVs. Keep the original ratings unchanged after collection; put reconciled decisions in `pilot/results.md` and update the versioned guidelines only after the meeting.
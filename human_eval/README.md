# Human evaluation artifacts

The `pilot/` directory contains the fixed 50-item evaluation inputs, scoring rubric, runbook, and result-record template. The agreement script accepts metadata-bearing CSVs when the three rater columns are passed explicitly with `--rater-cols`.

Do not commit rater identities, private comments, or model outputs into the pilot CSVs. Keep the original ratings unchanged after collection; put reconciled decisions in `pilot/results.md` and update the versioned guidelines only after the meeting.
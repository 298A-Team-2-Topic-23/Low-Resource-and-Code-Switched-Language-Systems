# Progress Report 2 — Part C: Work Completed This Period

Linear **298-48**. Owner: Prakhar; completed by Sarvesh on 23 October while Prakhar was
unavailable. Reporting period: Cycles 2 and 3, 25 September to 22 October 2026.

This part must agree with the Linear board, and the board is what gets checked. It was
written **after** the 298-45 reset, so the counts below are counts of work a reader can
open, not of issues someone marked Done. The reset is recorded in
`docs/progress2/board_reset_298-45.md`.

Two columns are given because they disagree, and the disagreement is informative. **Issues
closed** is the Linear board. **Pull requests merged** is the GitHub author of the branch
that landed the code. Where one member owns an outcome and another writes the code, the
board records the first and GitHub the second.

| Member | Issues closed | Points | Linear issue IDs | Labels worked | PRs merged | Key artifact |
|---|---|---|---|---|---|---|
| Savalia, Jenil Sanjaybhai | 6 | 19 | 298-12, 298-18, 298-32, 298-42, 298-43, 298-47 | data, writing | 8 — #30, #29, #23, #22, #19, #18, #12, #6 | Minutes for Team Meeting 1 and the 22 Oct session — `docs/minutes/` (PR #29) |
| Thomas Lnu, Shibin Biji | 5 | 16 | 298-14, 298-33, 298-41, 298-44, 298-49 | eval, model, data, writing | 3 — #28, #21, #1 | Part D blockers and critical path — `docs/progress2/part_d_risks.md` (PR #28) |
| Waghmare, Sarvesh | 5 | 15 | 298-30, 298-31, 298-36, 298-39, 298-46 | writing, eval, model, infra | 11 — #27, #25, #24, #16, #15, #14, #13, #9, #8, #7, #2 | QLoRA trainer, Colab notebook and the first GPU run records (PRs #25, #27) |
| Shevkar, Yash | 3 | 16 | 298-34, 298-35, 298-38 | data, research, writing | 2 — #26, #5 | Section 2.1 Data Management Plan (PR #26) |
| Singh, Prakhar Kumar | 2 | 8 | 298-37, 298-40 | infra, writing | 3 — #20, #17, #3 | Demo runbook and two fresh-clone preflight records (PR #20) |
| **Team total** | **21** | **74** | — | all six labels exercised | **27** | — |

Repository: `https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems`

## Reconciliation notes

- **Eight issues were reset from Done to Todo or In Progress** before this table was
  counted, because no artifact existed on `main` for them: 298-10, 298-15, 298-16, 298-17,
  298-21, 298-23, 298-24 and 298-25. Four of the eight had completion timestamps inside
  this reporting window, so the honest issues-closed total fell from 23 to 21. Each reset
  issue carries a comment naming what is missing and the issue that now tracks it. This was
  the single most important piece of work in this part: Progress Report 1 scored poorly on
  exactly this criterion.
- **Assignee and author disagree on 298-34 and 298-38.** Both are assigned to Shevkar on the
  board and landed as PRs #19 and #18 authored by Savalia. Neither column alone is
  complete, which is why both appear above. The same pattern appears in reverse on PRs #15
  and #16, which carry Shibin's branch names but were committed and merged under Sarvesh's
  account.
- **Points are not a proxy for effort.** Shevkar closed three issues for 16 points while
  Sarvesh closed five for 15: the data pipeline alone (298-38) is an 8-point issue. Issue
  counts and point counts rank the team differently and neither should be read as a ranking.
- **Work arrived on three days.** All 27 merges fell on 24–25 September, 7–8 October and
  22 October. No commit landed on `main` between 9 and 21 October — one of the six cycles
  before Team Meeting 2 produced no repository work. Tracked as blocker 7 in Part D.
- **No merged pull request in this window carried a review, and 20 of the 27 were merged by
  their own author.** Branch protection is not enabled on the default branch; the protection
  endpoint returns "Branch not protected". Individual contribution is graded off the
  Linear-to-GitHub chain, so unreviewed self-merges are weak evidence for every member, not
  only for the authors. Tracked as 298-60, due 26 October.
- **Label balance holds, label concentration does not.** All six configured labels were
  exercised and every member carries at least two. But `model` and `infra` work sits with
  two members, which Part D carries as a single-point-of-failure risk rather than a
  reporting artefact.
- **The reset made the cycle look worse, which is the point.** Cycle 3 (12 to 26 October)
  now carries 22 issues and 77 points, of which 7 issues and 20 points are Done. Before the
  reset it read 14 issues and 43 points: returning the eight falsely-Done issues to the open
  column added 33 points of real, unfinished work to the cycle. The cycle will not close on
  scope, and that overrun is stated here rather than absorbed. 298-45 and 298-48 close with
  the pull request that adds this file; 298-50 closes on submission to Canvas.

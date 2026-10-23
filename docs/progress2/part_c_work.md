# Progress Report 2 — Part C: Work Completed This Period

Linear **298-48**. Owner: Prakhar; completed by Sarvesh on 22 October while Prakhar was
unavailable. Reporting period: Cycles 2 and 3, **25 September to 22 October 2026, Pacific
time**.

Pacific time is stated because it changes the counts. Linear anchors its cycle boundaries to
Pacific midnight and the Canvas deadline is Pacific, but the GitHub API reports UTC, which
pushes work done on a California evening into the next day. Five pull requests merged on the
evening of 24 September — #1, #2, #3, #5 and #6 — and three issues closed with them
(298-12, 298-14, 298-18) read as 25 September in UTC. They belong to Progress Report 1,
whose window closed on 24 September, and counting them here would report the same work
twice. They are excluded.

This part must agree with the Linear board, and the board is what gets checked. It was
written **after** the 298-45 reset, so the counts are counts of work a reader can open, not
of issues someone marked Done. The audit is in `docs/progress2/board_reset_298-45.md`.

Two columns are given because they disagree, and the disagreement is the point. **Issues
closed** is the Linear board. **PRs merged** is the GitHub author of the branch that landed
the code. Where one member owns an outcome and another writes it, the board records the
first and GitHub the second.

| Member | Issues closed | Points | Linear issue IDs | Labels worked | PRs merged | Key artifact |
|---|---|---|---|---|---|---|
| Waghmare, Sarvesh | 5 | 15 | 298-30, 298-31, 298-36, 298-39, 298-46 | eval, writing | 11 — #31, #27, #25, #24, #16, #15, #14, #13, #9, #8, #7 | QLoRA trainer, Colab notebook and the first GPU run records (PRs #25, #27) |
| Singh, Prakhar Kumar | 4 | 12 | 298-37, 298-40, 298-45, 298-48 | infra, writing | 2 — #20, #17 | Demo runbook and two fresh-clone preflight records (PR #20) |
| Savalia, Jenil Sanjaybhai | 4 | 11 | 298-32, 298-42, 298-43, 298-47 | writing | 7 — #30, #29, #23, #22, #19, #18, #12 | Minutes for Team Meeting 1 and the 22 Oct session — `docs/minutes/` (PR #29) |
| Thomas Lnu, Shibin Biji | 4 | 11 | 298-33, 298-41, 298-44, 298-49 | data, writing | 2 — #28, #21 | Part D blockers and critical path — `docs/progress2/part_d_risks.md` (PR #28) |
| Shevkar, Yash | 3 | 16 | 298-34, 298-35, 298-38 | data, research, writing | 1 — #26 | Four-stage data pipeline, one command (PR #18 branch `yash/298-38`), and section 2.1 (PR #26) |
| **Team total** | **20** | **65** | — | 5 of 6 labels | **23** | — |

Repository: `https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems`

## Reconciliation notes

- **Eight issues were reset from Done before this table was counted**, because no artifact
  existed on `main`: 298-10, 298-15, 298-16, 298-17, 298-21, 298-23, 298-24 and 298-25. Each
  carries a comment naming what is missing and the issue that now tracks it. Progress
  Report 1 scored in the bottom band on exactly this criterion, so this was the most
  important piece of work in this part.
- **Prakhar's four closed issues overstate his contribution this period, and his two pull
  requests understate it.** He was ill on 22 October. 298-45 and 298-48 are assigned to him
  and closed under his name, but the work was done by Sarvesh and landed as PR #31 — which
  is why Sarvesh's eleven pull requests include it. His real output this period is 298-37
  and 298-40, both merged 7 October. Stated plainly rather than left for a grader to notice.
- **Assignee and author disagree in both directions.** 298-34 and 298-38 are Shevkar's on
  the board and landed as PRs #19 and #18 authored by Savalia; that is why Shevkar shows
  16 points against one pull request — the data pipeline alone (298-38) is eight points.
  PRs #15 and #16 run the other way, carrying Thomas Lnu's branch names but committed and
  merged under Waghmare's account. Neither column alone is honest, which is why both appear.
- **Points and issue counts rank the team differently and neither is a ranking.** Shevkar
  closed the fewest issues and the second-most points; Waghmare closed the most issues and
  fewer points than Shevkar. Reading either column as a league table would be wrong.
- **No model-labelled issue closed this period.** Five of the six configured labels were
  exercised — `data`, `eval`, `infra`, `research`, `writing`. The sixth is `model`, and its
  two open issues (298-53, 298-54) are both In Progress and blocked on the GPU allocation.
  The label gap and Part A row 4.5 say the same thing: no model has been trained.
- **Work landed on two days.** All 23 merges fell on 7 October and 22 October. Nothing
  reached `main` between 8 and 21 October — one of the cycles before Team Meeting 2 produced
  no repository work at all. Tracked as blocker 7 in Part D.
- **No merged pull request in this window carried a review, and 19 of the 23 were merged by
  their own author.** Branch protection is not enabled; the protection endpoint returns
  "Branch not protected". Individual contribution is graded off the Linear-to-GitHub chain,
  so unreviewed self-merges are weak evidence for every member, not only for the authors.
  Tracked as 298-60, due 26 October. PR #31, which carried the reset and this file, was
  itself self-merged — the problem is live, not historical.
- **The reset made the cycle look worse, which is correct.** Cycle 3 (12 to 26 October) now
  carries 22 issues and 77 points, of which 9 issues and 24 points are Done. Before the
  reset it read 14 issues and 43 points: returning the eight falsely-Done issues added 33
  points of real unfinished work. The cycle will miss its scope, and that is stated here
  rather than absorbed.

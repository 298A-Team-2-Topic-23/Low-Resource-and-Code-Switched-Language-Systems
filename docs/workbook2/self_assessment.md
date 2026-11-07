# Self-assessment and gap register

Rated against the rubric wording, not against effort. A section is rated only once it is on `main`
and can be read, so an unwritten section carries no rating rather than an optimistic one.

| Section | Rating | Why |
|---|---|---|
| 3.1 Data Process | [PENDING: not on main] | 298-57 |
| 3.2 Data Collection | [PENDING: not on main] | 298-57 |
| 3.3 Data Pre-processing | [PENDING: not on main] | 298-63 |
| 3.4 Data Transformation | [PENDING: not on main] | 298-63 |
| 3.5 Data Preparation | [PENDING: not on main] | 298-64 |
| 3.6 Data Statistics | Good | The stage table, and the distribution, imbalance and correlation plots and coverage gaps are all present and generated. Held below Excellent because its opening attributes every figure to the real-corpus run, and the fertility and coverage figures it quotes come from a synthetic slice (gap 3) |
| 4.1 Model Proposals | Excellent | Six configurations against the band's "5 or more", the baseline on its own row, and an innovative arm backed by a project-defined metric and a control. The evidence for the claim is uneven, and the section says which numbers are real-corpus and which are not |
| 4.2 Model Supports | [PENDING: not on main] | 298-67 |
| 4.3 Model Comparison and Justification | [PENDING: not on main] | 298-69 |
| 4.4 Model Evaluation Methods | [PENDING: not on main] | 298-68 |
| References | Good | APA with full author lists and no "et al.", and 18 of 21 entries are journal or conference papers. Held below Excellent until sources from the unmerged sections are added |

## Gap register

| # | Gap | Effect | Owner | Date |
|---|---|---|---|---|
| 1 | Sections 3.1, 3.2, 3.5 and 4.3 are not on `main`; they were due 4 to 6 November | Four rubric points unrated | Shevkar | 9 Nov |
| 2 | Sections 3.3, 3.4 and 4.4 are not on `main`. Section 4.4 was due 1 November so that metrics would be committed before results. No real-corpus scored run exists yet, so the commitment still precedes results only if it merges before 298-53 runs | Three rubric points, and the template's before-results rule | Thomas Lnu | 8 Nov |
| 3 | Fertility and coverage have never been measured on real HinGE; the committed figures are from a 1,091-pair synthetic slice. Section 3.6 quotes them as real-corpus figures | Limits 3.6, and limits how far the 4.1 claim can be taken | Waghmare, with the corpus from Thomas Lnu | 9 Nov |
| 4 | Section 4.2 is not on `main`, and no allocation is confirmed | One rubric point, and the compute decision in the carry-forward table | Singh | 9 Nov |
| 5 | Gold set holds 0 of 800 items and the 50-item rater pilot has not run. The first 200 items were due 5 November | The headline success criterion cannot be evaluated on its intended set | Savalia | [PENDING: revised date, to be set at the next meeting] |
| 6 | No corpus is named for M3's continued pretraining beyond the HinGE train split | M3 may underfit; the arm cannot be scheduled | Savalia (provisional) | 7 Dec |
| 7 | Bootstrap intervals and lexicon-driven normalisation are not in the harness (298-59, due 2 November) | No M1-versus-M2 difference can be called significant | Thomas Lnu | 9 Nov |
| 8 | No pull request has a recorded review, and `main` is unprotected (298-60, overdue since 26 October) | Weakens the contribution evidence for all five members | Singh | 9 Nov |
| 9 | The stage samples committed under `reports/samples/` come from the synthetic corpus, and their index says they are not a reportable sample set. Regenerating them needs the real HinGE file | Sections 3.2 to 3.5 each require samples, and cannot quote these as real data | Waghmare, with the corpus from Thomas Lnu | 9 Nov |

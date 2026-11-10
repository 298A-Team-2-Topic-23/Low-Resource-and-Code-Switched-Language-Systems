# Self-assessment and gap register

Rated against the rubric wording, not against effort. A section is rated only once it is on `main`
and can be read, so an unwritten section carries no rating rather than an optimistic one.

| Section | Rating | Why |
|---|---|---|
| 3.1 Data Process | [PENDING: not on main] | 298-57 |
| 3.2 Data Collection | [PENDING: not on main] | 298-57 |
| 3.3 Data Pre-processing | Excellent | Removal counts for all six filters sum to the total, and each threshold is argued from the task. Before and after samples are real HinGE records, and they show two filters catching misaligned pairs. Validation is cited to named tests |
| 3.4 Data Transformation | Excellent | Every transformation has a stated reason and a real sample. The section makes explicit that spelling is never normalised in the corpus, which the hypothesis depends on |
| 3.5 Data Preparation | Excellent | The required split table is complete, and "not stratified" is justified rather than filled. Per-split balance is measured, the leakage gate is shown halting, and the freeze was checked by regenerating byte-identical splits on 9 November |
| 3.6 Data Statistics | Excellent | Rows and columns per stage, distribution, imbalance and correlation plots, a null correlation reported as prominently as the positive one, and five coverage gaps tied to the groups they disadvantage. Fertility is now labelled as synthetic, matching the carry-forward correction |
| 4.1 Model Proposals | Excellent | Six configurations against the band's "5 or more", the baseline on its own row, and an innovative arm backed by a project-defined metric and a control. The evidence for the claim is uneven, and the section says which numbers are real-corpus and which are not |
| 4.2 Model Supports | [PENDING: not on main] | 298-67 |
| 4.3 Model Comparison and Justification | Excellent | Statistical, classical and deep-learning approaches are weighed, and the rejections are argued. Each model is justified by what it rules out, observed outcomes are mapped to conclusions in advance, and five ways the preferred model loses are given with their evidence |
| 4.4 Model Evaluation Methods | Excellent | Metrics are committed before any result, with the commit that first named each. The section commits not to revise after results, and lists the gaps between the committed method and the harness instead of describing a harness that does not exist |
| References | Good | APA, full author lists and no "et al." 21 of 23 entries are journal or conference papers. Held below Excellent until sources from sections 3.1, 3.2 and 4.2 are added |

## Gap register

| # | Gap | Effect | Owner | Date |
|---|---|---|---|---|
| 1 | Sections 3.1 and 3.2 are not on `main` | Two rubric points unrated | Shevkar | 10 Nov |
| 2 | Section 4.2 is not on `main`, and no GPU allocation is confirmed (298-51, 298-10) | One rubric point, and every model result | Singh | 10 Nov |
| 3 | Fertility has never been measured on real HinGE. Every committed fertility figure comes from synthetic slices, although the real file is now in team hands (section 3.5.6) | Limits how far the 4.1 claim can be taken | Waghmare | 12 Nov |
| 4 | Gold set holds 0 of 800 items and the 50-item rater pilot has not run. The first 200 items were due 5 November | The headline success criterion cannot be evaluated on its intended set | Savalia | [PENDING: revised date, to be set at the next meeting] |
| 5 | Compute estimates total 177 GPU-hours against the 145-hour cap | Arms may be cut, which would weaken attribution (section 4.3.5) | Singh, 298-72 | 11 Nov |
| 6 | No corpus is named for M3's continued pretraining beyond the HinGE train split | M3 may underfit; the arm cannot be scheduled | Savalia (provisional) | 7 Dec |
| 7 | Multi-reference scoring, committed in section 4.4.2, is not in the harness | Sources with more references weigh more until it lands | Thomas Lnu | [PENDING: issue to be filed] |
| 8 | No pull request has a recorded review, and `main` is still unprotected (298-60) | Weakens the contribution evidence for all five members | Singh | 12 Nov |

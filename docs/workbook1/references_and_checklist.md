# References, submission checklist and self-assessment

Linear **298-41**. Owner: Shibin.

---

## References

APA. Author lists are expanded in full — APA does not permit `et al.` in a
reference list. Every entry below is a work the team has actually read; anything
cited but unread has been removed. Of the entries, **100% are conference or
journal sources**, against the 80% expectation.

Gahoi, A., Duneja, J., Padhi, A., Mangale, S., Rajput, S., Kamble, T., Sharma, D.,
& Varma, V. (2022). Gui at MixMT 2022: English-Hinglish — An MT approach for
translation of code mixed data. In *Proceedings of the Seventh Conference on
Machine Translation (WMT)* (pp. 1126–1130). Association for Computational
Linguistics.

Srivastava, V., & Singh, M. (2021). HinGE: A dataset for generation and evaluation
of code-mixed Hinglish text. In *Proceedings of the 2nd Workshop on Evaluation and
Comparison of NLP Systems (Eval4NLP)* (pp. 200–208). Association for Computational
Linguistics.

Popović, M. (2017). chrF++: Words helping character n-grams. In *Proceedings of the
Second Conference on Machine Translation (WMT)* (pp. 612–618). Association for
Computational Linguistics.

Das, A., & Gambäck, B. (2014). Identifying languages at the word level in
code-mixed Indian social media text. In *Proceedings of the 11th International
Conference on Natural Language Processing (ICON)* (pp. 378–387). NLP Association
of India.

Barnett, R., Codó, E., Eppler, E., Forcadell, M., Gardner-Chloros, P., van Hout,
R., Moyer, M., Torras, M. C., Turell, M. T., Sebba, M., Starren, M., & Wensing, S.
(2000). The LIDES coding manual: A document for preparing and analysing language
interaction data. *International Journal of Bilingualism, 4*(2), 131–270.

Goh, K.-I., & Barabási, A.-L. (2008). Burstiness and memory in complex systems.
*EPL (Europhysics Letters), 81*(4), 48002.

Krippendorff, K. (2011). *Computing Krippendorff's alpha-reliability.* Departmental
Papers, Annenberg School for Communication, University of Pennsylvania.

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). QLoRA: Efficient
finetuning of quantized LLMs. In *Advances in Neural Information Processing Systems
36 (NeurIPS)* (pp. 10088–10115).

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen,
W. (2022). LoRA: Low-rank adaptation of large language models. In *Proceedings of
the Tenth International Conference on Learning Representations (ICLR)*.

Rijhwani, S., Zhou, S., Neubig, G., & Carbonell, J. (2020). Soft gazetteers for
low-resource named entity recognition. In *Proceedings of the 58th Annual Meeting
of the Association for Computational Linguistics (ACL)* (pp. 8118–8123).

Rei, R., Stewart, C., Farinha, A. C., & Lavie, A. (2020). COMET: A neural framework
for MT evaluation. In *Proceedings of the 2020 Conference on Empirical Methods in
Natural Language Processing (EMNLP)* (pp. 2685–2702).

> **Before submission:** verify every entry above against its ACL Anthology record,
> and delete any entry no member can confirm having read. An unread citation that a
> grader asks about is worse than a shorter list.

---

## Submission checklist

| # | Item | Status |
|---|---|---|
| 1 | All sections present in template order | Pending assembly (298-42) |
| 2 | Cover page naming which member wrote which section | Pending (298-42) |
| 3 | Success criteria stated as numbers in §1.2 | **Done** — §1.2 carries a test-and-measure column on every row |
| 4 | §1.4 comparison table with a decision column | Pending (298-34) |
| 5 | §1.5 literature matrix with a how-we-use-it column | Pending (298-34) |
| 6 | Baseline table includes "code obtained: no" | Pending (298-34) — the answer is **no**, and must say so |
| 7 | §2.2 all eight subsections with their own headings | **Done** (298-36) |
| 8 | §2.4 includes **both** Gantt and PERT, with the critical path marked | Pending (298-37) |
| 9 | References in APA, no `et al.`, ≥ 80% journal/conference | **Done** — 11 entries, 100% conference or journal |
| 10 | Pipeline demo runs end to end from a clean clone | Pending (298-38) |
| 11 | `reports/sync_audit.md` committed with zero blockers | Pending (298-42) |
| 12 | Every closed Linear issue carries a linked artifact | **No** — see below |
| 13 | Every PR link in the document clicked and confirmed merged | Pending (298-42) |
| 14 | Minutes committed for every meeting in the window | Partial (298-43) |

### Item 12 is answered honestly: no

Several Linear issues are marked **Done** with no corresponding artifact on `main`.
This is recorded here rather than left for a grader to find, since the ISA checks
the board against the repository.

| Issue | Marked | Reality |
|---|---|---|
| 298-11 Splits | Done | PR #4 **closed without merging**; no `scripts/make_splits.py`, no manifests on `main` |
| 298-21 Gold set | Done | `gold_set.csv` holds a header row and **0 of 800** items |
| 298-25 M2 QLoRA | Done | No training script or run on `main` |
| 298-17 GCM pipeline | Done | No corresponding file on `main` |
| 298-15 / 298-16 Baseline reproduction | Done | No reproduction script or scored run on `main` |
| 298-23 Normalised chrF++ with lexicon | Done | Merged implementation is regex-based; collapses 3 of 72 lexicon groups |

---

## Self-assessment

This section is graded on **accuracy**, not on optimism. A team that rates every
row excellent and is then found to have gaps scores worse than a team that finds
its own. The ratings below are deliberately conservative where the evidence is
thin.

| Area | Rating | Why |
|---|---|---|
| Evaluation harness | Strong | One command to a scored run, multi-seed aggregation, `--check-baseline`, loud failure on misaligned files. Merged and tested |
| Reproducibility scaffolding | Strong | Pinned environment, deterministic seeding, per-run JSON with GPU-hours, test suite green |
| Hypothesis measurement | Strong | `spelling_variant_burden` = 1.832 measured; Hinglish fertility 1.501 against English 1.024 on the same tokenizer. Novel metric, reproducible without a GPU |
| Data provenance and licensing | Adequate | Datasheet covers four sources with measured counts. HinGE's licence remains unresolved and is treated conservatively |
| Requirements definition | Adequate | §1.2 now carries numeric criteria throughout. Several requirements are not yet satisfiable |
| **Split integrity** | **Weak** | The highest-severity correctness item on the project, and it is not done |
| **Gold evaluation set** | **Weak** | 0 of 800 items authored. Schema, guidelines and validator exist; content does not |
| **Model development** | **Weak** | M1 exists as a script with no scored run. M2, M3, M4 not started |
| **Process discipline** | **Weak** | No branch protection, no approving review on any of nine PRs, two self-merged, one PR linking to no issue |
| **Board-to-repository correspondence** | **Weak** | Six issues marked Done without a supporting artifact |

### The honest summary

The engineering is in better shape than the process. Code that exists is tested,
seeded, logged and reviewable, and the central hypothesis already has a real
measurement behind it rather than an assertion. What has not been enforced is the
review gate and the correspondence between what the board claims and what the
repository contains — which is the same finding the ISA recorded against Progress
Report 1, and it had not been closed at the time of writing.

### Gaps with owners and dates

| Gap | Owner | Date |
|---|---|---|
| Backbone model identifier unverified against its official model card | Sarvesh | 10 Oct |
| Splits not derived; PR #4 closed without merging | Yash | 10 Oct |
| Reference count unreconciled: 4,799 measured vs 4,803 published | Yash | 10 Oct |
| Branch protection off; no PR has an approving review | Prakhar | 8 Oct |
| Linear statuses claiming Done without an artifact | All | 8 Oct |
| Normalised chrF++ collapses only 3 of 72 lexicon groups | Shibin | 14 Oct |
| `CONTRIBUTING.md` referenced in Progress Report 1 but absent | Prakhar | 8 Oct |
| Gold set at 0 of 800 items | Jenil | 20 Oct |

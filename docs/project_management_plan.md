# Project Management Plan: Sections 2.2.1-2.2.8

## 2.2.1 Scope and deliverables

The team will deliver the reproducible English-to-Hinglish research pipeline, including data documentation, model runs, evaluation, analysis, and the team-authored three-column gold set. Jenil owns annotation guidelines, the 50-item pilot, the gold-set data-writing workflow, and this plan's data-management prose. Any scope reduction from 800 to 500 gold items requires a recorded team decision before the frozen split deadline.

## 2.2.2 Work breakdown and ownership

Linear is the source of truth for issue ownership and status. Each issue has one accountable owner, a concrete artifact, acceptance criteria, and a linked pull request. Owners update their issue when work starts, when blocked, and when the artifact is ready for review. Shared reviews are requested in the issue rather than tracked in private messages.

## 2.2.3 Schedule and milestones

The immediate data milestones are: guidelines v1 and the 50-item pilot by 3 October; the 800-item gold set after pilot reconciliation and before the frozen split deadline; and sections 2.2.1-2.2.8 before Workbook 1 on 7 October. A pilot with alpha below 0.67 triggers guideline revision and may move gold-set authoring. If throughput makes 800 items infeasible, the team will freeze a complete 500-item set rather than submit an unfinished set.

## 2.2.4 Quality assurance and acceptance

Data artifacts are accepted only when the schema validates, source and reference rows remain aligned, named entities are checked, and flagged items have a documented resolution. The pilot uses Krippendorff's alpha and pairwise exact agreement. Alpha of at least 0.67 permits progression; 0.40-0.67 requires targeted guideline revision; below 0.40 requires retraining. Code changes require a focused test or smoke command before merge.

## 2.2.5 Version control and review

Work is developed on issue-specific branches named with the owner's identifier and issue number. Pull requests must describe the behavior or artifact added, include validation output, and link the Linear issue. At least one teammate reviews data/schema changes and one teammate reviews executable-code changes. Commits must use the contributor's configured identity and must not include generated model outputs or restricted source data unless the licence decision permits it.

## 2.2.6 Data governance and reproducibility

The repository stores schemas, manifests, guidelines, scripts, and small smoke-test fixtures. Large or restricted datasets stay outside Git and are referenced by documented paths, checksums, licences, and acquisition instructions. Random seeds, package versions, split manifests, and evaluation commands are recorded for every reported result. Orthographic variation in gold references is preserved; normalisation is used only for explicitly labelled evaluation metrics.

## 2.2.7 Risk and escalation

The main risks are low inter-rater agreement, insufficient authoring throughput, licence ambiguity, data leakage across splits, and unavailable compute. Agreement risk is escalated through reconciliation and retraining. Throughput risk is escalated by the 800-to-500 decision rule. Licence risk blocks redistribution until resolved. Leakage risk is checked with source-level overlap audits. Compute risk is handled by logging failed configurations and preserving a smaller reproducible smoke run.

## 2.2.8 Reporting and change control

The team reports milestone status in Linear and records material decisions in the repository documentation. Changes to guidelines, split membership, schema, evaluation metrics, or item-count commitments require a dated rationale and reviewer acknowledgement. The final report cites the exact commit, environment pins, data manifest, pilot agreement result, and any unresolved limitations. Completed work is not marked done until its artifact, validation evidence, and review link are present.
# Progress Report 2 — Part D: Blockers, Risks and Next Period

Linear **298-49**. Owner: Shibin. Reporting period: Cycles 2 and 3, 25 September to
22 October 2026.

Every blocker below was checked against `main` at commit `30fc77c`, the GitHub pull-request
record and the Linear board on 22 October. Where a claim could not be checked it is not made.

## The binding constraint

**Three weeks remain before Team Meeting 2 on 12 November**, and that date cannot move: a
missed graded session scores zero. The checkpoint requires four things —
a cloud pipeline, a live prototype, the published baseline reproduced, and the first model
trained. **None of the four exists today.** Every blocker below is ranked by how directly it
stands between the team and those four items.

The critical path is short and has almost no slack:

```
GPU confirmed (24 Oct) -> M1 scored (3 Nov) -> M2 trained (9 Nov) -> deployed (9 Nov) -> TM2 (12 Nov)
                          baseline reproduced (7 Nov) ------------------------------^
```

Three days separate the last planned delivery from the checkpoint. A slip of more than three
days on any node on that path lands on the demo.

---

## Blockers

| # | Blocker | Evidence | Impact | Owner | Next action and date |
|---|---|---|---|---|---|
| 1 | **No GPU allocation** | Requested 26 Sep; still unconfirmed. The only GPU runs so far used a free Colab Tesla T4 | Blocks the baseline, M1 and M2 — three of the four Team Meeting 2 items | Prakhar | Written answer from the cluster, or the fallback funded and one job run on it, by **24 Oct** (298-51) |
| 2 | **No model trained on the real corpus** | `runs/` holds four model records, all smoke tests on synthetic data with a 0.5B stand-in (`docs/COMPUTE_BUDGET.md`: "None of it is a reportable result"). 298-24 and 298-25 were marked Done without artifacts | Section 4.5 cannot progress; the first-trained-model requirement for 12 Nov is unmet | Sarvesh | M1 scored on three seeds by **3 Nov** (298-53); M2 QLoRA on three seeds by **9 Nov** (298-54) |
| 3 | **Baseline not reproduced** | Gahoi et al. (2022) released no code. 298-15 and 298-16 were marked Done without artifacts and are being reset | This is the project's quality gate: until the harness reproduces a published number, no model result can be interpreted | Shibin | Recipe rebuilt and run under both input conditions by **7 Nov** (298-52) |
| 4 | **Harness gaps that affect that gate** | `evaluation/run_eval.py` has no bootstrap resampling, although requirement AI-2 commits to it. Its regex normalisation fully collapses only 3 of the 72 groups in `analysis/spelling_variants.tsv`, and two rules corrupt words (`hy`→`y`, `hna`→`na`). ROUGE-L and WER are computed on the normalised tokens | No M1-versus-M2 difference can be called significant; the raw-versus-normalised gap measures little; and the baseline is scored on a different tokenisation from the paper's | Shibin | Bootstrap and lexicon-driven normalisation, with a test that fails on the regex version, by **2 Nov** (298-59) |
| 5 | **Gold set at 0 of 800 items** | `data/goldtestset/gold_set.csv` holds no rows | Success criterion AI-1 is defined on this set; without it there is no surface to report the headline result on | Jenil | First 200 items authored and validated by **5 Nov** (298-55); 800-to-500 fallback rule stays in force |
| 6 | **No code review on any recent merge** | The seven pull requests merged since 7 Oct (#21–#27) carry **zero reviews**; six were merged by their own author, #21 included. `main` is unprotected | The Linear-to-GitHub chain is how individual contribution is graded; unreviewed self-merges are weak evidence for every member | Prakhar | Branch protection on and a reviewer rotation published by **26 Oct** (298-60). Every PR after that date carries one non-author approval |
| 7 | **No commits from 8 to 21 October** | `git log` shows the last commit on 7 Oct and the next on 22 Oct | One of the six cycles before the checkpoint produced no repository work | All five; Prakhar tracks | Every member pushes at least one commit against a cycle-4 issue by **26 Oct**, then at least twice a week; Prakhar checks the commit log at each weekly meeting |
| 8 | **Issues marked Done without artifacts** | Eight issues are Done on the board with no linked PR or run: 298-10, 298-15, 298-16, 298-17, 298-21, 298-23, 298-24 and 298-25 | Part A and Part C cannot agree with the board until they are reset | Prakhar | Reset to their true state today, **22 Oct** (298-45) |

---

## Risks not yet blocking

| Risk | Likelihood / impact | Trigger | Mitigation | Owner |
|---|---|---|---|---|
| The baseline cannot reach 0.617 even if rebuilt correctly | High / high | Reproduction lands below 0.60 | The published 0.617 comes after an automatic transliteration step **and** a dictionary-based step whose dictionary was not released; with automatic transliteration alone the paper reports 0.484. Report against both rows, check tokenisation first, and raise the tolerance question with the advisor rather than tune toward the number | Shibin |
| MixMT Subtask-1 test references not obtainable | Medium / high | Codalab download unavailable by 26 Oct | Fall back to the held-out human split of HinGE, as the abstract already states, and say so in the report | Shibin |
| Free-tier GPU is too slow for three seeds of a 7B model | High / medium | One M2 seed takes more than a session | The Colab notebook already persists finished seeds; reduce to a 4B-class backbone only as the plan's stated last resort, never below three seeds for reported results | Sarvesh |
| Zero-shot output in the wrong script | Observed / medium | The 0-shot smoke run produced Devanagari in 13 of 48 outputs | Count it as a failure-taxonomy category rather than filter it; compare against 5-shot, which produced none | Sarvesh |
| Back-translation leaks the test set | Medium / high | HinGE's English comes from the IIT Bombay corpus, which is part of Samanantar | Run the contamination check before any synthetic data is generated (298-58, 9 Nov) | Yash |
| Model scripts disagree on the default backbone | Low / medium | A command-line run omits `--model` | `generate_zeroshot.py` defaults to Qwen3-8B and `train_qlora.py` to Qwen2.5-7B-Instruct; the Colab notebook passes Qwen2.5-7B-Instruct to both, so the planned runs agree. Align the defaults when either script is next touched | Sarvesh |

---

## Outcomes for the next period

Cycle 4 runs from 22 October to 9 November, ending three days before Team Meeting 2.
Five outcomes define success for it. Each is a Linear issue with one owner and a date, and
each is checkable against an artifact rather than a statement.

| # | Outcome | Issue | Owner | Due | Done means |
|---|---|---|---|---|---|
| 1 | GPU access confirmed or the fallback funded and tested | **298-51** | Prakhar | 24 Oct | A run record from the chosen GPU in `runs/` |
| 2 | Published baseline reproduced, or the failure reported with evidence | **298-52** | Shibin | 7 Nov | Scored outputs for both input conditions and a `--check-baseline` result |
| 3 | Model 1 zero-shot scored on three seeds | **298-53** | Sarvesh | 3 Nov | Three run records and a results row with mean ± std |
| 4 | Model 2 QLoRA trained and scored on three seeds | **298-54** | Sarvesh | 9 Nov | Three adapters' run records and a results row with mean ± std |
| 5 | First 200 gold items authored and validated | **298-55** | Jenil | 5 Nov | `validate_gold_set.py --expected-count 200` passes |

Supporting the five, and needed for the same checkpoint:

| Issue | What | Owner | Due |
|---|---|---|---|
| 298-50 | Progress Report 2 assembled and submitted | Jenil | 22 Oct |
| 298-56 | Thin-slice prototype deployed to the cloud for the live demo | Prakhar | 9 Nov |
| 298-57 | Workbook 2 sections 3.1–3.6 written from the real run | Yash | 6 Nov |
| 298-58 | Back-translation source prepared and contamination-checked | Yash | 9 Nov |
| 298-59 | Bootstrap and lexicon-driven normalised chrF++ in the harness | Shibin | 2 Nov |
| 298-60 | Branch protection and reviewer rotation | Prakhar | 26 Oct |

## What would change this plan

- **No GPU by 24 October** moves the baseline, M1 and M2 onto the fallback the same day, and
  the team reports at the next meeting whether three seeds still fit before 9 November.
- **A baseline that misses tolerance** is reported as a finding with evidence. Model results
  are then presented as uninterpreted measurements, and that limitation is stated at Team
  Meeting 2 rather than discovered there.
- **Gold-set throughput below 200 items by 5 November** triggers the recorded 800-to-500
  fallback, and M1/M2 are scored on the HinGE test split in the meantime.

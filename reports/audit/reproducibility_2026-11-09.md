# Reproducibility audit, 9 November 2026

Linear **298-86**, first half. Performed by Shevkar, Yash, against `main` at `fbd1f65`.

**Run this again in the last week before 5 December.** The brief asks for the audit in the last
week so that problems can still be fixed. This first pass is early on purpose: it finds what can be
fixed now. A re-run on the final `main` is what the hand-off can cite. To repeat it, follow the
method below and compare against `commands_2026-11-09.tsv`.

## Method

- A fresh `git clone` of the GitHub repository into an empty directory, so nothing from a working
  copy leaks in.
- A new virtual environment on the machine's stock Python. This is macOS 26 (Darwin 25.5.0) on
  Apple Silicon, with Python 3.9.6 from the Command Line Tools. That matches the "demo laptop"
  row of the README.
- Each command documented in `README.md`, `Makefile`, `analysis/README.md`,
  `human_eval/pilot/README.md`, `data/goldtestset/` and each script's usage line, run in README
  order. Every command was timed and its exit code recorded (`commands_2026-11-09.tsv`; full
  logs were kept outside the repository).
- After each group of commands, `git status` was checked in the clone. A documented command that
  rewrites a committed file is a finding even when it exits 0.
- **Limit.** This is not a machine that had never run the project. The clone and venv were fresh,
  but the person running it already had `HinGE.pkl`. Its absence is recorded as a step that fails
  (step 08) before the file was supplied.

## Result in one table

32 steps in total: 24 succeeded, 8 failed (one of them, step 08, failed as intended).

| Severity | Finding | Step |
|---|---|---|
| **None (the check that outranks everything)** | **The frozen split manifest regenerates byte-identically.** `HinGE.pkl` (sha `e78c8f48…5960`) converts to `hinge.csv` (sha `dcfaf37c…c9c3`), the pipeline writes train/dev/test with the hashes in `data/processed/manifests/hinge_split_manifest.json`, and `git diff` on the manifest is empty. 3,738 / 468 / 468, leakage gate passed. | 12, 13 |
| **High** | **Section 3.6 does not trace in full.** 6 of its 53 numeric claims differ from the artifact they cite (`section_3_6_trace.json`). Four are the fertility and coverage figures 1.024 / 1.501 and 98.5% / 52.6%, attributed to `reports/fertility.csv`. That file now says 1.154 / 1.653 and 53.2% / 54.8%. The quoted values come from the superseded `reports/fertility_1091_slice.csv`. `carry_forward.md` says the coverage claim "should be withdrawn". The section also says every figure is from "the 8 October run on the real HinGE corpus", but `fertility.csv` is measured on synthetic slices (`data/slices/manifest.json`). | trace |
| Low | Section 3.6 says "79.98 / 10.01 / 10.01". The artifact gives 79.97 (3,738 / 4,674). It also says "77% and 90%", where the artifact gives 0.9059, which rounds to 91%. | trace |
| **High** | **The README quickstart overwrites committed real-data results with synthetic ones.** `run_pipeline.py --synthetic` (and `make demo-298-70`) rewrite `reports/data_statistics.json`, `reports/pipeline_monitor.json` and `reports/figures/fig1–4`. The real HinGE statistics become synthetic ones, with nothing to mark the change except `"synthetic": true` inside the JSON. A contributor who follows the README and then runs `git add reports/` commits it. | 07, 11 |
| Medium | **The committed `reports/data_statistics.json` is older than the code.** Regenerating it from the real corpus gives identical measured values but adds a `stages` block (raw/pre-processed/transformed/prepared row and column counts). The committed file was produced on 8 October, before that block existed. Section 3.6.1 says the next run "fills it". It has not been committed since. | 13 |
| Medium | **The full training stack cannot be installed on the team's Macs.** `pip install -r requirements.txt` fails on macOS arm64 because `bitsandbytes==0.47.0` ships only Linux and Windows wheels. A dry-run resolve on Linux x86_64 succeeds for both Python 3.9 and 3.11. The README does not say the full stack is Linux/GPU only. | dry-run |
| Medium | **`results/results.jsonl` cannot be regenerated from a clone.** Its three rows (M1 0-shot, M1 5-shot, M2 QLoRA; 48 lines; Colab T4, 22 October) name hypothesis files under `out/`, which is gitignored. `--report` renders the table, but the numbers behind it cannot be re-scored. They are smoke-test numbers on synthetic data (commit `f8cb929`) and must not be read as results. | 18 |
| Medium | **Figures differ pixel-wise on a fresh machine.** The committed `fig1–6` and the schedule charts were drawn with a font this machine lacks; matplotlib falls back to DejaVu Sans. The fallback font gives the same data with different pixels, so every figure shows as modified after any run. Data identical, checked visually on fig 3. | 13, 22–24 |
| Low | `analysis/tokenizer_fertility.py --corpus … --tokenizer Qwen/…`, documented in the README, fails under `requirements-demo.txt` with "transformers is required". It needs the full stack, so it inherits the macOS problem above. | 10 |
| Low | `python scripts/build_workbook2.py` and `build_report.py` fail with `No module named 'docx'` until `requirements-report.txt` is installed. That file is not mentioned in the README install block. They succeed after it is. `build_report.py` then rewrites the committed `reports/progress2/T2.A5.docx`. | 26, 27, 31, 32 |
| Low | `analysis/README.md` documents `--cmi-only --conll data/hinge_tagged.conll`. The file does not exist, and the same README says so further down. The command fails with a traceback rather than a message. | 19 |
| Low | `human_eval/agreement.py` on the pilot CSVs exits 1 ("need at least one item scored by two or more raters"), because the 50 pilot items carry no ratings yet. The guidelines present it as runnable. | 15, 16 |
| Low | `docs/briefs/jenil.md` tells its reader to run `make presubmit`. No such target exists. | 28 |
| Info | `make_slices.py` without `HinGE.pkl` reports AI-6 "not met: 3 of 4". With the pickle and `--hi-deva-from`, it reports "met: 4 of 4". That rewrites `data/slices/manifest.json`, and the committed version still says not met. | 20, 29 |
| Info | Every pipeline and self-test run writes a new `runs/*.json`. These are committed by design as GPU-hour evidence, so smoke runs by anyone following the README end up in `git status` and can inflate the run count if committed. | all |

## What reproduced exactly

These regenerated with no diff against `main`:

- `data/processed/manifests/hinge_split_manifest.json`: split hashes, counts, params
- `reports/samples/hinge/*.md` (`emit_stage_samples.py`)
- `reports/workbook2_figures.json`: imbalance and both correlations
- `reports/variant_cost_hinge.json`: 1.3955 tokens per occurrence, burden 1.8322
- every measured value in `reports/data_statistics.json`; only timestamps, timings and the
  missing `stages` block differ
- 148 tests passed and 4 skipped in 14 s. `common/repro.py --selftest` and
  `tokenizer_fertility.py --selftest` pass.

End to end, from clone to the real-corpus manifest: about 40 seconds of commands plus 16 s of pip
on a laptop, given `HinGE.pkl`. Without it, nothing on the real corpus runs, and the error message
says where to get it (step 08).

## Not covered by this audit

- Anything that needs a GPU: M1–M4, both controls, the mBART baseline (`models/`). Each is blocked
  on 298-51, and none has a committed run on real data to reproduce.
- The Samanantar/Dakshina steps (298-58, 298-76). They are on open branches, not `main`. Each
  stats file records input and output SHA-256 so it can be audited once merged.
- Byte-level reproducibility across operating systems. The split hashes matched on macOS. Linux
  has not been tried.

## Suggested fixes, smallest first

1. Section 3.6: replace the four fertility/coverage figures with the `fertility.csv` values (or
   cite `fertility_1091_slice.csv` and call them superseded and synthetic). Fix 79.98 to 79.97 and
   90% to 91%. Then `python scripts/audit_section_3_6.py` should exit 0. Owner: Waghmare
   (section author).
2. Point `run_pipeline.py --synthetic` at a separate output directory (for example
   `reports/synthetic/`) so the quickstart cannot overwrite real-corpus artifacts. Owner: Shevkar.
3. Re-run the real pipeline once and commit the refreshed `data_statistics.json` with `stages`.
   Owner: Shevkar.
4. README install block: add `requirements-report.txt`, and say the full stack is Linux + CUDA.
   Owner: Singh (infrastructure).
5. Pin a font that ships with matplotlib (DejaVu Sans) in the figure scripts, so figures
   reproduce pixel for pixel.

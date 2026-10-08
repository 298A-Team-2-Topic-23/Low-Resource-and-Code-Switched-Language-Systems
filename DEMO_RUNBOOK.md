# Workbook 1 demo runbook

Issue [298-40](https://linear.app/298a-team-2-topic-23/issue/298-40).
Owner/opening speaker: Prakhar. Requested review pair: Shibin and Jenil.
Updated 7 October 2026. **Full team rehearsal remains pending.**

## Before rehearsal

The brief planned rehearsals on 5 and 7 October. No 5 October run is asserted.
Two automated checks on 7 October used fresh clones of the pipeline candidate
`jenil/298-38-data-pipeline`, commit
`b7494e5a7db52008fa20bb3c83df9fa76c9b1144`, and synthetic input.
They are preflight checks, not either required real-corpus team rehearsal.
At the checked main commit `d41d6d8`, `scripts/run_pipeline.py` is absent.

Before the full rehearsal, merge the reviewed 298-38 pipeline PR and select its
exact commit on both machines. If rehearsing a candidate branch, say so and
record its SHA; do not present a branch-only artifact as merged.

- Confirm the primary laptop, backup laptop, operators and charging arrangements.
- Use Python 3.10 or newer on both. The default `python3` here is 3.9.6;
  the verified CPU environment uses Python 3.11.14. Explicitly select the interpreter.
- Install dependencies before going offline. The CPU subset below exercises the
  data pipeline and checks; it does not validate CUDA or the full training stack.
- Obtain the authorised real HinGE CSV/TSV from the data owner, per
  `docs/datasheet.md`. Keep it in gitignored `data/raw/`. Confirm its checksum,
  column mapping and reference count; do not substitute the paper's 4,803 for a
  measured count (the datasheet reports 4,799; reconciliation is still open).
- Open the merged pipeline PR with a **non-author approval visible**, the real
  Linear cycle board filtered by assignee, and `reports/data_statistics.json`.
  A requested review is not an approval. These tabs remain preparation tasks.
- Start the stopwatch and a screen recording before speaking. Save the recording
  location, attendees and actual machine details in the rehearsal record.

## Fresh-clone commands — repeat for each full rehearsal

Use a different empty directory for each attempt; do not reuse generated outputs.
Run these after the pipeline is available on the chosen revision:

```bash
git clone https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git rehearsal-1
cd rehearsal-1
git rev-parse HEAD
python3.11 --version
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-demo.txt
python -m pytest tests/ -q
python common/repro.py --selftest
python analysis/tokenizer_fertility.py --selftest
# Copy the authorised real CSV/TSV into data/raw/ before running:
python scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42
```

Repeat in `rehearsal-2`. Record the **whole presentation** duration separately
from the pipeline's execution time. This runbook does not assume the supplied
CSV path exists. Confirm stages 1–4, a stage-3 manifest, a passing leakage gate,
`reports/data_statistics.json`, and all four EDA figures. Inspect source and
`synthetic` fields: synthetic outputs do not evidence a real-corpus run.

## Proposed speaking order — seven-minute target

The team must confirm this order during rehearsal; it is not a claim that anyone
has already spoken or agreed.

| Time | Speaker | Demonstration |
|---|---|---|
| 0:00–0:45 | Prakhar | Task, hypothesis, exact commit, interpreter, and disclosure of real or synthetic input |
| 0:45–1:45 | Jenil | Ingest source, licence caveat, checksum, measured row/reference counts |
| 1:45–3:15 | Yash | Cleaning attrition, language tags, split groups and zero-overlap manifests |
| 3:15–4:45 | Sarvesh | Four EDA figures and spelling-variance evidence; distinguish smoke numbers from corpus findings |
| 4:45–6:15 | Shibin | Leakage failure behavior and evaluation/reproducibility evidence |
| 6:15–7:00 | Prakhar | Review/board artifacts, compute constraints, limitations and handoff |

## Failure plan — agree aloud before the timed run

| Failure | Response |
|---|---|
| Real corpus unavailable / cannot load | Run `python scripts/run_pipeline.py --synthetic --n-synthetic 1200 --seed 42`; explicitly say “This is synthetic fallback input.” It does not fulfil real-corpus rehearsal acceptance |
| Wi-Fi unavailable | Run locally using the already staged corpus and installed dependencies; prepare local screenshots of board/review evidence beforehand |
| Primary laptop fails | Switch to the named, tested backup; backup identity and operator are still pending |
| Leakage gate halts | Do not bypass it. Say “The gate caught an overlap and halted the pipeline.” Show diagnostic output; a halted run must not publish new manifests |
| Live presentation cannot proceed | Show the saved screen recording; recording is still pending |

To demonstrate the failure gate, use synthetic data and an **empty separate**
manifest directory so an older successful manifest cannot be mistaken for a new one:

```bash
python scripts/run_pipeline.py --synthetic --n-synthetic 1200 --seed 42 \
  --inject-leak 1 --no-figures --no-run-log \
  --raw-dir data/raw/leak-demo \
  --processed-dir data/processed/leak-demo \
  --manifest-dir data/processed/leak-demo-manifests \
  --reports-dir reports/leak-demo
```

Expected exit code: 3. Use a new empty output location for repeated failure drills.
The automated preflight verified this halt and absence of newly written manifests.

## Evidence and completion gate

See [preflight record](reports/rehearsals/2026-10-07/README.md) and its raw logs.
Mark 298-40 complete only after both full rehearsals have all of:

- Date/time, exact commit, fresh clone, interpreter and dependency environment.
- Real input provenance/checksum, four stages, four figures, passing gate and manifest.
- All five speakers present, measured presentation duration and agreed failure plan.
- Primary and backup laptop/operator confirmed and tested; recording artifact linked.
- Merged pipeline PR carrying independent approval and current board evidence.

Use this record per rehearsal, replacing each pending field with observed evidence:

| Field | Rehearsal 1 | Rehearsal 2 |
|---|---|---|
| Actual date/time and attendees | Pending | Pending |
| Commit / fresh-clone directory | Pending | Pending |
| Primary / backup machine and operator | Pending | Pending |
| Real corpus path, licence decision, SHA-256 | Pending | Pending |
| Stage logs, manifest, statistics, four figures | Pending | Pending |
| Pipeline seconds / presentation minutes | Pending | Pending |
| All five speakers / failure plan agreed | Pending | Pending |
| Screen recording artifact | Pending | Pending |
| Independently approved merged pipeline PR / board evidence | Pending | Pending |

The PR uses `Refs 298-40` while this gate is incomplete.

# Team Meeting 2 — demo runbook

Written for the presenter to keep open during the session. Every command here was run on
`main` at `d2147ac` and the timings are measured, not estimated.

**Two separate things are assessed.** The professor track is a ≤8 slide deck (17 + 3 min). The
ISA demonstration is 7 rows run live. Rubric line 4.5, *Data Pipeline Demo*, is worth **2 points
— as much as any two written sections** — and it is scored on what you run, not on the document.

---

## Before you start — 5 minutes, do this once

```bash
cd /Users/sarveshwaghmare/Low-Resource-and-Code-Switched-Language-Systems
git checkout main && git pull
```

```bash
python3 scripts/fetch_data.py --only hinge && cp data/raw/hinge/HinGE.csv data/raw/hinge.csv
```

That fetch rewrites the `generated` timestamp in `data/raw/MANIFEST.json` — only the
timestamp, no hash and no content — so `git status` will show it modified. Harmless, but clear
it so nothing is committed by accident:

```bash
git checkout -- data/raw/MANIFEST.json
```

Then open these in tabs so you are never searching mid-demo:

| Tab | What |
|---|---|
| 1 | Terminal, in the repo |
| 2 | `notebooks/tm1_data_pipeline_demo.ipynb` on GitHub (it has saved outputs) |
| 3 | The repo's **Actions** tab — the nightly `pipeline` workflow run history |
| 4 | `reports/m1_m2_comparison.md` |
| 5 | Your Linear board, filtered to you |

**One rule: never run a bare `python3 scripts/run_pipeline.py` without `--reports-dir`.** It
overwrites the committed real-corpus `reports/`. Every command below already redirects.

---

## ISA demonstration — the 7 rows, in order

### Row 1 · Transformations with before/after samples and rationale

**Show:** tab 2, the notebook, section 2. Scroll the six-filter attrition table and the
before/after samples.

**Say:** "Six filters. Each removal is charged to the first filter that rejects it, so the
counts sum to 125 exactly rather than double-counting. The samples show the filters catching
worse defects than their names suggest — both `not_romanized` examples are also misaligned."

*Why the notebook and not a live run: it is committed with outputs, so it cannot fail.*

### Row 2 · Pipeline running on a schedule

**Show:** tab 3, the Actions tab. Point at the run history, then open the most recent run.

**Say:** "It runs nightly at 06:17 UTC, and on every push that touches the pipeline. It installs
nothing — the whole chain is standard library only, so the job cannot fail on somebody else's
release. And it is a gate, not a tick: it fails if the corpus hash changes, if the splits stop
matching the committed manifest, if the leakage gate trips, or on count drift."

**If asked "has it ever failed?"** Yes — the first run, because `ubuntu-latest` moved to Ubuntu
26.04 which no longer ships Python 3.9. The runner is pinned to 22.04 now, because 3.9 is the
oldest version a team machine uses.

### Row 3 · Warehouse contents — and the whole pipeline, source to warehouse

This is the row rubric 4.5 is really about. Run it live, **10 seconds**:

```bash
PYTHONWARNINGS=ignore TRANSFORMERS_VERBOSITY=error python3 scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42 --reports-dir out/real/reports --processed-dir out/real/processed --manifest-dir out/real/manifests --raw-dir out/real/raw --no-run-log
```

*The two environment variables only silence a urllib3 LibreSSL warning and a transformers message about PyTorch being absent — neither is used by the pipeline, but on a projector they read as errors above your output. Without them the run is identical.*

**Then prove it is the committed data, not a fresh guess:**

```bash
python3 -c "import json;c=json.load(open('data/processed/manifests/hinge_split_manifest.json'));f=json.load(open('out/real/manifests/hinge_split_manifest.json'));[print(f\"{s:<6}{f['splits'][s]['records']:>6}  {c['splits'][s]['sha256'][:16]}  {c['splits'][s]['sha256']==f['splits'][s]['sha256']}\") for s in ('train','dev','test')]"
```

**Say:** "Four stages, 9 seconds, and the splits come out byte-identical to the manifest
committed in October. That has now reproduced four times on three machines — twice locally, once
inside Colab, once in CI. No split file is committed, because the corpus is licensed text. What
is committed is the hash and the record ids, which is what makes a result citable without
redistributing data."

**Then the warehouse:**

```bash
make warehouse && make warehouse-demo
```

**Say:** "SQLite, one table per pipeline stage — raw, pre-processed, transformed, prepared — plus
the run log. Six queries over it. The load is idempotent on run id, so re-loading the same run
replaces its rows and leaves other runs alone."

### Row 4 · Monitoring: logs, status, retries, alerts

```bash
python3 scripts/monitor_pipeline.py --stats out/real/reports/data_statistics.json --out out/real/monitor.json --previous reports/pipeline_monitor.json
```

**Say:** "Stage counts, latency per stage, the gate result, retries on the corpus fetch, and
drift against the committed baseline. One command, all four. It reads `drift ok` because this
run matches the baseline — which is the same check CI makes nightly."

**Do not use bare `make monitor` in the demo.** It writes to the committed
`reports/pipeline_monitor.json` and leaves your tree dirty; the command above redirects to
`out/real/` and compares against the committed baseline instead. If you do run it by accident:
`git checkout -- reports/pipeline_monitor.json`.

**⚠️ If you instead run `make demo-298-70`, the monitor prints `drift ALERT`.** That is correct
and you must say so before it appears: *"This is the synthetic offline pipeline, so the monitor
is comparing 1,200 synthetic records against the committed 4,799 real ones and correctly flagging
that the data changed. That is the alert working."* If you would rather not explain it, use
`make monitor` on the real run as above, which prints `drift ok`.

### Row 5 · PROTOTYPE, LIVE — audience picks the input

**The heaviest single row.** Template 7: *if any part of it is mocked, say so before you run it.*

```bash
make demo
```

Opens `http://127.0.0.1:8000`. Ask someone to type an English sentence.

**Say first, before anything is typed:** "Two declarations. Nothing here is mocked — every word
is generated when you press the button, greedy decoding, no cache, so the same sentence twice
gives the same answer. And it is **not deployed** — it runs on this laptop and serves localhost.
Linear 298-56 tracks the deployment and is still open."

**What to point at:** M1 and M2 side by side on the same sentence, with CMI and switch-point
fraction measured live. The interesting part is not that M2 produces Hinglish — it is that M1
often does not.

**If a sentence shows `N words not in the tagger lexicon`:** that is deliberate. The tagger is
lexicon-driven, so a Hindi word outside the 323-entry list is unresolved and CMI understates it.
The page says so at the moment it happens rather than printing a quietly wrong number.

**Needs:** the adapter under `models/adapters/`, about 8 GB free, and **`mlx_lm`, which lives in
`.venv` and not in the system interpreter** — the target resolves `.venv/bin/python`
automatically and prints an install hint if it cannot find the module. Measured on this machine:
**ready in 11 seconds** with both models, 10 with `make demo-light` (M2 only, half the memory).
Generation is 3–7 seconds per sentence.

**A sentence that shows the contrast well**, if nobody volunteers one:
*"Please submit your assignment before Friday."* M1 returns it unchanged at CMI 0.0 — it does not
code-switch at all — while M2 gives *"Please submit your assignment Friday tak."* at CMI 16.67.
That difference is the whole argument for M2 in one line.

### Row 6 · Clone-and-run, from scratch

```bash
cd $(mktemp -d) && git clone -q https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git r && cd r && python3 -m pytest -q
```

**Say:** "Fresh clone, nothing from my machine. The README's four commands fetch the corpus at a
pinned revision, verify its SHA-256, validate it and run the pipeline. I verified this from a
clean clone twice."

**Then come back:** `cd /Users/sarveshwaghmare/Low-Resource-and-Code-Switched-Language-Systems`

### Row 7 · Each member walks their own Linear issues and linked PRs

**Yours:** 298-53 (M1, three seeds), 298-54 (M2, three seeds), 298-75 (real data and AI-6),
298-70 (the TSV defect, warehouse, CI), 298-57 (sections 3.1 and 3.2).

**Say for 298-54:** "Closed with the run records attached — three seeds, NF4 as §4.1 specifies,
1.508 GPU-hours. The comment also records two things the run did not establish: no paired
bootstrap, and no validation loss during training, so nothing defends the final checkpoint."

Naming a limitation yourself is worth more here than claiming a clean win.

---

## The professor deck — what goes on each slide

| Slide | Content you already have |
|---|---|
| 1 Data summary | Stage table 4,799 → 4,674 → 3,738/468/468; leakage 0 exact, 0 near; `fig3_1_lineage.png` |
| 2 Model proposals | §4.1.1's table: six configurations plus the baseline, listed separately |
| 3 Supports and architecture | `fig4_2_1_platform.png` and `fig4_2_2_ml_dataflow.png` |
| 4 Comparison and justification | §4.3.2's table. **"When would your preferred model lose?"** — five answers, and one is now measured, not hypothetical |
| 5 Evaluation methods | §4.4's metrics table with per-metric commitment dates |
| 6 First model trained | chrF++ 40.666 → 51.683, three seeds; `fig7_training_curves.png` **including the 1e-4 run that diverged to NaN**; 3.039 GPU-hours of 165 |
| 7 Baseline reproduction | Not reproduced — and the template allows "what you tried, with evidence". The MixMT test set was never released; CMU DoG replaces the surface |
| 8 Next, risks, asks | M3 and M4; the ask is a confirmed GPU allocation; the risk is Control A costing 36 hours rather than 20 |

**The strongest 30 seconds in the whole session**, for slide 4 or 6:

> "An earlier run had M2 winning chrF++ by 14.5 points while code-switching *less* than M1 —
> CMI 11.88 against a human 25.86. We recorded it as probable undertraining. Three full epochs
> reversed it: M2 now lands on the human target, M-index 0.692 against 0.696. We kept both runs,
> because the disagreement between them is the evidence that one metric was never enough."

That is a result with a story and an admission in it, which is rarer than a clean number.

---

## If something breaks

| Problem | Do this |
|---|---|
| A live command fails | Fall back to tab 2, the notebook with saved outputs. Say you are doing it and why |
| `make demo` is slow to load | It loads a 7B model; say so. `make demo-light` is faster |
| Someone asks for a number you do not have | "It is in the run record, I will send it" beats guessing. Every run is in `runs/` |
| `git status` is dirty after a demo | `git checkout -- reports/` before committing anything |

**Two numbers to have in your head:** M2 cost **1.508 GPU-hours against a 25-hour reservation**,
which 298-72 is signing off unchanged. And the roll-up's **157.04 projection is an upper bound**,
not a forecast — finished arms still project their full allocation because their records predate
the run contract.

# Yash — Workbook 1 brief

**Your issues: 298-34, 298-35, 298-38. 16 points — the heaviest load on the team.**

| Issue | What | Est | Due |
|---|---|---|---|
| [298-38](https://linear.app/298a-team-2-topic-23/issue/298-38) | **Data pipeline — the live demo** | 8 | 6 Oct |
| [298-34](https://linear.app/298a-team-2-topic-23/issue/298-34) | §1.4 / §1.5 surveys with comparison tables | 5 | 5 Oct |
| [298-35](https://linear.app/298a-team-2-topic-23/issue/298-35) | §2.1 Data Management Plan | 3 | 5 Oct |

**Do 298-38 first.** It is 3 of the 15 points, it is live in front of the ISA, and
it is the only one that cannot be written the night before. If you are short on
time, hand 298-34 to Shibin — agree that today, not on the 7th.

Read [README.md](README.md) for setup and the PR workflow before you start.

---

## 298-38 — the pipeline. This is the demo.

The rubric gives half a point per missing component, and there are four:

| Component | Pipeline stage |
|---|---|
| right data sources identified | 1 — provenance table |
| data successfully extracted | 1 — measured row counts |
| and cleaned | 2 — attrition table |
| EDA was performed | 4 — statistics and four figures |

### What to land

The kit ships the whole thing. Copy `repo/` into the repository root:

```
src/lrcs/data/ingest.py        stage 1: provenance, measured counts, synthetic fallback
src/lrcs/data/clean.py         stage 2: six filters with attrition logging, LinCE tagging
src/lrcs/data/splits.py        stage 3: dedupe + split derivation
src/lrcs/data/leakage.py       stage 3: the leakage gate
src/lrcs/analysis/eda.py       stage 4: statistics, spelling-variance, four figures
src/lrcs/analysis/codemixing.py  CMI, switch-point fraction
scripts/run_pipeline.py        one command, all four stages
```

### Run it

```bash
PYTHONPATH=src python scripts/run_pipeline.py --synthetic --n-synthetic 1200
PYTHONPATH=src python scripts/run_pipeline.py --input data/raw/hinge.csv
```

`PYTHONPATH=src` is required — the package lives under `src/` and is not installed.
Put it in the command or add a `.pth`; do not let the demo be the first time
anyone notices.

I ran it on synthetic data: **8.3 seconds, all four stages, four figures written,
leakage gate passed.**

### Before you demo, fix this

**The kit does not run on Python 3.9.** Three modules use `zip(..., strict=False)`,
which is a 3.10+ signature. On 3.9 the pipeline dies at **stage 3 — the split
stage** — which is one of the four graded components. It fails *after* stages 1
and 2 print, so it looks like it is working right up until it isn't.

Seven call sites, in `analysis/codemixing.py`, `analysis/eda.py` and `data/splits.py`.
`strict=False` is the default, so deleting it is a no-op:

```bash
grep -rln "strict=False" src/ | xargs sed -i '' 's/, strict=False)/)/g'
```

Then re-run and confirm stage 3 prints its manifest lines.

### Acceptance criteria

- `python scripts/run_pipeline.py --input data/raw/hinge.csv` runs end to end in
  under five minutes **from a clean clone**
- stage 1 prints path, retrieval timestamp, bytes, SHA-256, and the **measured**
  row count
- stage 2 prints the attrition table, each filter reporting its own removals
- stage 3 re-derives disjoint splits, halts on leakage, writes hashed manifests
- stage 4 prints statistics and writes four figures plus `reports/data_statistics.json`
- `--synthetic` works with no network

Commit a real run of `reports/data_statistics.json`. That file is the evidence
Shibin points at when he closes the demo.

### One thing the kit gets right that is worth saying out loud

`--dup-threshold` is shared by dedupe *and* the leakage gate. When those two used
different thresholds, pairs slipped between them and the gate failed on clean
data. If anyone asks how you know the splits are clean, that is the answer: the
same threshold on both sides, and the gate halts the pipeline rather than warning.

**If the gate halts during the demo, do not bypass it.** Say: *"the gate caught an
overlap and halted the pipeline — that is the gate working. The committed run
passed."* Then show the manifests.

---

## 298-34 — §1.4 and §1.5 surveys

Both rubrics say **comparison**. A list of technologies is not a comparison.

**§1.4 technology survey** — one row per candidate, and a **DECISION** column:

| Candidate | Class | Key features | Fit for us | Decision |
|---|---|---|---|---|

Cover the backbone candidates, the PEFT method, the evaluation stack and the
serving stack. **Do not name a model identifier you have not checked against its
official model card** — an earlier draft named a configuration that does not
exist. Only `Qwen/Qwen2.5-7B-Instruct` has been confirmed to resolve.

**§1.5 literature matrix** — work, class, contribution, limitation, **how we use it**.

**The baseline table** needs: author, year, reported number, **exact table**,
benchmark, code obtained yes/no.

> Gahoi et al. (2022), Table 2, MixMT Subtask-1, ROUGE-L 0.617, WER 0.633.
> **Code obtained: no.**

Say no. It is a tracked risk and claiming otherwise is falsifiable in one click.

Cite only what you actually read. Delete anything unread.

---

## 298-35 — §2.1 Data Management Plan

Five paragraphs: collection, acquisition provenance, three-tier storage, the split
hazard, usage and licensing. Plus a table: source, role, **measured** size, licence,
physical location.

Most of this is already written in [`docs/datasheet.md`](../datasheet.md) — your own
merged work. Pull from it rather than starting over.

Two things that must appear:

**The count discrepancy.** You measured **4,799** human Hinglish references off
`HinGE.pkl`; the paper reports **4,803**. State both and say the reconciliation is
open, with an owner and a date. Hiding it is worse than having it.

**The split hazard.** HinGE's downstream released splits are not mutually
exclusive — your audit found **285 of dev's 376 unique English sources (75.8%)**
also in train. Write that splits are being re-derived, **not that they are done**:
PR #4 was closed without merging, and there is no `scripts/make_splits.py` on main.

Licensing: HinGE has no stated licence. Treat as CC-BY-NC-4.0-equivalent and say
why — it inherits the IIT Bombay corpus restriction through its source pairs.

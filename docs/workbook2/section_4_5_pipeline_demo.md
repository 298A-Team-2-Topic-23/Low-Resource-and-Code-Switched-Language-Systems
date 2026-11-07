# 4.5 Data Pipeline Demo — warehouse, monitoring and management

Author: Shevkar, Yash · Linear **298-70**

Rubric 4.5 asks for a demonstration *from source to data warehouse*, plus
pipeline *monitoring and management*. Ingestion and transformation already
live in `scripts/run_pipeline.py`. This section is the missing half: a
queryable store, a monitor that writes drift into git history, and a
make-style entry point for running and rolling back a demo.

## What already existed

One command, four stages, a leakage gate that **halts** (exit 3, no manifest)
rather than warns:

```bash
python scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42
# offline fallback:
python scripts/run_pipeline.py --synthetic --n-synthetic 1200 --seed 42
```

Outputs: gitignored split TSVs under `data/processed/<source>/`, a committed
manifest, `reports/data_statistics.json`, figures, and a `runs/*.json`
provenance record. That run record is not monitoring — it does not compare
counts across runs or report stage latency against a threshold.

## Warehouse

SQLite file at `data/warehouse/lrcs.sqlite` (gitignored; it holds sentences).
Schema and loader live under `src/lrcs/warehouse/`. Load is idempotent on
`run_id` (`{source}_{seed}_{input_sha256[:12]}`): reloading the same run
deletes that run’s rows and re-inserts; other runs stay.

| Rubric stage | Table | Source |
|---|---|---|
| raw | `raw_records` | re-ingest of the provenance input when the file is on disk |
| pre-processed | `preprocessed_records` | re-clean of that ingest |
| transformed | `transformed_records` | kept rows + LinCE tags as JSON |
| prepared | `prepared_records` | `data/processed/<source>/{train,dev,test}.tsv` |
| run log | `pipeline_runs`, `attrition`, `code_mixing_summary` | `reports/data_statistics.json` |

```bash
python scripts/load_warehouse.py
# or: make warehouse
```

If the input file is missing (raw is gitignored on a fresh clone without a
local copy), prepared rows and aggregates still load; raw / preprocessed /
transformed stay empty and the loader says so. The synthetic demo writes the
input under `data/raw/`, so a full stage load works offline.

### Path to a cloud warehouse

When Prakhar’s cloud prototype (298-56) lands, the same tables map onto
Postgres or BigQuery without changing the stage vocabulary: export each
SQLite table as Parquet or CSV, or replace `sqlite3.connect` with a
Postgres connection string behind the same `load_from_pipeline_outputs`
contract. The local SQLite store is the demo-laptop path; it is not a claim
that production will stay on a laptop file.

## Demo queries

Six SQL files under `warehouse/queries/`, run in order by
`scripts/warehouse_demo.py` (or `make warehouse-demo`):

1. Rows per stage
2. Attrition per filter
3. Split sizes with leakage-gate status
4. Code-mixing summary (CMI, SPF, M-index)
5. References per English source
6. Stage wall-clock latency

These double as live evidence for sections 3.3–3.6.

## Monitoring

```bash
python scripts/monitor_pipeline.py
# or: make monitor
```

Writes `reports/pipeline_monitor.json` with rows in/out, wall-clock per
stage, gate result, and a drift block against the previous committed report.
Default threshold is 1% relative change on ingested / kept / split counts;
any gate flip to failed is an alert. Aggregates only — no sentences — so the
file is safe to commit and drift is visible in `git log -p`.

`--fail-on-drift` exits 5 when an alert fires, for CI or a rehearsal gate.

## Management

| Action | How |
|---|---|
| Schedule / run | `make demo-298-70` (synthetic) or pipeline with `--input` then `make warehouse warehouse-demo monitor` |
| Re-run | same command; warehouse load replaces the same `run_id` |
| Roll back warehouse | delete the `run_id` rows, or delete `data/warehouse/lrcs.sqlite` and reload an older statistics + TSV pair |
| Gate fails | exit 3; **no manifest, no statistics rewrite, do not load the warehouse**. That is the gate working. Fix the overlap or the threshold; do not bypass |
| Degenerate split | exit 4; same rule — nothing downstream |

One-liner for the live demo (no HinGE file required):

```bash
make demo-298-70
```

That runs the synthetic pipeline, loads SQLite, prints the six queries, and
refreshes the monitor report. For the real corpus, convert `HinGE.pkl` once
(see `docs/datasheet.md`), run `scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42`,
then `make warehouse warehouse-demo monitor`.

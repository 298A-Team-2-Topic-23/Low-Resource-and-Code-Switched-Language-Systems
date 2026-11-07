-- Wall-clock seconds per stage for the latest run (pipeline monitoring).
WITH latest AS (
  SELECT run_id, source, seed, synthetic, elapsed_seconds,
         ingest_seconds, clean_seconds, split_seconds, eda_seconds,
         records_ingested, records_kept, gate_passed, loaded_at
  FROM pipeline_runs ORDER BY loaded_at DESC LIMIT 1
)
SELECT run_id,
       source,
       seed,
       CASE WHEN synthetic = 1 THEN 'synthetic' ELSE 'corpus' END AS kind,
       records_ingested,
       records_kept,
       CASE WHEN gate_passed = 1 THEN 'passed' ELSE 'FAILED' END AS leakage_gate,
       ingest_seconds,
       clean_seconds,
       split_seconds,
       eda_seconds,
       elapsed_seconds,
       loaded_at
FROM latest;

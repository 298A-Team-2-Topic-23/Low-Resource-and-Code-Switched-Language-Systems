-- Rows per pipeline stage for the latest loaded run.
-- raw = ingest, preprocessed = cleaned, transformed = tagged, prepared = splits.
WITH latest AS (
  SELECT run_id FROM pipeline_runs ORDER BY loaded_at DESC LIMIT 1
)
SELECT 'raw' AS stage, COUNT(*) AS rows
FROM raw_records WHERE run_id = (SELECT run_id FROM latest)
UNION ALL
SELECT 'preprocessed', COUNT(*)
FROM preprocessed_records WHERE run_id = (SELECT run_id FROM latest)
UNION ALL
SELECT 'transformed', COUNT(*)
FROM transformed_records WHERE run_id = (SELECT run_id FROM latest)
UNION ALL
SELECT 'prepared', COUNT(*)
FROM prepared_records WHERE run_id = (SELECT run_id FROM latest);

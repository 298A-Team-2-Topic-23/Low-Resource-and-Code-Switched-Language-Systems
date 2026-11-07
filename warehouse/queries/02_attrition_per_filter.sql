-- Attrition charged to each of the six cleaning filters (latest run).
WITH latest AS (
  SELECT run_id FROM pipeline_runs ORDER BY loaded_at DESC LIMIT 1
)
SELECT filter_order AS step,
       filter_name,
       rows_in,
       removed,
       rows_out,
       pct_removed
FROM attrition
WHERE run_id = (SELECT run_id FROM latest)
ORDER BY filter_order;

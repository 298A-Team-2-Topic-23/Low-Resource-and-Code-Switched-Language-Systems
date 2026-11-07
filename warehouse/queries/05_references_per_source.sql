-- How many human Hinglish references each English source carries (latest run).
WITH latest AS (
  SELECT run_id FROM pipeline_runs ORDER BY loaded_at DESC LIMIT 1
)
SELECT n_refs AS references_per_source,
       n_sources AS english_sources
FROM references_per_source
WHERE run_id = (SELECT run_id FROM latest)
ORDER BY n_refs;

-- Split sizes with the leakage-gate result for the latest run.
WITH latest AS (
  SELECT run_id, gate_passed, gate_exact, gate_near,
         unique_sources, groups, records_kept
  FROM pipeline_runs ORDER BY loaded_at DESC LIMIT 1
),
sizes AS (
  SELECT split, COUNT(*) AS rows, COUNT(DISTINCT group_id) AS groups
  FROM prepared_records
  WHERE run_id = (SELECT run_id FROM latest)
  GROUP BY split
)
SELECT s.split,
       s.rows,
       ROUND(100.0 * s.rows / l.records_kept, 2) AS pct_of_kept,
       s.groups,
       CASE WHEN l.gate_passed = 1 THEN 'passed' ELSE 'FAILED' END AS leakage_gate,
       l.gate_exact AS exact_overlaps,
       l.gate_near AS near_overlaps,
       l.unique_sources,
       l.groups AS near_dup_groups
FROM sizes s
CROSS JOIN latest l
ORDER BY CASE s.split WHEN 'train' THEN 1 WHEN 'dev' THEN 2 ELSE 3 END;

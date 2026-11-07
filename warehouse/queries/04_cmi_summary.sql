-- Code-mixing characterisation for the latest run (evidence for section 3.6).
WITH latest AS (
  SELECT run_id FROM pipeline_runs ORDER BY loaded_at DESC LIMIT 1
)
SELECT n_sentences,
       ROUND(tagger_coverage, 4) AS tagger_coverage,
       ROUND(cmi_mean_all, 2) AS cmi_mean_all,
       ROUND(cmi_mean_mixed_only, 2) AS cmi_mean_mixed_only,
       ROUND(frac_sentences_mixed, 4) AS frac_sentences_mixed,
       ROUND(switch_point_fraction, 4) AS switch_point_fraction,
       ROUND(m_index, 3) AS m_index,
       ROUND(burstiness, 4) AS burstiness,
       ROUND(mean_span_length, 2) AS mean_span_length
FROM code_mixing_summary
WHERE run_id = (SELECT run_id FROM latest);

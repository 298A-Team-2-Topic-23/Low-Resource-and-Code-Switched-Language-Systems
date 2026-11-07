"""Warehouse schema, idempotent load, and demo-query smoke tests.  [298-70]"""

import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lrcs.warehouse.load import load_from_pipeline_outputs, make_run_id
from lrcs.warehouse.schema import SCHEMA_SQL, connect, init_db

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES = sorted((REPO_ROOT / "warehouse" / "queries").glob("*.sql"))


def _minimal_stats(**overrides):
    stats = {
        "source": "synthetic",
        "synthetic": True,
        "generated_at": "2026-11-06T00:00:00+00:00",
        "elapsed_seconds": 1.5,
        "params": {"seed": 42},
        "provenance": {
            "source": "synthetic",
            "path": "data/raw/missing.tsv",
            "bytes": 100,
            "sha256": "abc123def4567890abc123def4567890abc123def4567890abc123def4567890",
            "rows_in_file": 3,
            "records": 3,
        },
        "attrition": {
            "ingested": 3,
            "kept": 2,
            "removed_total": 1,
            "table": [
                {"filter": "missing_field", "in": 3, "removed": 0, "out": 3, "pct_removed": 0.0},
                {"filter": "not_romanized", "in": 3, "removed": 0, "out": 3, "pct_removed": 0.0},
                {"filter": "untranslated", "in": 3, "removed": 0, "out": 3, "pct_removed": 0.0},
                {"filter": "length_bounds", "in": 3, "removed": 1, "out": 2, "pct_removed": 33.33},
                {"filter": "length_ratio", "in": 2, "removed": 0, "out": 2, "pct_removed": 0.0},
                {"filter": "exact_duplicate", "in": 2, "removed": 0, "out": 2, "pct_removed": 0.0},
            ],
        },
        "splits": {
            "train": {"records": 1},
            "dev": {"records": 1},
            "test": {"records": 0},
        },
        "grouping": {"unique_sources": 2, "groups": 2},
        "leakage_gate": {
            "passed": True,
            "exact_overlaps": 0,
            "near_overlaps": 0,
            "threshold": 0.7,
        },
        "timings_seconds": {
            "ingest": 0.1, "clean": 0.2, "split": 0.3, "eda": 0.4,
        },
        "code_mixing": {
            "n_sentences": 2,
            "tagger_coverage": 0.7,
            "cmi_mean_all": 20.0,
            "cmi_mean_mixed_only": 25.0,
            "frac_sentences_mixed": 0.5,
            "switch_point_fraction": 0.2,
            "m_index": 0.5,
            "burstiness": 0.0,
            "mean_span_length": 3.0,
        },
        "references_per_source": {"distribution": {"1": 2}},
    }
    stats.update(overrides)
    return stats


def _write_splits(processed_dir, source="synthetic"):
    base = Path(processed_dir) / source
    base.mkdir(parents=True)
    header = "id\tgroup\tenglish\thindi\thinglish\n"
    (base / "train.tsv").write_text(
        header + "aaaa\tg0\thello\t\tnamaste yaar\n", encoding="utf-8")
    (base / "dev.tsv").write_text(
        header + "bbbb\tg1\tbye\t\talvida friend\n", encoding="utf-8")
    (base / "test.tsv").write_text(header, encoding="utf-8")


class SchemaTest(unittest.TestCase):

    def test_init_creates_expected_tables(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        names = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in (
            "pipeline_runs", "raw_records", "preprocessed_records",
            "transformed_records", "prepared_records", "attrition",
            "code_mixing_summary", "references_per_source",
        ):
            self.assertIn(table, names)
        self.assertIn("CREATE TABLE IF NOT EXISTS pipeline_runs", SCHEMA_SQL)


class LoadTest(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.processed = self.root / "processed"
        self.stats_path = self.root / "stats.json"
        _write_splits(self.processed)
        self.stats_path.write_text(
            json.dumps(_minimal_stats()) + "\n", encoding="utf-8")
        self.conn = connect(self.root / "lrcs.sqlite")
        self.addCleanup(self.conn.close)

    def test_make_run_id_is_stable(self):
        stats = _minimal_stats()
        self.assertEqual(make_run_id(stats), make_run_id(stats))
        self.assertTrue(make_run_id(stats).startswith("synthetic_42_"))

    def test_load_fills_prepared_and_aggregates_without_input(self):
        summary = load_from_pipeline_outputs(
            self.conn, self.stats_path, processed_dir=self.processed)
        self.assertEqual(summary["prepared"], 2)
        self.assertFalse(summary["input_reloaded"])
        self.assertEqual(summary["raw"], 0)
        n_attr = self.conn.execute(
            "SELECT COUNT(*) FROM attrition WHERE run_id = ?",
            (summary["run_id"],),
        ).fetchone()[0]
        self.assertEqual(n_attr, 6)
        gate = self.conn.execute(
            "SELECT gate_passed FROM pipeline_runs WHERE run_id = ?",
            (summary["run_id"],),
        ).fetchone()[0]
        self.assertEqual(gate, 1)

    def test_reload_same_run_is_idempotent(self):
        first = load_from_pipeline_outputs(
            self.conn, self.stats_path, processed_dir=self.processed)
        second = load_from_pipeline_outputs(
            self.conn, self.stats_path, processed_dir=self.processed)
        self.assertEqual(first["run_id"], second["run_id"])
        n_runs = self.conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        n_prepared = self.conn.execute(
            "SELECT COUNT(*) FROM prepared_records"
        ).fetchone()[0]
        self.assertEqual(n_runs, 1)
        self.assertEqual(n_prepared, 2)

    def test_demo_queries_run_on_loaded_db(self):
        self.assertGreaterEqual(len(QUERIES), 5)
        load_from_pipeline_outputs(
            self.conn, self.stats_path, processed_dir=self.processed)
        for path in QUERIES:
            sql = path.read_text(encoding="utf-8")
            cur = self.conn.execute(sql)
            rows = cur.fetchall()
            self.assertIsNotNone(cur.description, path.name)
            # Empty result is allowed only for refs if distribution missing;
            # our fixture always has data for every query.
            self.assertGreaterEqual(len(rows), 1, path.name)


class MonitorTest(unittest.TestCase):

    def test_build_and_compare_detects_kept_drift(self):
        import importlib.util

        path = REPO_ROOT / "scripts" / "monitor_pipeline.py"
        spec = importlib.util.spec_from_file_location("monitor_pipeline", path)
        mon = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mon)

        stats = _minimal_stats()
        current = mon.build_report(stats)
        previous = mon.build_report(stats)
        previous["rows"]["kept"] = 100
        drift = mon.compare(current, previous, threshold=0.01)
        self.assertFalse(drift["within_threshold"])
        self.assertTrue(any("kept drifted" in a for a in drift["alerts"]))


if __name__ == "__main__":
    unittest.main()

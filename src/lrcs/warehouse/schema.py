"""Warehouse schema.  [298-70]

Stage names follow the rubric language rather than our internal names:

  raw           ingest output (every exploded reference)
  preprocessed  records that survived the six filters
  transformed   the same kept rows with LinCE tags (JSON)
  prepared      split assignment (train / dev / test)

Every fact table is keyed by run_id so a reload of the same run is idempotent
and a new run appends without touching the previous one.
"""

from pathlib import Path
import sqlite3

from lrcs import REPO_ROOT

DEFAULT_DB_PATH = REPO_ROOT / "data" / "warehouse" / "lrcs.sqlite"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id            TEXT PRIMARY KEY,
    source            TEXT NOT NULL,
    synthetic         INTEGER NOT NULL DEFAULT 0,
    seed              INTEGER,
    input_path        TEXT,
    input_sha256      TEXT,
    input_bytes       INTEGER,
    rows_in_file      INTEGER,
    records_ingested  INTEGER,
    records_kept      INTEGER,
    records_removed   INTEGER,
    gate_passed       INTEGER,
    gate_exact        INTEGER,
    gate_near         INTEGER,
    unique_sources    INTEGER,
    groups            INTEGER,
    elapsed_seconds   REAL,
    ingest_seconds    REAL,
    clean_seconds     REAL,
    split_seconds     REAL,
    eda_seconds       REAL,
    generated_at      TEXT,
    loaded_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_records (
    run_id    TEXT NOT NULL,
    seq       INTEGER NOT NULL,
    record_id TEXT NOT NULL,
    english   TEXT NOT NULL,
    hindi     TEXT,
    hinglish  TEXT NOT NULL,
    PRIMARY KEY (run_id, seq),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS preprocessed_records (
    run_id    TEXT NOT NULL,
    record_id TEXT NOT NULL,
    english   TEXT NOT NULL,
    hindi     TEXT,
    hinglish  TEXT NOT NULL,
    PRIMARY KEY (run_id, record_id),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS transformed_records (
    run_id    TEXT NOT NULL,
    record_id TEXT NOT NULL,
    english   TEXT NOT NULL,
    hindi     TEXT,
    hinglish  TEXT NOT NULL,
    tags_json TEXT,
    PRIMARY KEY (run_id, record_id),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS prepared_records (
    run_id    TEXT NOT NULL,
    record_id TEXT NOT NULL,
    split     TEXT NOT NULL,
    group_id  TEXT,
    english   TEXT NOT NULL,
    hindi     TEXT,
    hinglish  TEXT NOT NULL,
    PRIMARY KEY (run_id, record_id),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS attrition (
    run_id      TEXT NOT NULL,
    filter_name TEXT NOT NULL,
    filter_order INTEGER NOT NULL,
    rows_in     INTEGER NOT NULL,
    removed     INTEGER NOT NULL,
    rows_out    INTEGER NOT NULL,
    pct_removed REAL,
    PRIMARY KEY (run_id, filter_name),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS code_mixing_summary (
    run_id                TEXT PRIMARY KEY,
    n_sentences           INTEGER,
    tagger_coverage       REAL,
    cmi_mean_all          REAL,
    cmi_mean_mixed_only   REAL,
    frac_sentences_mixed  REAL,
    switch_point_fraction REAL,
    m_index               REAL,
    burstiness            REAL,
    mean_span_length      REAL,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE TABLE IF NOT EXISTS references_per_source (
    run_id TEXT NOT NULL,
    n_refs INTEGER NOT NULL,
    n_sources INTEGER NOT NULL,
    PRIMARY KEY (run_id, n_refs),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_prepared_split ON prepared_records(run_id, split);
CREATE INDEX IF NOT EXISTS idx_raw_run ON raw_records(run_id);
CREATE INDEX IF NOT EXISTS idx_pre_run ON preprocessed_records(run_id);
"""


def connect(db_path=None):
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn

"""Idempotent warehouse load from pipeline outputs.  [298-70]

Reads the committed statistics JSON and the (gitignored) split TSVs. When the
source file named in provenance is still on disk, re-runs ingest + clean so the
raw / preprocessed / transformed tables hold real rows. Without that file the
loader still fills prepared_records and the aggregate tables, so a machine that
only has the processed splits can load what it has.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from lrcs import REPO_ROOT
from lrcs.data import clean as clean_stage
from lrcs.data import ingest
from lrcs.lexicon import load_variant_groups
from lrcs.warehouse.schema import init_db


FACT_TABLES = (
    "raw_records",
    "preprocessed_records",
    "transformed_records",
    "prepared_records",
    "attrition",
    "code_mixing_summary",
    "references_per_source",
)


def make_run_id(stats):
    """Stable id for one pipeline outcome: source + seed + input hash."""
    prov = stats.get("provenance") or {}
    sha = (prov.get("sha256") or "unknown")[:12]
    seed = (stats.get("params") or {}).get("seed", "noseed")
    source = stats.get("source") or prov.get("source") or "unknown"
    return "{}_{}_{}".format(source, seed, sha)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _delete_run(conn, run_id):
    for table in FACT_TABLES:
        conn.execute("DELETE FROM {} WHERE run_id = ?".format(table), (run_id,))
    conn.execute("DELETE FROM pipeline_runs WHERE run_id = ?", (run_id,))


def _read_split_tsv(path):
    """Read a split TSV exactly as `lrcs.data.splits` wrote it.

    QUOTE_NONE is required, not cosmetic. The writer joins fields with tabs and
    does not quote anything, so a double quote in the text is literal data. The
    csv module's default quotechar is '"', which made it treat 58 quote-bearing
    HinGE rows as the start of a quoted field and swallow the following lines:
    train came back as 3,611 rows instead of 3,738 and test as 383 instead of
    468, with some records emerging with an empty hinglish field that then
    failed the NOT NULL constraint on prepared_records.

    The files themselves were always correct and the split manifest's hashes
    always honoured them. Only this reader was wrong. Synthetic data contains no
    quotes, which is why it took real text to surface it.
    """
    rows = []
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t",
                                quoting=csv.QUOTE_NONE, quotechar=None)
        for row in reader:
            rows.append({
                "id": row["id"],
                "group": row.get("group", ""),
                "english": row["english"],
                "hindi": row.get("hindi") or "",
                "hinglish": row["hinglish"],
            })
    return rows


def _load_prepared(conn, run_id, processed_dir, source):
    base = Path(processed_dir) / source
    total = 0
    for split in ("train", "dev", "test"):
        path = base / "{}.tsv".format(split)
        if not path.exists():
            continue
        for row in _read_split_tsv(path):
            conn.execute(
                "INSERT INTO prepared_records "
                "(run_id, record_id, split, group_id, english, hindi, hinglish) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, row["id"], split, row["group"],
                 row["english"], row["hindi"], row["hinglish"]),
            )
            total += 1
    return total


def _load_attrition(conn, run_id, attrition):
    for i, row in enumerate(attrition.get("table") or []):
        conn.execute(
            "INSERT INTO attrition "
            "(run_id, filter_name, filter_order, rows_in, removed, rows_out, pct_removed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, row["filter"], i, row["in"], row["removed"],
             row["out"], row.get("pct_removed")),
        )


def _load_code_mixing(conn, run_id, cm):
    if not cm:
        return
    conn.execute(
        "INSERT INTO code_mixing_summary "
        "(run_id, n_sentences, tagger_coverage, cmi_mean_all, cmi_mean_mixed_only, "
        " frac_sentences_mixed, switch_point_fraction, m_index, burstiness, mean_span_length) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            cm.get("n_sentences"),
            cm.get("tagger_coverage"),
            cm.get("cmi_mean_all"),
            cm.get("cmi_mean_mixed_only"),
            cm.get("frac_sentences_mixed"),
            cm.get("switch_point_fraction"),
            cm.get("m_index"),
            cm.get("burstiness"),
            cm.get("mean_span_length"),
        ),
    )


def _load_refs_per_source(conn, run_id, distribution):
    for n_refs, n_sources in (distribution or {}).items():
        conn.execute(
            "INSERT INTO references_per_source (run_id, n_refs, n_sources) VALUES (?, ?, ?)",
            (run_id, int(n_refs), int(n_sources)),
        )


def _resolve_input(stats, input_override=None):
    if input_override:
        path = Path(input_override)
        return path if path.exists() else None
    prov = stats.get("provenance") or {}
    rel = prov.get("path")
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path if path.exists() else None


def _load_stage_rows(conn, run_id, input_path, lexicon_path=None):
    """Re-ingest and re-clean so raw / preprocessed / transformed have rows."""
    records, _prov = ingest.ingest_file(input_path)
    # seq is the primary key: content-hash ids collide on exact-duplicate
    # references that the cleaner has not yet removed.
    for seq, r in enumerate(records):
        conn.execute(
            "INSERT INTO raw_records (run_id, seq, record_id, english, hindi, hinglish) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, seq, r["id"], r["english"], r.get("hindi") or "", r["hinglish"]),
        )

    lexicon = load_variant_groups(lexicon_path) if lexicon_path else load_variant_groups()
    kept, _attrition = clean_stage.clean(records, lexicon=lexicon)
    for r in kept:
        conn.execute(
            "INSERT INTO preprocessed_records "
            "(run_id, record_id, english, hindi, hinglish) VALUES (?, ?, ?, ?, ?)",
            (run_id, r["id"], r["english"], r.get("hindi") or "", r["hinglish"]),
        )
        tags = r.get("tags") or []
        conn.execute(
            "INSERT INTO transformed_records "
            "(run_id, record_id, english, hindi, hinglish, tags_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, r["id"], r["english"], r.get("hindi") or "", r["hinglish"],
             json.dumps(tags)),
        )
    return len(records), len(kept)


def load_from_pipeline_outputs(
    conn,
    stats_path,
    processed_dir=None,
    input_path=None,
    lexicon_path=None,
    run_id=None,
):
    """Load one pipeline run into the warehouse. Returns a summary dict."""
    init_db(conn)
    stats_path = Path(stats_path)
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    rid = run_id or make_run_id(stats)
    processed_dir = Path(processed_dir) if processed_dir else REPO_ROOT / "data" / "processed"
    prov = stats.get("provenance") or {}
    attrition = stats.get("attrition") or {}
    gate = stats.get("leakage_gate") or {}
    grouping = stats.get("grouping") or {}
    timings = stats.get("timings_seconds") or {}
    params = stats.get("params") or {}
    source = stats.get("source") or prov.get("source") or "unknown"

    _delete_run(conn, rid)

    conn.execute(
        "INSERT INTO pipeline_runs ("
        " run_id, source, synthetic, seed, input_path, input_sha256, input_bytes,"
        " rows_in_file, records_ingested, records_kept, records_removed,"
        " gate_passed, gate_exact, gate_near, unique_sources, groups,"
        " elapsed_seconds, ingest_seconds, clean_seconds, split_seconds, eda_seconds,"
        " generated_at, loaded_at"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            rid,
            source,
            1 if stats.get("synthetic") else 0,
            params.get("seed"),
            prov.get("path"),
            prov.get("sha256"),
            prov.get("bytes"),
            prov.get("rows_in_file"),
            attrition.get("ingested") or prov.get("records"),
            attrition.get("kept"),
            attrition.get("removed_total"),
            1 if gate.get("passed") else 0,
            gate.get("exact_overlaps"),
            gate.get("near_overlaps"),
            grouping.get("unique_sources"),
            grouping.get("groups"),
            stats.get("elapsed_seconds"),
            timings.get("ingest"),
            timings.get("clean"),
            timings.get("split"),
            timings.get("eda"),
            stats.get("generated_at"),
            _now(),
        ),
    )

    n_prepared = _load_prepared(conn, rid, processed_dir, source)
    _load_attrition(conn, rid, attrition)
    _load_code_mixing(conn, rid, stats.get("code_mixing"))
    _load_refs_per_source(
        conn, rid, (stats.get("references_per_source") or {}).get("distribution"),
    )

    n_raw = n_kept = 0
    stage_source = _resolve_input(stats, input_path)
    if stage_source is not None:
        n_raw, n_kept = _load_stage_rows(conn, rid, stage_source, lexicon_path)

    conn.commit()
    return {
        "run_id": rid,
        "source": source,
        "prepared": n_prepared,
        "raw": n_raw,
        "preprocessed": n_kept,
        "transformed": n_kept,
        "input_reloaded": stage_source is not None,
        "db_path": None,
    }


def open_and_load(db_path, stats_path, **kwargs):
    from lrcs.warehouse.schema import connect

    conn = connect(db_path)
    try:
        summary = load_from_pipeline_outputs(conn, stats_path, **kwargs)
        summary["db_path"] = str(db_path)
        return summary
    finally:
        conn.close()

#!/usr/bin/env python3
"""
Pipeline monitoring: stage counts, latency, gate result, drift.  [298-70]

  python scripts/monitor_pipeline.py
  python scripts/monitor_pipeline.py --stats reports/data_statistics.json \\
      --out reports/pipeline_monitor.json --threshold 0.01

Reads the latest statistics JSON (and optionally the previous committed
monitor report). Writes an aggregate-only JSON so drift shows up in git
history without committing sentence data.

Exit codes: 0 ok, 2 bad input, 5 drift or gate failure detected.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATS = REPO_ROOT / "reports" / "data_statistics.json"
DEFAULT_OUT = REPO_ROOT / "reports" / "pipeline_monitor.json"
DEFAULT_PREV = DEFAULT_OUT


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--stats", default=str(DEFAULT_STATS))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--previous", default=str(DEFAULT_PREV),
                   help="previous monitor report to compare against")
    p.add_argument("--threshold", type=float, default=0.01,
                   help="relative drift on kept / ingested rows that raises an alert")
    p.add_argument("--fail-on-drift", action="store_true",
                   help="exit 5 when drift or a failed gate is reported")
    return p.parse_args(argv)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_report(stats):
    attrition = stats.get("attrition") or {}
    gate = stats.get("leakage_gate") or {}
    timings = stats.get("timings_seconds") or {}
    prov = stats.get("provenance") or {}
    splits = stats.get("splits") or {}
    return {
        "generated_at": _now(),
        "source": stats.get("source"),
        "synthetic": bool(stats.get("synthetic")),
        "pipeline_generated_at": stats.get("generated_at"),
        "input_sha256": prov.get("sha256"),
        "seed": (stats.get("params") or {}).get("seed"),
        "rows": {
            "in_file": prov.get("rows_in_file"),
            "ingested": attrition.get("ingested") or prov.get("records"),
            "kept": attrition.get("kept"),
            "removed": attrition.get("removed_total"),
            "train": (splits.get("train") or {}).get("records"),
            "dev": (splits.get("dev") or {}).get("records"),
            "test": (splits.get("test") or {}).get("records"),
        },
        "timings_seconds": {
            "ingest": timings.get("ingest"),
            "clean": timings.get("clean"),
            "split": timings.get("split"),
            "eda": timings.get("eda"),
            "elapsed": stats.get("elapsed_seconds"),
        },
        "leakage_gate": {
            "passed": bool(gate.get("passed")),
            "exact_overlaps": gate.get("exact_overlaps"),
            "near_overlaps": gate.get("near_overlaps"),
            "threshold": gate.get("threshold"),
        },
        "ingest_retries": _fetch_retries(),
    }


def _fetch_retries():
    """What the last fetch cost in attempts, read from data/raw/MANIFEST.json.

    ISA row 4 asks for monitoring that covers logs, status, retries and alerts.
    The retries live in the fetch manifest and the rest live here, which meant
    demonstrating row 4 took three artefacts and an explanation. This pulls the
    retry count into the one report.

    A download that needed more than one attempt is not an error -- it succeeded
    -- but it is the signal that precedes a job that starts failing, so it is
    surfaced rather than left in a file nobody opens.
    """
    path = REPO_ROOT / "data" / "raw" / "MANIFEST.json"
    if not path.exists():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    files, retried = 0, []
    for name, ds in (manifest.get("datasets") or {}).items():
        for local, rec in (ds.get("files") or {}).items():
            files += 1
            n = rec.get("attempts")
            if isinstance(n, int) and n > 1:
                retried.append({"file": local, "attempts": n})
    return {"files": files, "retried": retried,
            "clean": not retried}


def _rel_delta(old, new):
    if old is None or new is None:
        return None
    if old == 0:
        return 0.0 if new == 0 else 1.0
    return abs(new - old) / float(old)


def compare(current, previous, threshold):
    alerts = []
    if previous is None:
        return {
            "compared_to": None,
            "within_threshold": True,
            "alerts": ["no previous monitor report; baseline written"],
        }

    prev_rows = previous.get("rows") or {}
    cur_rows = current.get("rows") or {}
    for key in ("ingested", "kept", "train", "dev", "test"):
        delta = _rel_delta(prev_rows.get(key), cur_rows.get(key))
        if delta is not None and delta > threshold:
            alerts.append(
                "{} drifted by {:.2%} ({} -> {})".format(
                    key, delta, prev_rows.get(key), cur_rows.get(key),
                )
            )

    prev_gate = (previous.get("leakage_gate") or {}).get("passed")
    cur_gate = (current.get("leakage_gate") or {}).get("passed")
    if prev_gate is True and cur_gate is False:
        alerts.append("leakage gate flipped from passed to FAILED")
    if cur_gate is False:
        alerts.append("leakage gate FAILED on this run")

    if previous.get("input_sha256") and current.get("input_sha256"):
        if previous["input_sha256"] != current["input_sha256"]:
            alerts.append(
                "input sha256 changed ({} -> {})".format(
                    previous["input_sha256"][:12], current["input_sha256"][:12],
                )
            )

    return {
        "compared_to": previous.get("generated_at"),
        "previous_pipeline_generated_at": previous.get("pipeline_generated_at"),
        "threshold": threshold,
        "within_threshold": not alerts,
        "alerts": alerts or ["no drift above threshold"],
    }


def main(argv=None):
    args = parse_args(argv)
    stats_path = Path(args.stats)
    if not stats_path.exists():
        print("missing statistics: {}".format(stats_path), file=sys.stderr)
        return 2

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    report = build_report(stats)

    prev = None
    prev_path = Path(args.previous)
    # When writing over the same path, read the existing file first as baseline.
    if prev_path.exists():
        try:
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
            # Ignore a report that is already about this exact pipeline run so a
            # second monitor pass in one demo does not alert against itself.
            if prev.get("pipeline_generated_at") == report.get("pipeline_generated_at") \
                    and prev.get("input_sha256") == report.get("input_sha256") \
                    and prev.get("rows") == report.get("rows"):
                prev = None
        except json.JSONDecodeError:
            prev = None

    report["drift"] = compare(report, prev, args.threshold)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    rows = report["rows"]
    timings = report["timings_seconds"]
    gate = report["leakage_gate"]
    print("pipeline monitor")
    print("  source     {}".format(report["source"]))
    print("  ingested   {:,}  kept {:,}  removed {:,}".format(
        rows["ingested"] or 0, rows["kept"] or 0, rows["removed"] or 0))
    print("  splits     train {:,}  dev {:,}  test {:,}".format(
        rows["train"] or 0, rows["dev"] or 0, rows["test"] or 0))
    print("  latency    ingest {:.2f}s  clean {:.2f}s  split {:.2f}s  eda {:.2f}s  total {:.2f}s".format(
        timings.get("ingest") or 0, timings.get("clean") or 0,
        timings.get("split") or 0, timings.get("eda") or 0,
        timings.get("elapsed") or 0))
    print("  gate       {} (exact={}, near={})".format(
        "passed" if gate["passed"] else "FAILED",
        gate.get("exact_overlaps"), gate.get("near_overlaps")))
    retries = report.get("ingest_retries")
    if retries is None:
        print("  retries    n/a (no fetch manifest; corpus not fetched by "
              "scripts/fetch_data.py)")
    elif retries["clean"]:
        print("  retries    none, {} file(s) fetched first time".format(retries["files"]))
    else:
        print("  retries    {} of {} file(s) needed more than one attempt".format(
            len(retries["retried"]), retries["files"]))
        for r in retries["retried"]:
            print("    - {} took {} attempts".format(r["file"], r["attempts"]))
    print("  drift      {}".format(
        "ok" if report["drift"]["within_threshold"] else "ALERT"))
    for alert in report["drift"]["alerts"]:
        print("    - {}".format(alert))
    print("  wrote      {}".format(out))

    if args.fail_on_drift and not report["drift"]["within_threshold"]:
        return 5
    if args.fail_on_drift and not gate["passed"]:
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())

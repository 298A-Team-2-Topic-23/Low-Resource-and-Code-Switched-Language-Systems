#!/usr/bin/env python3
"""
GPU-hours spent and projected, per arm, against the 298-72 cap.  [298-73, owner: Singh]

Reads every run record under runs/:

  runs/<model>/<seed>/run.json         the 298-73 contract (current run)
  runs/<model>/<seed>/run.*-<t>.json   archived earlier attempts; they spent budget too
  runs/*.json                          RunLogger records from before the contract

and rolls them up against the allocations decided under 298-72. This replaces
the hand-maintained running total in docs/COMPUTE_BUDGET.md: the number in the
document is whatever this prints, and a run that is not on disk did not happen.

Charging rules
--------------
  * a `train` run is charged to its arm's line
  * M1 has no training, so its `generate` runs are charged to M1's line
  * every other `generate` or `evaluate` run is charged to "inference"
  * `smoke` and pre-contract records are shown on their own lines and count
    toward the total, never toward an arm, because they are not results

Projection
----------
For an arm with at least one finished training run on a reportable seed, the
projection is the mean measured GPU-hours per seed times three seeds. Otherwise
the 298-72 allocation stands. This is the check docs/COMPUTE_BUDGET.md asks
for before M3 and Control A are scheduled.

Usage
-----
  python scripts/run_summary.py
  python scripts/run_summary.py --json reports/run_summary.json
  python scripts/run_summary.py --fail-over-cap      # exit 2 if the projection exceeds 165
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "common"))

from repro import (HARD_CAP_GPU_HOURS, INFERENCE_GPU_HOURS,  # noqa: E402
                   TRAINING_CAP_GPU_HOURS)
from run_contract import REPORTABLE_SEEDS, SCHEMA, validate  # noqa: E402

# Allocations decided under 298-72 (docs/COMPUTE_BUDGET.md). Change them there and here together.
PLAN = {
    "M1": 2, "M2": 25, "baseline": 15, "M3": 36, "control-a": 20, "control-b": 11, "M4": 25,
    "inference": 20,
}
SEEDS_PER_ARM = len(REPORTABLE_SEEDS)
# Control B's allocation is by definition M3 - M2, not a per-seed rate, so it is not projected
NOT_PROJECTED = {"control-b", "inference"}
LEGACY = "pre-contract"


def load_records(runs_root):
    """Yield (path, record, kind) for every record file under runs_root."""
    root = Path(runs_root)
    for path in sorted(root.glob("*.json")):
        yield path, _read(path), "legacy"
    for path in sorted(root.glob("*/*/run*.json")):
        yield path, _read(path), "contract"


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"_unreadable": str(e)}


def line_for(record, kind):
    if kind == "legacy":
        return LEGACY
    arm, phase = record.get("arm"), record.get("phase")
    if arm == "smoke":
        return "smoke"
    if phase == "train" or (arm == "M1" and phase == "generate"):
        return arm
    if phase in ("generate", "evaluate"):
        return "inference"
    return "data"


def summarise(runs_root):
    lines = defaultdict(lambda: {"spent": 0.0, "ok": 0, "failed": 0, "running": 0,
                                 "seed_hours": defaultdict(float)})
    problems = []
    for path, rec, kind in load_records(runs_root):
        rel = path.relative_to(Path(runs_root).parent) if path.is_relative_to(
            Path(runs_root).parent) else path
        if "_unreadable" in rec:
            problems.append(f"{rel}: unreadable ({rec['_unreadable']})")
            continue
        if kind == "contract":
            if rec.get("schema") != SCHEMA:
                problems.append(f"{rel}: not a {SCHEMA} record")
                continue
            for p in validate(rec):
                problems.append(f"{rel}: {p}")
            if rec.get("git", {}).get("dirty"):
                problems.append(f"{rel}: produced from a dirty tree; see dirty.patch beside it")
        line = line_for(rec, kind)
        hours = float(rec.get("gpu_hours") or 0.0)
        status = rec.get("status", "ok")
        e = lines[line]
        e["spent"] += hours
        e[status if status in ("ok", "failed", "running") else "failed"] += 1
        if (kind == "contract" and status == "ok" and rec.get("phase") == "train"
                and rec.get("seed") in REPORTABLE_SEEDS and path.name == "run.json"):
            e["seed_hours"][rec["seed"]] += hours

    rows, total_spent, train_spent, inf_spent, projected_total = [], 0.0, 0.0, 0.0, 0.0
    order = list(PLAN) + sorted(k for k in lines if k not in PLAN)
    for name in order:
        e = lines.get(name)
        spent = e["spent"] if e else 0.0
        plan = PLAN.get(name)
        measured = dict(e["seed_hours"]) if e else {}
        if plan is not None and measured and name not in NOT_PROJECTED:
            per_seed = sum(measured.values()) / len(measured)
            projected, basis = round(per_seed * SEEDS_PER_ARM, 2), f"measured, {len(measured)} seed(s)"
        elif plan is not None:
            projected, basis = float(max(plan, spent)), "298-72 allocation"
        else:
            projected, basis = spent, "spent; not an arm"
        rows.append({"line": name, "plan": plan, "spent": round(spent, 4),
                     "ok": e["ok"] if e else 0, "failed": e["failed"] if e else 0,
                     "running": e["running"] if e else 0,
                     "projected": round(projected, 2), "basis": basis})
        total_spent += spent
        projected_total += projected
        if name == "inference":
            inf_spent += spent
        elif name in PLAN:
            train_spent += spent

    return {
        "rows": rows,
        "spent": {"total": round(total_spent, 4), "training": round(train_spent, 4),
                  "inference": round(inf_spent, 4)},
        "cap": {"hard": HARD_CAP_GPU_HOURS, "training": TRAINING_CAP_GPU_HOURS,
                "inference": INFERENCE_GPU_HOURS, "planned": sum(PLAN.values())},
        "projected_total": round(projected_total, 2),
        "over_cap": projected_total > HARD_CAP_GPU_HOURS,
        "problems": problems,
    }


def render(s):
    out = [f"\n{'line':<14}{'plan':>7}{'spent':>10}{'ok':>5}{'fail':>6}{'run':>5}"
           f"{'projected':>11}  basis", "-" * 78]
    for r in s["rows"]:
        plan = "" if r["plan"] is None else str(r["plan"])
        out.append(f"{r['line']:<14}{plan:>7}{r['spent']:>10.3f}{r['ok']:>5}{r['failed']:>6}"
                   f"{r['running']:>5}{r['projected']:>11.2f}  {r['basis']}")
    out.append("-" * 78)
    c, sp = s["cap"], s["spent"]
    out.append(f"spent      {sp['total']:.3f} of {c['hard']} GPU-hours "
               f"(training {sp['training']:.3f} of {c['training']}, "
               f"inference {sp['inference']:.3f} of {c['inference']})")
    flag = "  OVER THE CAP" if s["over_cap"] else ""
    out.append(f"projected  {s['projected_total']:.2f} against a cap of {c['hard']} "
               f"(plan {c['planned']}){flag}")
    if s["problems"]:
        out.append(f"\n{len(s['problems'])} record problem(s):")
        out.extend(f"  {p}" for p in s["problems"])
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="GPU-hours against the 298-72 cap (298-73)")
    ap.add_argument("--runs", default=str(REPO_ROOT / "runs"))
    ap.add_argument("--json", metavar="PATH", help="also write the summary as JSON")
    ap.add_argument("--fail-over-cap", action="store_true",
                    help="exit 2 if the projected total exceeds the hard cap")
    a = ap.parse_args(argv)
    s = summarise(a.runs)
    print(render(s))
    if a.json:
        Path(a.json).write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
    if a.fail_over_cap and s["over_cap"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

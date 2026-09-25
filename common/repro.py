#!/usr/bin/env python3
"""
Reproducibility utilities. [Linear 298-26, owner: Prakhar]

Two things the abstract promises and Part A row 7 is graded on:
  1. every run is seeded, and the seed is recorded
  2. every run is logged, with its GPU-hours, so the compute budget is evidenced

Import this from every training and evaluation script. Do not reimplement
seeding per script -- the whole point is that one function governs all of them.

Usage
-----
    import sys; sys.path.insert(0, "common")      # or run from repo root
    from repro import set_seed, RunLogger

    set_seed(42)
    with RunLogger("model2-qlora", seed=42, config={"rank": 32, "lr": 2e-4}) as run:
        ...train...
        run.log_metric("chrf++", 41.7)

Then:
    python common/repro.py --summary runs/     # every run + total GPU-hours
    python common/repro.py --selftest          # sanity check

Notes
-----
* GPU-hours are wall-clock hours of the run on ONE GPU. Our jobs are
  single-GPU by design, so this is exact. If a run ever uses N GPUs,
  pass n_gpus=N to RunLogger and it is multiplied in.
* Logs always land in <repo root>/runs/ regardless of the directory the
  script is launched from, so nobody's runs go missing from the summary.
"""
import argparse
import json
import os
import platform
import random
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS_DIR = REPO_ROOT / "runs"
BUDGET_GPU_HOURS = (80, 145)   # from the abstract


# ------------------------------------------------------------------- seeding
def set_seed(seed: int) -> int:
    """Seed every source of randomness we might touch. Returns the seed.

    Call this at the very top of main(), before any model, tokenizer,
    dataloader or sampler is created.
    """
    # PYTHONHASHSEED only affects *child* processes (e.g. DataLoader workers);
    # the current interpreter's hash seed is fixed at startup. Our code never
    # iterates over sets/dicts of strings to make random choices, so this is
    # sufficient -- make_splits.py sorts keys before shuffling for this reason.
    os.environ["PYTHONHASHSEED"] = str(seed)
    # Needed by cuBLAS for deterministic matmuls on CUDA >= 10.2.
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        # Determinism costs some speed. Worth it: our success criterion depends
        # on non-overlapping error bars across three seeds, so run-to-run noise
        # from cuDNN autotuning would muddy exactly the thing we are measuring.
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass
    try:
        # transformers keeps its own seeding helper (also covers TF/JAX if present)
        from transformers import set_seed as hf_set_seed
        hf_set_seed(seed)
    except ImportError:
        pass
    return seed


# --------------------------------------------------------------- environment
def _run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                             cwd=REPO_ROOT)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def git_commit():
    sha = _run(["git", "rev-parse", "HEAD"])
    if not sha:
        return None
    dirty = _run(["git", "status", "--porcelain"])
    return sha + ("-dirty" if dirty else "")


def _version(pkg):
    try:
        from importlib.metadata import version
        return version(pkg)
    except Exception:
        return None


def gpu_info():
    try:
        import torch
        if torch.cuda.is_available():
            return {"name": torch.cuda.get_device_name(0),
                    "count": torch.cuda.device_count(),
                    "cuda": torch.version.cuda}
    except ImportError:
        pass
    return None


def environment():
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "host": socket.gethostname(),
        "git_commit": git_commit(),
        "gpu": gpu_info(),
        "packages": {p: _version(p) for p in
                     ("torch", "transformers", "accelerate", "peft",
                      "bitsandbytes", "sacrebleu", "numpy")},
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    }


# ------------------------------------------------------------------- logging
class RunLogger:
    """Context manager. Writes one JSON file per run into runs/.

    A failed run is still written (status="failed") -- failed runs consume
    budget too, and the report has to account for them.
    """

    def __init__(self, name, seed=None, config=None, outdir=None, n_gpus=1):
        self.name = name
        self.seed = seed
        self.config = config or {}
        self.outdir = Path(outdir) if outdir else DEFAULT_RUNS_DIR
        self.n_gpus = n_gpus
        self.metrics = {}
        self.notes = []

    def __enter__(self):
        self.t0 = time.time()
        self.started = datetime.now(timezone.utc)
        print(f"[run] {self.name} started, seed={self.seed}")
        return self

    def log_metric(self, key, value):
        self.metrics[key] = value

    def note(self, text):
        self.notes.append(text)

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.time() - self.t0
        self.outdir.mkdir(parents=True, exist_ok=True)
        stamp = self.started.strftime("%Y%m%dT%H%M%SZ")
        gpu_hours = round(elapsed * self.n_gpus / 3600, 3)
        rec = {
            "name": self.name,
            "seed": self.seed,
            "started_at": self.started.isoformat(timespec="seconds"),
            "elapsed_seconds": round(elapsed, 1),
            "n_gpus": self.n_gpus,
            "gpu_hours": gpu_hours,
            "status": "failed" if exc_type else "ok",
            "error": repr(exc) if exc else None,
            "config": self.config,
            "metrics": self.metrics,
            "notes": self.notes,
            "environment": environment(),
        }
        path = self.outdir / f"{stamp}_{self.name}_seed{self.seed}.json"
        path.write_text(json.dumps(rec, indent=2, default=str) + "\n",
                        encoding="utf-8")
        print(f"[run] {self.name} {rec['status']} in {gpu_hours:.3f} GPU-hours -> {path}")
        return False  # never swallow the exception


# ------------------------------------------------------------------- summary
def summary(outdir):
    files = sorted(Path(outdir).glob("*.json"))
    if not files:
        sys.exit(f"no runs recorded in {outdir}")
    rows = []
    for f in files:
        try:
            rows.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  skipping unreadable {f.name}: {e}", file=sys.stderr)

    print(f"\n{'run':<34}{'seed':>6}{'status':>9}{'GPU-h':>9}")
    print("-" * 58)
    total, failed = 0.0, 0.0
    for r in rows:
        gh = float(r.get("gpu_hours", 0))
        total += gh
        if r.get("status") != "ok":
            failed += gh
        print(f"{str(r.get('name'))[:33]:<34}{str(r.get('seed')):>6}"
              f"{str(r.get('status')):>9}{gh:>9.3f}")
    print("-" * 58)
    print(f"{'TOTAL (' + str(len(rows)) + ' runs)':<49}{total:>9.3f}")
    if failed:
        print(f"{'  of which failed runs':<49}{failed:>9.3f}")
    lo, hi = BUDGET_GPU_HOURS
    print(f"\nBudget in the abstract: {lo}-{hi} GPU-hours. Used so far: {total:.2f} "
          f"({100 * total / hi:.1f}% of the upper bound).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Reproducibility utilities (298-26)")
    ap.add_argument("--summary", metavar="RUNS_DIR", nargs="?",
                    const=str(DEFAULT_RUNS_DIR),
                    help="print the run table and total GPU-hours")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summary(a.summary)
    elif a.selftest:
        set_seed(42)
        x = [random.random() for _ in range(3)]
        set_seed(42)
        assert x == [random.random() for _ in range(3)], "seeding is not deterministic"
        with RunLogger("selftest", seed=42, config={"demo": True}) as run:
            run.log_metric("chrf++", 41.7)
            run.note("selftest only")
        print("selftest OK: seeding deterministic, run log written")
    else:
        ap.print_help()

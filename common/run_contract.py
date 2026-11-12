#!/usr/bin/env python3
"""
The experiment-run contract: every run writes runs/<model>/<seed>/run.json.  [298-73, owner: Singh]

`RunLogger` (298-26) proves a run happened and what it cost. It does not say
which split, which tokenizer or whether the code that produced a number was the
code at the recorded commit. When twelve runs land, those are the questions
the results section cannot answer from memory. This contract makes each one a
required field, written at the moment of the run, so 298-83 can generate the
results table from files rather than from anyone typing.

What a record holds
-------------------
  schema               "lrcs.run/1"
  model, arm, phase    model id, ablation arm (M1..M4, control-a, control-b,
                       baseline, smoke) and phase (train, generate, evaluate, data)
  seed                 13, 42 or 1337 for reportable runs
  git                  commit SHA, dirty flag, SHA-256 of `git diff HEAD`
  split_manifest       path and SHA-256 of the frozen split manifest
  tokenizer            id and vocabulary size
  hyperparameters      whatever the trainer was given
  started_at, finished_at, wall_clock_seconds
  gpu, n_gpus, gpu_hours      gpu_hours is 0.0 when no CUDA GPU was used
  peak_gpu_memory_gb, peak_host_rss_gb
  metrics, status, error, notes, environment

The dirty-tree guard
--------------------
If tracked files differ from HEAD when the run starts, the record says
`"dirty": true`, stores the SHA-256 of `git diff HEAD`, and writes the diff
itself to `dirty.patch` beside run.json. A number can then never be silently
attributed to a commit that does not contain the code that produced it: the
commit plus the patch is the code. Untracked files are ignored, for the same
reason `repro.git_commit` ignores them: runs write outputs into the tree.

Re-runs
-------
A finished record is never overwritten. If runs/<model>/<seed>/run.json exists
and is `ok`, the new run refuses to start unless `overwrite=True`; if it is
`failed`, it is archived as run.failed-<stamp>.json first, because a failed
run still spent budget and the roll-up must still count it.

Usage
-----
    from run_contract import ExperimentRun

    with ExperimentRun(model="Qwen/Qwen2.5-7B-Instruct", arm="M2", phase="train",
                       seed=13,
                       split_manifest="data/processed/manifests/hinge_split_manifest.json",
                       tokenizer_id="Qwen/Qwen2.5-7B-Instruct", vocab_size=152064,
                       hyperparameters={"rank": 32, "alpha": 64, "lr": 2e-4}) as run:
        ...train...
        run.log_metric("train_loss", 1.21)

    python common/run_contract.py --smoke          # CPU smoke run, writes a real record
    python scripts/run_summary.py                  # hours spent against the cap
"""

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from repro import REPO_ROOT, environment, set_seed  # noqa: E402

SCHEMA = "lrcs.run/1"
ARMS = ("M1", "M2", "M3", "M4", "control-a", "control-b", "baseline", "smoke")
PHASES = ("train", "generate", "evaluate", "data")
REPORTABLE_SEEDS = (13, 42, 1337)
REQUIRED = ("schema", "model", "arm", "phase", "seed", "git", "split_manifest", "tokenizer",
            "hyperparameters", "started_at", "finished_at", "wall_clock_seconds", "n_gpus",
            "gpu_hours", "status", "metrics")


# ------------------------------------------------------------------- helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args, cwd):
    try:
        out = subprocess.run(["git", *args], capture_output=True, cwd=cwd, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def git_state(repo_root=REPO_ROOT):
    """Commit, dirty flag and the diff that makes the tree differ from it.

    Returns {"available": False, ...} when git or the repository is missing,
    which is a fact to record, not a reason to refuse to run.
    """
    sha = _git(["rev-parse", "HEAD"], repo_root)
    if sha is None:
        return {"available": False, "commit": None, "dirty": None, "diff_sha256": None}, None
    status = _git(["status", "--porcelain", "--untracked-files=no"], repo_root) or b""
    dirty = bool(status.strip())
    diff = _git(["diff", "HEAD", "--binary"], repo_root) if dirty else None
    return {
        "available": True,
        "commit": sha.decode().strip(),
        "dirty": dirty,
        "diff_sha256": hashlib.sha256(diff).hexdigest() if diff is not None else None,
    }, diff


def _cuda():
    """(device name, count) of the CUDA GPU in use, or (None, 0). Never raises."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0), torch.cuda.device_count()
    except Exception:
        pass
    return None, 0


def _peak_gpu_memory_gb():
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.max_memory_allocated() / 1e9, 3)
    except Exception:
        pass
    return None


def _peak_host_rss_gb():
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:   # Windows has no `resource`
        return None
    # ru_maxrss is kilobytes on Linux and bytes on macOS (the team's laptops)
    scale = 1 if sys.platform == "darwin" else 1024
    return round(rss * scale / 1e9, 3)


def run_dir(model, seed, runs_root=None):
    """runs/<model>/<seed>/ with the model id made path-safe (Qwen/Qwen2.5 -> Qwen__Qwen2.5)."""
    root = Path(runs_root) if runs_root else REPO_ROOT / "runs"
    return root / model.replace("/", "__") / str(seed)


# ---------------------------------------------------------------- validation
def validate(record):
    """Return a list of problems with a run record; empty means it meets the contract."""
    problems = [f"missing field: {k}" for k in REQUIRED if k not in record]
    if problems:
        return problems
    if record["schema"] != SCHEMA:
        problems.append(f"schema {record['schema']!r} is not {SCHEMA!r}")
    if record["arm"] not in ARMS:
        problems.append(f"arm {record['arm']!r} not in {ARMS}")
    if record["phase"] not in PHASES:
        problems.append(f"phase {record['phase']!r} not in {PHASES}")
    if record["status"] not in ("ok", "failed", "running"):
        problems.append(f"status {record['status']!r}")
    g = record["git"]
    if g.get("available") and not g.get("commit"):
        problems.append("git available but no commit recorded")
    if g.get("dirty") and not g.get("diff_sha256"):
        problems.append("dirty tree without a diff hash")
    sm = record["split_manifest"]
    if record["arm"] != "smoke" and not (sm and sm.get("sha256")):
        problems.append("reportable arm without a split-manifest hash")
    if record["arm"] != "smoke" and record["seed"] not in REPORTABLE_SEEDS:
        problems.append(f"seed {record['seed']} is not one of {REPORTABLE_SEEDS}")
    if not isinstance(record["gpu_hours"], (int, float)) or record["gpu_hours"] < 0:
        problems.append("gpu_hours must be a non-negative number")
    if record["n_gpus"] == 0 and record["gpu_hours"] != 0:
        problems.append("gpu_hours is non-zero but no GPU was used")
    return problems


# --------------------------------------------------------------- the contract
class ExperimentRun:
    """Context manager that writes runs/<model>/<seed>/run.json for one run.

    The record is written when the run starts (status "running") and rewritten
    when it ends, so a run killed by a dropped Colab session still leaves a
    record of what it was and when it started.
    """

    def __init__(self, model, arm, seed, phase="train", split_manifest=None,
                 tokenizer_id=None, vocab_size=None, hyperparameters=None,
                 runs_root=None, repo_root=None, overwrite=False, n_gpus=None,
                 gpu_probe=_cuda):
        if arm not in ARMS:
            raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")
        if phase not in PHASES:
            raise ValueError(f"phase must be one of {PHASES}, got {phase!r}")
        self.model, self.arm, self.seed, self.phase = model, arm, seed, phase
        self.repo_root = Path(repo_root) if repo_root else REPO_ROOT
        self.split_manifest = split_manifest
        self.tokenizer = {"id": tokenizer_id, "vocab_size": vocab_size}
        self.hyperparameters = dict(hyperparameters or {})
        self.dir = run_dir(model, seed, runs_root)
        self.path = self.dir / "run.json"
        self.overwrite = overwrite
        self._n_gpus = n_gpus
        self._gpu_probe = gpu_probe
        self.metrics, self.notes = {}, []

    # -- user API
    def log_metric(self, key, value):
        self.metrics[key] = value

    def note(self, text):
        self.notes.append(text)

    # -- internals
    def _manifest(self):
        if self.split_manifest is None:
            return None
        p = Path(self.split_manifest)
        if not p.is_absolute():
            p = self.repo_root / p
        if not p.exists():
            raise FileNotFoundError(f"split manifest not found: {p}")
        try:
            shown = p.relative_to(self.repo_root).as_posix()
        except ValueError:
            shown = str(p)
        return {"path": shown, "sha256": sha256_file(p)}

    def _make_room(self):
        if not self.path.exists():
            return
        try:
            old = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            old = {"status": "unreadable"}
        if old.get("status") == "ok" and not self.overwrite:
            raise FileExistsError(
                f"{self.path} already holds a finished run; pass overwrite=True to replace it")
        stamp = str(old.get("started_at", "unknown")).replace(":", "").replace("-", "")
        self.path.rename(self.dir / f"run.{old.get('status', 'old')}-{stamp}.json")

    def _write(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.record, indent=2, default=str) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def __enter__(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self._make_room()
        git, diff = git_state(self.repo_root)
        if diff is not None:
            (self.dir / "dirty.patch").write_bytes(diff)
        gpu_name, gpu_count = self._gpu_probe()
        n_gpus = self._n_gpus if self._n_gpus is not None else (1 if gpu_name else 0)
        self.t0 = time.time()
        self.record = {
            "schema": SCHEMA,
            "model": self.model, "arm": self.arm, "phase": self.phase, "seed": self.seed,
            "git": git,
            "split_manifest": self._manifest(),
            "tokenizer": self.tokenizer,
            "hyperparameters": self.hyperparameters,
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "finished_at": None,
            "wall_clock_seconds": None,
            "gpu": gpu_name, "n_gpus": n_gpus, "gpu_hours": 0.0,
            "peak_gpu_memory_gb": None, "peak_host_rss_gb": None,
            "metrics": self.metrics, "status": "running", "error": None, "notes": self.notes,
            "environment": environment(),
        }
        self._write()
        tag = " DIRTY TREE: diff saved to dirty.patch" if git.get("dirty") else ""
        print(f"[run] {self.arm} {self.model} seed={self.seed} -> {self.path}{tag}")
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.time() - self.t0
        r = self.record
        r["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        r["wall_clock_seconds"] = round(elapsed, 1)
        # GPU-hours are wall-clock time on the GPUs actually used: 0.0 on CPU, never a crash
        r["gpu_hours"] = round(elapsed * r["n_gpus"] / 3600, 4) if r["n_gpus"] else 0.0
        r["peak_gpu_memory_gb"] = _peak_gpu_memory_gb() if r["n_gpus"] else None
        r["peak_host_rss_gb"] = _peak_host_rss_gb()
        r["status"] = "failed" if exc_type else "ok"
        r["error"] = repr(exc) if exc else None
        self._write()
        problems = validate(r)
        for p in problems:
            print(f"[run] contract warning: {p}", file=sys.stderr)
        print(f"[run] {r['status']} in {r['gpu_hours']:.4f} GPU-hours -> {self.path}")
        return False  # never swallow the exception


# ------------------------------------------------------------------- CLI
def smoke(runs_root=None, seed=42, repo_root=None):
    """A CPU smoke run: proves a record is written and readable, costs nothing."""
    manifest = REPO_ROOT / "data" / "processed" / "manifests" / "synthetic_split_manifest.json"
    set_seed(seed)
    with ExperimentRun(model="smoke/cpu", arm="smoke", phase="data", seed=seed,
                       split_manifest=manifest, tokenizer_id=None, vocab_size=None,
                       hyperparameters={"n": 200_000}, runs_root=runs_root,
                       repo_root=repo_root, overwrite=True) as run:
        total = sum(random.random() for _ in range(200_000))
        run.log_metric("mean", round(total / 200_000, 6))
        run.note(f"CPU smoke on {platform.machine()}; not a result")
    return run.path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Experiment-run contract (298-73)")
    ap.add_argument("--smoke", action="store_true", help="write a CPU smoke record")
    ap.add_argument("--runs-root", help="default: <repo>/runs")
    ap.add_argument("--validate", metavar="RUN_JSON", nargs="+",
                    help="check records against the contract")
    a = ap.parse_args()
    if a.smoke:
        print(smoke(a.runs_root))
    elif a.validate:
        bad = 0
        for f in a.validate:
            probs = validate(json.loads(Path(f).read_text(encoding="utf-8")))
            bad += bool(probs)
            print(f"{f}: {'ok' if not probs else '; '.join(probs)}")
        sys.exit(1 if bad else 0)
    else:
        ap.print_help()

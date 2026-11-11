"""Tests for common/run_contract.py and scripts/run_summary.py  [298-73]

The acceptance criteria: a CPU smoke run produces a valid run.json and the
roll-up reads it; the dirty-tree and no-GPU cases are covered (gpu_hours 0.0,
not a crash).
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import run_contract as rc
from run_contract import ExperimentRun, validate

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "data/processed/manifests/synthetic_split_manifest.json"

_spec = importlib.util.spec_from_file_location("run_summary", REPO_ROOT / "scripts" / "run_summary.py")
run_summary = importlib.util.module_from_spec(_spec)
sys.modules["run_summary"] = run_summary
_spec.loader.exec_module(run_summary)

NO_GPU = lambda: (None, 0)          # noqa: E731
FAKE_GPU = lambda: ("Fake A100", 1)  # noqa: E731
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


# Hermetic git: ignore the machine's global and system config, so commit signing,
# hooks or a default branch name on someone's laptop cannot break the fixture.
GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", *args], cwd=repo,
                   check=True, capture_output=True, env=GIT_ENV)


@pytest.fixture
def repo(tmp_path):
    """A throwaway git repository with one committed file and a split manifest."""
    r = tmp_path / "repo"
    (r / "data").mkdir(parents=True)
    (r / "train.py").write_text("print('v1')\n")
    (r / "data" / "manifest.json").write_text('{"split": "frozen"}\n')
    if shutil.which("git"):
        _git(r, "init", "-q")
        _git(r, "add", ".")
        _git(r, "commit", "-q", "-m", "init")
    return r


def _run(repo, runs, **kw):
    args = dict(model="Qwen/Qwen2.5-7B-Instruct", arm="M2", seed=13,
                split_manifest="data/manifest.json", tokenizer_id="qwen", vocab_size=152064,
                runs_root=runs, repo_root=repo, gpu_probe=NO_GPU)
    args.update(kw)
    return ExperimentRun(**args)


# ------------------------------------------------------------ the record itself
def test_no_gpu_records_zero_gpu_hours_not_a_crash(repo, tmp_path):
    with _run(repo, tmp_path / "runs") as run:
        run.log_metric("train_loss", 1.2)
    rec = json.loads(run.path.read_text())
    assert rec["gpu"] is None and rec["n_gpus"] == 0
    assert rec["gpu_hours"] == 0.0
    assert rec["peak_gpu_memory_gb"] is None
    assert rec["status"] == "ok" and rec["metrics"] == {"train_loss": 1.2}
    assert validate(rec) == []


def test_path_is_runs_model_seed_run_json(repo, tmp_path):
    with _run(repo, tmp_path / "runs", seed=42) as run:
        pass
    assert run.path == tmp_path / "runs" / "Qwen__Qwen2.5-7B-Instruct" / "42" / "run.json"


def test_gpu_hours_are_wall_clock_on_the_gpu(repo, tmp_path, monkeypatch):
    clock = iter([1000.0, 1000.0 + 1800.0])
    monkeypatch.setattr(rc.time, "time", lambda: next(clock))
    with _run(repo, tmp_path / "runs", gpu_probe=FAKE_GPU) as run:
        pass
    rec = json.loads(run.path.read_text())
    assert rec["gpu"] == "Fake A100" and rec["n_gpus"] == 1
    assert rec["gpu_hours"] == 0.5


def test_split_manifest_is_hashed(repo, tmp_path):
    with _run(repo, tmp_path / "runs") as run:
        pass
    rec = json.loads(run.path.read_text())
    expected = hashlib.sha256((repo / "data" / "manifest.json").read_bytes()).hexdigest()
    assert rec["split_manifest"] == {"path": "data/manifest.json", "sha256": expected}


def test_missing_manifest_fails_before_the_run(repo, tmp_path):
    with pytest.raises(FileNotFoundError):
        with _run(repo, tmp_path / "runs", split_manifest="data/nope.json"):
            pytest.fail("the run body must not execute")


def test_record_exists_while_running(repo, tmp_path):
    with _run(repo, tmp_path / "runs") as run:
        live = json.loads(run.path.read_text())
        assert live["status"] == "running" and live["finished_at"] is None


def test_unknown_arm_or_phase_rejected(repo, tmp_path):
    with pytest.raises(ValueError):
        _run(repo, tmp_path / "runs", arm="M5")
    with pytest.raises(ValueError):
        _run(repo, tmp_path / "runs", phase="finetune")


# -------------------------------------------------------------- dirty-tree guard
@needs_git
def test_clean_tree_records_commit_and_no_patch(repo, tmp_path):
    with _run(repo, tmp_path / "runs") as run:
        pass
    rec = json.loads(run.path.read_text())
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                          text=True).stdout.strip()
    assert rec["git"] == {"available": True, "commit": head, "dirty": False, "diff_sha256": None}
    assert not (run.dir / "dirty.patch").exists()


@needs_git
def test_dirty_tree_records_diff_hash_and_saves_patch(repo, tmp_path):
    (repo / "train.py").write_text("print('v2, uncommitted')\n")
    with _run(repo, tmp_path / "runs") as run:
        pass
    rec = json.loads(run.path.read_text())
    patch = (run.dir / "dirty.patch").read_bytes()
    assert rec["git"]["dirty"] is True
    assert rec["git"]["diff_sha256"] == hashlib.sha256(patch).hexdigest()
    assert b"v2, uncommitted" in patch
    assert validate(rec) == []
    # the commit plus the patch reproduces the code that ran
    _git(repo, "stash", "-q")
    assert (repo / "train.py").read_text() == "print('v1')\n"
    subprocess.run(["git", "apply", str(run.dir / "dirty.patch")], cwd=repo, check=True,
                   env=GIT_ENV)
    assert "v2, uncommitted" in (repo / "train.py").read_text()


@needs_git
def test_untracked_outputs_do_not_mark_the_tree_dirty(repo, tmp_path):
    (repo / "out.txt").write_text("a run's own output\n")
    with _run(repo, tmp_path / "runs") as run:
        pass
    assert json.loads(run.path.read_text())["git"]["dirty"] is False


def test_no_git_repository_is_recorded_not_fatal(tmp_path):
    bare = tmp_path / "not_a_repo"
    (bare / "data").mkdir(parents=True)
    (bare / "data" / "manifest.json").write_text("{}\n")
    with _run(bare, tmp_path / "runs") as run:
        pass
    rec = json.loads(run.path.read_text())
    assert rec["git"]["available"] is False and rec["git"]["commit"] is None
    assert validate(rec) == []


# ------------------------------------------------------------------- re-runs
def test_failed_run_is_written_then_archived_by_the_retry(repo, tmp_path):
    runs = tmp_path / "runs"
    with pytest.raises(RuntimeError):
        with _run(repo, runs):
            raise RuntimeError("CUDA out of memory")
    first = json.loads((runs / "Qwen__Qwen2.5-7B-Instruct" / "13" / "run.json").read_text())
    assert first["status"] == "failed" and "out of memory" in first["error"]

    with _run(repo, runs) as run:
        pass
    archived = list(run.dir.glob("run.failed-*.json"))
    assert len(archived) == 1
    assert json.loads(archived[0].read_text())["status"] == "failed"
    assert json.loads(run.path.read_text())["status"] == "ok"


def test_finished_run_is_never_silently_overwritten(repo, tmp_path):
    runs = tmp_path / "runs"
    with _run(repo, runs):
        pass
    with pytest.raises(FileExistsError):
        with _run(repo, runs):
            pytest.fail("must not start")
    with _run(repo, runs, overwrite=True) as run:
        pass
    assert len(list(run.dir.glob("run.ok-*.json"))) == 1   # the replaced run is kept


# ---------------------------------------------------------------- validation
def test_validate_catches_what_the_results_table_needs():
    good = {k: None for k in rc.REQUIRED}
    good.update(schema=rc.SCHEMA, model="m", arm="M3", phase="train", seed=7,
                git={"available": True, "commit": "abc", "dirty": True, "diff_sha256": None},
                split_manifest=None, tokenizer={}, hyperparameters={}, n_gpus=0,
                gpu_hours=0.3, status="ok", metrics={})
    problems = " | ".join(validate(good))
    assert "dirty tree without a diff hash" in problems
    assert "without a split-manifest hash" in problems
    assert "seed 7" in problems
    assert "no GPU was used" in problems
    assert validate({"schema": rc.SCHEMA}) and "missing field" in validate({})[0]


def test_peak_rss_scale_is_platform_aware(monkeypatch):
    class Usage:
        ru_maxrss = 2_000_000
    monkeypatch.setattr("resource.getrusage", lambda _: Usage())
    monkeypatch.setattr(rc.sys, "platform", "linux")      # kilobytes
    assert rc._peak_host_rss_gb() == 2.048
    monkeypatch.setattr(rc.sys, "platform", "darwin")     # bytes
    assert rc._peak_host_rss_gb() == 0.002


# ------------------------------------------------------------------ roll-up
def _contract(runs, model, seed, arm, phase, hours, status="ok", name="run.json", dirty=False):
    d = runs / model / str(seed)
    d.mkdir(parents=True, exist_ok=True)
    rec = {"schema": rc.SCHEMA, "model": model, "arm": arm, "phase": phase, "seed": seed,
           "git": {"available": True, "commit": "abc", "dirty": dirty,
                   "diff_sha256": "f" * 64 if dirty else None},
           "split_manifest": {"path": "m", "sha256": "0" * 64}, "tokenizer": {},
           "hyperparameters": {}, "started_at": "t", "finished_at": "t",
           "wall_clock_seconds": hours * 3600, "n_gpus": 1, "gpu_hours": hours,
           "status": status, "metrics": {}}
    (d / name).write_text(json.dumps(rec))


def _row(summary, line):
    return next(r for r in summary["rows"] if r["line"] == line)


def test_cpu_smoke_record_is_read_by_the_rollup(tmp_path):
    """Acceptance: a CPU smoke run produces a valid run.json and the roll-up reads it."""
    runs = tmp_path / "runs"
    outside = tmp_path / "not_a_repo"      # independent of whether this checkout is dirty
    outside.mkdir()
    path = rc.smoke(runs_root=runs, repo_root=outside)
    rec = json.loads(Path(path).read_text())
    assert validate(rec) == [] and rec["split_manifest"]["sha256"]
    s = run_summary.summarise(runs)
    assert _row(s, "smoke")["ok"] == 1 and _row(s, "smoke")["spent"] == 0.0
    assert s["problems"] == []


def test_empty_runs_project_the_298_72_plan(tmp_path):
    (tmp_path / "runs").mkdir()
    s = run_summary.summarise(tmp_path / "runs")
    assert s["projected_total"] == 154 and s["cap"]["hard"] == 165 and not s["over_cap"]


def test_legacy_runlogger_records_still_count(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "20261022T213339Z_model2-qlora_seed13.json").write_text(
        json.dumps({"name": "model2-qlora", "seed": 13, "gpu_hours": 0.085, "status": "ok"}))
    s = run_summary.summarise(runs)
    assert _row(s, "pre-contract")["spent"] == 0.085
    assert s["spent"]["total"] == 0.085 and s["spent"]["training"] == 0.0


def test_charging_rules(tmp_path):
    runs = tmp_path / "runs"
    _contract(runs, "qwen", 13, "M1", "generate", 0.4)
    _contract(runs, "qwen-m2", 13, "M2", "train", 5.0)
    _contract(runs, "qwen-m2-gen", 13, "M2", "generate", 0.7)
    s = run_summary.summarise(runs)
    assert _row(s, "M1")["spent"] == 0.4            # M1's generation is its arm
    assert _row(s, "M2")["spent"] == 5.0
    assert _row(s, "inference")["spent"] == 0.7     # other generation is inference
    assert s["spent"]["training"] == 5.4 and s["spent"]["inference"] == 0.7


def test_projection_from_measured_seeds_flags_overrun(tmp_path):
    runs = tmp_path / "runs"
    _contract(runs, "qwen-m3", 13, "M3", "train", 20.0)
    _contract(runs, "qwen-m3", 42, "M3", "train", 22.0)
    s = run_summary.summarise(runs)
    assert _row(s, "M3")["projected"] == 63.0       # (20 + 22) / 2 * 3 seeds
    assert _row(s, "M3")["basis"].startswith("measured")
    assert s["projected_total"] == 154 - 36 + 63 and s["over_cap"]
    assert run_summary.main(["--runs", str(runs), "--fail-over-cap"]) == 2


def test_archived_failures_spend_budget_but_do_not_project(tmp_path):
    runs = tmp_path / "runs"
    _contract(runs, "qwen-m2", 13, "M2", "train", 3.0, status="failed",
              name="run.failed-20261120T000000Z.json")
    _contract(runs, "qwen-m2", 13, "M2", "train", 6.0)
    s = run_summary.summarise(runs)
    assert _row(s, "M2")["spent"] == 9.0 and _row(s, "M2")["failed"] == 1
    assert _row(s, "M2")["projected"] == 18.0       # only the finished run sets the rate


def test_dirty_and_invalid_records_are_reported(tmp_path):
    runs = tmp_path / "runs"
    _contract(runs, "qwen-m2", 13, "M2", "train", 1.0, dirty=True)
    (runs / "x" / "1").mkdir(parents=True)
    (runs / "x" / "1" / "run.json").write_text("{not json")
    problems = " | ".join(run_summary.summarise(runs)["problems"])
    assert "dirty tree" in problems and "unreadable" in problems


def test_plan_matches_the_decision_record():
    """PLAN in run_summary.py and the table in docs/COMPUTE_BUDGET.md must agree."""
    doc = (REPO_ROOT / "docs" / "COMPUTE_BUDGET.md").read_text(encoding="utf-8")
    assert sum(run_summary.PLAN.values()) == 154
    assert "| **Total** | **177** | **154** |" in doc
    from repro import HARD_CAP_GPU_HOURS, PLANNED_GPU_HOURS
    assert PLANNED_GPU_HOURS == sum(run_summary.PLAN.values()) and HARD_CAP_GPU_HOURS == 165

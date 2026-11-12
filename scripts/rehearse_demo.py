#!/usr/bin/env python3
"""
Rehearse the end-of-term demo on a genuinely fresh clone, timed and logged.  [298-85, owner: Singh]

298-40 rehearsed the Team Meeting 1 demo twice on fresh clones and that is why
it worked. This does the same for the end-of-term demo, with one difference
named in the issue: the plan that is rehearsed first is the one that needs no
GPU, no corpus and no network, because that is the demo the team gives if the
allocation never arrives (README "The honest fallback", 298-83 outcome 4).

What "fresh" means here
-----------------------
  * `git clone` into an empty directory at a named commit; nothing carried over
    from a working tree, so an untracked file on one machine cannot rescue a step
  * the demo steps run with networking OFF (`unshare -rn` on Linux), after the
    dependencies are installed, so nothing in the demo path can download
  * after the last step, `git status` in the clone must show no change to a
    tracked file: a demo that rewrites committed evidence is a demo that drifts

The steps (the no-GPU, no-corpus demo)
--------------------------------------
  tests            pytest, the gate on every claim below
  repro            seeding and run-logging self-test
  fertility        tokenizer measurement self-test (the measured tokenizer problem)
  pipeline         make demo-298-70: four stages -> SQLite warehouse -> queries -> monitor
  samples          stage samples from synthetic data, labelled as such
  codemix          the code-mixing generator on its committed fixture
  harness          the evaluation harness on its committed demo hypotheses
  budget           GPU-hours spent and projected against the cap
  figures          section 4.2's diagrams regenerate

Model outputs are not in this list yet: no model has run on real data. When
one has, its step reads committed pre-generated outputs together with the
run.json that produced them, never a live GPU.

Usage
-----
  python scripts/rehearse_demo.py --label clone-1
  python scripts/rehearse_demo.py --label clone-2 --ref <commit> \
      --source https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git

Each rehearsal writes <out>/<label>/<step>.log and <out>/<label>.json.
A rehearsal that finds nothing was probably not done on a clean clone. The
summary says what broke; that list is the deliverable.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STEPS = [
    ("tests", "{py} -m pytest tests/ -q -p no:cacheprovider"),
    ("repro", "{py} common/repro.py --selftest"),
    ("fertility", "{py} analysis/tokenizer_fertility.py --selftest"),
    ("pipeline", "make demo-298-70 PYTHON={py}"),
    ("samples", "{py} scripts/emit_stage_samples.py --synthetic --n-synthetic 1200 --seed 42"),
    ("codemix", "{py} scripts/generate_codemix.py"),
    ("harness", "{py} evaluation/run_eval.py --hyp evaluation/demo/hyp.seed1.txt "
                "evaluation/demo/hyp.seed2.txt --ref evaluation/demo/ref.hinglish.txt "
                "--system rehearsal"),
    ("budget", "{py} scripts/run_summary.py"),
    ("figures", "{py} scripts/model_support_figures.py --check --out-dir {tmp}/figures"),
]


def offline_prefix():
    """Command prefix that removes network access, or None if this OS cannot."""
    if platform.system() == "Linux" and shutil.which("unshare"):
        probe = subprocess.run(["unshare", "-rn", "true"], capture_output=True)
        if probe.returncode == 0:
            return ["unshare", "-rn"]
    return None


def sh(cmd, cwd, log, prefix=None, env=None):
    t0 = time.time()
    full = (prefix or []) + ["bash", "-c", cmd]
    with open(log, "w", encoding="utf-8") as f:
        f.write(f"$ {cmd}\n")
        f.flush()
        rc = subprocess.run(full, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
    return rc, round(time.time() - t0, 2)


def rehearse(source, ref, label, out_dir, offline=True, keep=False):
    out = Path(out_dir)
    logs = out / label
    logs.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"rehearsal-{label}-"))
    clone = work / "repo"
    record = {"label": label, "source": source, "ref": ref,
              "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "python": sys.version.split()[0], "platform": platform.platform(),
              "steps": [], "broke": []}

    rc, secs = sh(f"git clone -q {source} {clone} && git -C {clone} checkout -q {ref}",
                  work, logs / "clone.log")
    record["steps"].append({"step": "clone", "exit": rc, "seconds": secs})
    if rc:
        record["broke"].append("clone failed; see clone.log")
        return _finish(record, out, label)
    record["commit"] = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                                      capture_output=True, text=True).stdout.strip()
    untracked = [p for p in ("data/raw", "data/processed/hinge") if (clone / p).exists()]
    record["fresh"] = not untracked
    if untracked:
        record["broke"].append(f"clone already holds data it should not: {untracked}")

    venv = work / "venv"
    rc, secs = sh(f"{sys.executable} -m venv {venv} && {venv}/bin/python -m pip install -q "
                  f"-r requirements-demo.txt", clone, logs / "install.log")
    record["steps"].append({"step": "install (network on)", "exit": rc, "seconds": secs})
    if rc:
        record["broke"].append("dependency install failed; see install.log")
        return _finish(record, out, label)
    py = venv / "bin" / "python"

    prefix = offline_prefix() if offline else None
    record["network"] = "off (unshare -rn)" if prefix else (
        "ON: this OS cannot drop networking; turn Wi-Fi off by hand" if offline else "on")
    env = dict(os.environ, PIP_NO_INDEX="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    for name, template in STEPS:
        cmd = template.format(py=py, tmp=work)
        rc, secs = sh(cmd, clone, logs / f"{name}.log", prefix=prefix, env=env)
        record["steps"].append({"step": name, "exit": rc, "seconds": secs})
        if rc:
            tail = (logs / f"{name}.log").read_text(encoding="utf-8").strip().splitlines()[-1:]
            record["broke"].append(f"{name}: exit {rc}: {tail[0] if tail else ''}")

    changed = subprocess.run(["git", "-C", str(clone), "status", "--porcelain",
                              "--untracked-files=no"], capture_output=True, text=True).stdout
    record["tracked_files_changed"] = changed.split("\n")[:-1] if changed else []
    if changed:
        record["broke"].append("the demo rewrote tracked files: "
                               + ", ".join(l[3:] for l in changed.splitlines()))
    if not keep:
        shutil.rmtree(work, ignore_errors=True)
    else:
        record["kept_at"] = str(work)
    return _finish(record, out, label)


def _finish(record, out, label):
    record["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["demo_seconds"] = round(sum(s["seconds"] for s in record["steps"]
                                       if s["step"] not in ("clone", "install (network on)")), 2)
    (Path(out) / f"{label}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"\n{label}: {record.get('commit', '?')[:7]}  network {record.get('network', '?')}")
    for s in record["steps"]:
        print(f"  {s['step']:<22} exit {s['exit']:<3} {s['seconds']:>8.2f} s")
    print(f"  demo steps total {record['demo_seconds']} s")
    print("  broke: " + ("; ".join(record["broke"]) if record["broke"] else "nothing"))
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default=str(REPO_ROOT),
                    help="clone source: the GitHub URL for a real rehearsal")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--label", required=True, help="e.g. clone-1")
    ap.add_argument("--out", default=str(REPO_ROOT / "reports" / "rehearsals"
                                         / datetime.now().strftime("%Y-%m-%d")))
    ap.add_argument("--online", action="store_true", help="do not drop networking")
    ap.add_argument("--keep", action="store_true", help="keep the clone for inspection")
    a = ap.parse_args(argv)
    ref = a.ref
    if ref == "HEAD" and Path(a.source).exists():
        ref = subprocess.run(["git", "-C", a.source, "rev-parse", "HEAD"],
                             capture_output=True, text=True).stdout.strip()
    r = rehearse(a.source, ref, a.label, a.out, offline=not a.online, keep=a.keep)
    return 1 if r["broke"] else 0


if __name__ == "__main__":
    sys.exit(main())

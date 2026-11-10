#!/usr/bin/env python3
"""
Train Model 2 (LoRA) on Apple Silicon, and record the run properly.

A thin wrapper around `mlx_lm lora`. It exists for three reasons, all of them
about reporting rather than training:

1. **Learning curves.** Team Meeting 2 slide 6 asks for learning curves
   "including any run that diverged". `mlx_lm` prints losses to stdout and
   keeps no history, so this parses them into `runs/*.json` and a CSV that the
   figure script can read. A run whose validation loss turns upward is kept and
   reported, not re-run quietly.

2. **Compute actually consumed.** Same slide. Wall clock, tokens per second,
   peak memory and the device, written down at the end of the run rather than
   remembered afterwards.

3. **The config travels with the result.** The recipe and all its deviations
   from section 4.1 live in `configs/*.yaml`, and the exact config used is
   copied into the run record. A loss curve without its hyperparameters is not
   evidence.

Usage
-----
  python3 scripts/train_lora_mlx.py -c configs/m2_lora_qwen7b.yaml
  python3 scripts/train_lora_mlx.py -c configs/m2_lora_qwen7b.yaml --seed 1 \\
      --adapter-path models/adapters/m2_qwen7b_seed1 --iters 600

Three seeds are what 298-54 asks for. Run it three times with different
--seed/--adapter-path, then score each adapter and pass all three hypothesis
files to the harness, which reports mean and standard deviation.
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# mlx_lm's report lines, e.g.
#   Iter 10: Train loss 2.145, Learning Rate 1.000e-04, It/sec 0.412, ...
#   Iter 50: Val loss 1.983, Val took 12.345s
TRAIN_RE = re.compile(r"Iter\s+(\d+):\s*Train loss\s+([0-9.]+)")
VAL_RE = re.compile(r"Iter\s+(\d+):\s*Val loss\s+([0-9.]+)")
TOKSEC_RE = re.compile(r"Tokens/sec\s+([0-9.]+)")
PEAK_RE = re.compile(r"Peak mem(?:ory)?\s+([0-9.]+)\s*GB")


def diverged(val_curve, patience=2):
    """True if validation loss rose on the last `patience` consecutive evals.

    Reported rather than hidden. A diverged run is a result about the
    hyperparameters, and slide 6 asks for it by name.
    """
    if len(val_curve) < patience + 1:
        return False
    tail = [v for _, v in val_curve[-(patience + 1):]]
    return all(b > a for a, b in zip(tail, tail[1:]))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("-c", "--config", required=True)
    p.add_argument("--seed", type=int, default=None, help="override the config seed")
    p.add_argument("--iters", type=int, default=None)
    p.add_argument("--adapter-path", default=None)
    p.add_argument("--system", default=None, help="name for the run record")
    p.add_argument("--runs-dir", default=str(REPO_ROOT / "runs"))
    args = p.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit("{}: not found".format(config_path))
    config_text = config_path.read_text(encoding="utf-8")

    cmd = [sys.executable, "-m", "mlx_lm", "lora", "-c", str(config_path)]
    for flag, value in (("--seed", args.seed), ("--iters", args.iters),
                        ("--adapter-path", args.adapter_path)):
        if value is not None:
            cmd += [flag, str(value)]

    system = args.system or "M2 LoRA seed {}".format(args.seed if args.seed is not None else 42)
    print("$ {}\n".format(" ".join(cmd)))

    train_curve, val_curve = [], []
    tok_sec, peak_gb = None, None
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    try:
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            m = TRAIN_RE.search(line)
            if m:
                train_curve.append((int(m.group(1)), float(m.group(2))))
            m = VAL_RE.search(line)
            if m:
                val_curve.append((int(m.group(1)), float(m.group(2))))
            m = TOKSEC_RE.search(line)
            if m:
                tok_sec = float(m.group(1))
            m = PEAK_RE.search(line)
            if m:
                peak_gb = float(m.group(1))
    except KeyboardInterrupt:
        proc.terminate()
        print("\ninterrupted; recording the partial curve", file=sys.stderr)
    rc = proc.wait()
    elapsed = time.time() - t0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = re.sub(r"[^A-Za-z0-9]+", "-", system).strip("-").lower()
    runs = Path(args.runs_dir)
    runs.mkdir(parents=True, exist_ok=True)

    curve_csv = runs / "{}_{}_curve.csv".format(stamp, tag)
    with curve_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["iter", "split", "loss"])
        for it, loss in train_curve:
            w.writerow([it, "train", loss])
        for it, loss in val_curve:
            w.writerow([it, "val", loss])

    record = {
        "kind": "train_lora",
        "system": system,
        "returncode": rc,
        "ok": rc == 0,
        "command": " ".join(cmd),
        "config_file": str(config_path.relative_to(REPO_ROOT)),
        "config": config_text,
        "overrides": {"seed": args.seed, "iters": args.iters,
                      "adapter_path": args.adapter_path},
        "train_curve": [{"iter": i, "loss": l} for i, l in train_curve],
        "val_curve": [{"iter": i, "loss": l} for i, l in val_curve],
        "first_train_loss": train_curve[0][1] if train_curve else None,
        "last_train_loss": train_curve[-1][1] if train_curve else None,
        "best_val_loss": min((l for _, l in val_curve), default=None),
        "best_val_iter": min(val_curve, key=lambda t: t[1])[0] if val_curve else None,
        "last_val_loss": val_curve[-1][1] if val_curve else None,
        "diverged": diverged(val_curve),
        "elapsed_seconds": round(elapsed, 2),
        "gpu_hours": round(elapsed / 3600, 5),
        "tokens_per_second": tok_sec,
        "peak_memory_gb": peak_gb,
        "device": "Apple M4, 16 GB unified memory (MLX)",
        "curve_csv": str(curve_csv.relative_to(REPO_ROOT)),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    rec_path = runs / "{}_{}.json".format(stamp, tag)
    rec_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print("\nrun record -> {}".format(rec_path))
    print("curve      -> {}".format(curve_csv))
    print("{:.1f}s ({:.3f} GPU-hours)".format(elapsed, record["gpu_hours"]))
    if train_curve:
        print("train loss {:.4f} -> {:.4f} over {} reports".format(
            train_curve[0][1], train_curve[-1][1], len(train_curve)))
    if val_curve:
        print("val loss best {:.4f} at iter {}, last {:.4f}".format(
            record["best_val_loss"], record["best_val_iter"], record["last_val_loss"]))
    if record["diverged"]:
        print("\nVALIDATION LOSS ROSE on the last evals. This run is kept and "
              "reported as a diverged run (Team Meeting 2 slide 6 asks for it); "
              "do not quietly re-run it with different settings and present only "
              "the survivor.")
    if rc != 0:
        print("\nmlx_lm exited {}".format(rc), file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())

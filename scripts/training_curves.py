#!/usr/bin/env python3
"""
Plot training and validation loss from the run records.

Team Meeting 2 slide 6 asks for learning curves "including any run that
diverged". This reads whatever `runs/*_train-lora*.json` records exist and draws
them all, marking a diverged run rather than leaving it out. Picking the nicest
curve and showing only that is the specific thing the slide is written to
prevent.

Usage
-----
  python3 scripts/training_curves.py
  python3 scripts/training_curves.py --runs-dir runs --out reports/figures/fig7_training_curves.png
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "reports" / "figures" / "fig7_training_curves.png"


def load_runs(runs_dir):
    runs = []
    for path in sorted(Path(runs_dir).glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if rec.get("kind") != "train_lora":
            continue
        if not rec.get("train_curve"):
            continue
        runs.append((path.name, rec))
    return runs


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--runs-dir", default=str(REPO_ROOT / "runs"))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    args = p.parse_args(argv)

    runs = load_runs(args.runs_dir)
    if not runs:
        print("no train_lora run records with a loss curve in {}.\n"
              "Train something first: python3 scripts/train_lora_mlx.py "
              "-c configs/m2_lora_qwen7b.yaml".format(args.runs_dir),
              file=sys.stderr)
        return 1

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5.5))
    colours = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    for i, (name, rec) in enumerate(runs):
        c = colours[i % len(colours)]
        label = rec.get("system", name)
        tr = rec["train_curve"]
        ax.plot([d["iter"] for d in tr], [d["loss"] for d in tr],
                color=c, linewidth=1.4, alpha=0.9, label="{} — train".format(label))
        va = rec.get("val_curve") or []
        if va:
            ax.plot([d["iter"] for d in va], [d["loss"] for d in va],
                    color=c, linewidth=1.8, linestyle="--", marker="o",
                    markersize=4, label="{} — validation".format(label))
            best = rec.get("best_val_iter")
            if best is not None:
                bl = rec.get("best_val_loss")
                ax.annotate("best {:.3f} @ {}".format(bl, best),
                            xy=(best, bl), xytext=(4, 6),
                            textcoords="offset points", fontsize=8, color=c)
        if rec.get("diverged"):
            ax.plot([], [], " ", label="   ^ DIVERGED (validation loss rising)")

    ax.set_xlabel("iteration")
    ax.set_ylabel("loss (cross-entropy on the completion)")
    ax.set_title("Model 2 LoRA — training and validation loss\n"
                 "Qwen2.5-7B-Instruct 4-bit, Apple M4 16 GB via MLX")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="upper right")

    note = []
    for _name, rec in runs:
        note.append("{}: {:.0f}s, {:.3f} GPU-h, peak {} GB".format(
            rec.get("system", "run"), rec.get("elapsed_seconds") or 0,
            rec.get("gpu_hours") or 0,
            rec.get("peak_memory_gb") if rec.get("peak_memory_gb") else "n/a"))
    fig.text(0.01, 0.01, "   |   ".join(note), fontsize=7, color="#444")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(out, dpi=150)
    print("figure -> {}".format(out.relative_to(REPO_ROOT)))
    for _name, rec in runs:
        print("  {:<34} train {:.4f} -> {:.4f}   best val {}   {}".format(
            rec.get("system", "run")[:34],
            rec.get("first_train_loss") or float("nan"),
            rec.get("last_train_loss") or float("nan"),
            "{:.4f}".format(rec["best_val_loss"]) if rec.get("best_val_loss") else "n/a",
            "DIVERGED" if rec.get("diverged") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

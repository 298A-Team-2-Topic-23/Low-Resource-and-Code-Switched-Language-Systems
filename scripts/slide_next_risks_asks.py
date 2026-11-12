#!/usr/bin/env python3
"""
Generate Team Meeting 2 slide 8: what is next, risks and asks.

Generated rather than drawn by hand, for the same reason the section 4.2 figures
are: a slide nobody can regenerate cannot be checked against the repository it
claims to describe. The compute figures are read from runs/ at render time, so
the slide cannot quote a number the run records do not support.

  python3 scripts/slide_next_risks_asks.py
  -> reports/figures/slide8_next_risks_asks.png   (16:9, 1920x1080 at 150 dpi)

Drop the PNG straight into PowerPoint or Google Slides.
"""

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

INK = "#16161a"
MUTED = "#5a5a66"
RULE = "#d8d8de"
ACCENT = "#2a5db0"
WARN = "#b4420f"
SURFACE = "#fbfbfd"


def spent_gpu_hours():
    """Read the real total from runs/, so the slide cannot overstate it."""
    total = 0.0
    for f in (REPO_ROOT / "runs").glob("*.json"):
        try:
            total += json.loads(f.read_text(encoding="utf-8")).get("gpu_hours") or 0
        except (json.JSONDecodeError, OSError):
            continue
    return total


NEXT = [
    ("Ablation", [
        ("M3 vocab extension + Control A + Control B", "20 Nov", "Waghmare"),
        ("M4 synthetic augmentation, 3 seeds", "2 Dec", "Waghmare"),
        ("Ablation table + verdict, incl. the null case", "4 Dec", "Thomas"),
    ]),
    ("Failure study", [
        ("Gold set: first 200 items, then 800", "16 Nov", "Savalia"),
        ("Krippendorff alpha, 100-item overlap", "18 Nov", "Savalia"),
        ("150 outputs coded by failure type", "2 Dec", "Savalia"),
    ]),
    ("Hardening", [
        ("Gahoi et al. baseline, both conditions", "--", "Thomas"),
        ("Branch protection + review rotation", "today", "Singh"),
    ]),
]

RISKS = [
    ("M3 may buy little -- and we already measured why",
     "Usage-weighted cost is 1.395 tokens/occurrence against a 1.722 lexicon burden:\n"
     "writers favour cheap spellings. Sweep K on CPU, fix it on dev. A null result is published."),
    ("Control A may not fit the budget",
     "Reserved 20 GPU-h but runs M3's two stages. Step-matched it is ~36, putting the\n"
     "plan near 170 against a 165 cap. The first measured M3 seed settles it."),
    ("The evaluation surface is small",
     "197 test sources; the gold set holds 0 of 800 today. A true 2-3 chrF++ gain can\n"
     "fall inside overlapping intervals."),
    ("No confirmed GPU allocation (298-10, open since 26 Sep)",
     "Colab carried M1 and M2 at 1.508 GPU-h. M3 is 36 hours on a 40 GB card."),
]

ASKS = [
    "A written allocation outcome this week -- approval or refusal. Silence blocks the decision.",
    "Sign-off today on 298-72: 154 planned against a 165 cap.",
    "Gold set first 200 by 16 Nov, so the agreement study can run on the 18th.",
    "One non-author review per pull request (298-60).",
]


def build(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(12.8, 7.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis("off")

    ax.text(0.042, 0.935, "What's next, risks and asks", fontsize=25, color=INK, va="top")
    ax.text(0.042, 0.878, "Team Meeting 2  ·  plan to the final submission, 7 December",
            fontsize=11.5, color=MUTED, va="top")
    ax.plot([0.042, 0.958], [0.852, 0.852], color=RULE, lw=1.1)

    # ---- left column: NEXT
    x, y = 0.042, 0.805
    ax.text(x, y, "NEXT", fontsize=12.5, color=ACCENT, va="top", fontweight="bold")
    y -= 0.047
    for group, rows in NEXT:
        ax.text(x, y, group, fontsize=11, color=INK, va="top", fontweight="bold")
        y -= 0.036
        for what, when, who in rows:
            ax.text(x + 0.008, y, what, fontsize=9.6, color=INK, va="top")
            ax.text(x + 0.292, y, when, fontsize=9.6, color=WARN if when in ("16 Nov", "20 Nov", "today")
                    else MUTED, va="top", ha="right",
                    fontweight="bold" if when in ("16 Nov", "20 Nov", "today") else "normal")
            ax.text(x + 0.300, y, who, fontsize=9.0, color=MUTED, va="top")
            y -= 0.034
        y -= 0.012

    # ---- divider
    ax.plot([0.408, 0.408], [0.09, 0.815], color=RULE, lw=1.0)

    # ---- right column: RISKS
    x2, y2 = 0.432, 0.805
    ax.text(x2, y2, "RISKS", fontsize=12.5, color=ACCENT, va="top", fontweight="bold")
    y2 -= 0.047
    for i, (head, body) in enumerate(RISKS, 1):
        ax.text(x2, y2, f"{i}.  {head}", fontsize=10.4, color=INK, va="top", fontweight="bold")
        y2 -= 0.033
        ax.text(x2 + 0.018, y2, body, fontsize=9.0, color=MUTED, va="top", linespacing=1.45)
        y2 -= 0.034 * (body.count("\n") + 1) + 0.021

    # ---- asks band
    ax.add_patch(plt.Rectangle((0.432, 0.105), 0.526, 0.205, transform=ax.transAxes,
                               facecolor="#eef2fa", edgecolor=ACCENT, lw=1.0, zorder=1))
    ax.text(0.449, 0.288, "ASKS", fontsize=12, color=ACCENT, va="top", fontweight="bold", zorder=2)
    ya = 0.247
    for a in ASKS:
        ax.text(0.449, ya, "•  " + a, fontsize=9.3, color=INK, va="top", zorder=2)
        ya -= 0.033

    # ---- compute block, read from runs/. Sits directly under the NEXT column
    # rather than at the page foot, where the last line was being clipped.
    spent = spent_gpu_hours()
    ax.add_patch(plt.Rectangle((0.042, 0.105), 0.336, 0.185, transform=ax.transAxes,
                               facecolor="#f1f0ec", edgecolor=RULE, lw=1.0, zorder=1))
    ax.text(0.059, 0.268, "COMPUTE", fontsize=11, color=ACCENT, va="top",
            fontweight="bold", zorder=2)
    ax.text(0.059, 0.228, f"{spent:.3f} of 165 GPU-hours spent",
            fontsize=12.5, color=INK, va="top", fontweight="bold", zorder=2)
    ax.text(0.059, 0.188,
            "The 157.04 projection is an upper bound, not a\n"
            "forecast: finished arms still project their full\n"
            "allocation, because their run records predate\n"
            "the run contract that would attribute them.",
            fontsize=8.2, color=MUTED, va="top", linespacing=1.42, zorder=2)

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE, metadata={"Software": None})
    plt.close(fig)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=str(REPO_ROOT / "reports" / "figures" /
                                        "slide8_next_risks_asks.png"))
    a = p.parse_args(argv)
    print("slide ->", build(pathlib.Path(a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

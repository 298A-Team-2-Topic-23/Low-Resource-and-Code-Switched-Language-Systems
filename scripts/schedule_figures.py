"""Generate Workbook 1 Figures 2.4.1 (Gantt) and 2.4.2 (PERT) from one task list.

Usage:  python scripts/schedule_figures.py [--out reports/figures]

The PERT network is computed in working days (Mon-Fri) from Monday 14 September 2026,
the start of Linear Cycle 1. The Gantt chart draws the same tasks on calendar dates,
coloured by status as of STATUS_DATE, with two-week Linear cycles shaded behind the bars.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Patch

PROJECT_START = date(2026, 9, 14)          # Linear Cycle 1 starts
STATUS_DATE = date(2026, 10, 7)            # Workbook 1 submission
DEADLINE = date(2026, 12, 7)               # Final report due
TM2 = date(2026, 11, 12)                   # Team Meeting 2 (live prototype)
CHECKPOINTS = [date(2026, 9, 10), date(2026, 10, 8), date(2026, 11, 12), date(2026, 12, 8)]
CYCLE_LEN = 14

# PERT network: id, label, owner, duration (working days), dependencies, status
NETWORK = [
    ("A", "Corpus acquisition", "Yash", 10, [], "done"),
    ("B", "Pre-processing &\nlanguage ID", "Yash", 4, ["A"], "done"),
    ("C", "Disjoint split\nre-derivation", "Yash", 3, ["B"], "done"),
    ("D", "Tokenizer fertility\n+ CMI statistics", "Sarvesh", 8, ["A"], "done"),
    ("E", "Annotation guidelines\n+ 50-item pilot", "Jenil", 10, ["A"], "progress"),
    ("F", "Evaluation harness", "Shibin", 3, ["C"], "progress"),
    ("G", "800-item gold set", "Jenil", 20, ["E"], "planned"),
    ("H", "Baseline\nreproduction", "Shibin", 10, ["F"], "planned"),
    ("I", "Model 1\nzero-shot", "Sarvesh", 5, ["F"], "progress"),
    ("J", "Model 2\nQLoRA", "Sarvesh", 8, ["H", "I"], "planned"),
    ("K", "Serving +\ninterface", "Prakhar", 12, ["F"], "planned"),
    ("L", "Cloud deploy\n+ clone test", "Prakhar", 3, ["J", "K"], "planned"),
    ("M", "Failure study\n+ ablation", "Sarvesh", 10, ["L", "G", "D"], "planned"),
    ("N", "Final report\n+ 298B plan", "Jenil", 7, ["M"], "planned"),
]

# Extra Gantt rows that are not PERT activities: label, owner, start, end, status
EXTRA = [
    ("Project scoping & abstract (298-7, 298-8)", "Jenil", date(2026, 9, 1), date(2026, 9, 10), "done"),
    ("Linear + GitHub setup (298-27, 298-28)", "Prakhar", date(2026, 9, 1), date(2026, 10, 14), "progress"),
    ("Literature & technology survey (298-6, 298-34)", "Yash", date(2026, 9, 8), date(2026, 10, 7), "done"),
    ("Workbook 1 authoring", "Jenil", date(2026, 9, 28), date(2026, 10, 7), "done"),
    ("Team Meeting 1 - pipeline demo", "All", date(2026, 10, 8), date(2026, 10, 9), "checkpoint"),
    ("Workbook 2 authoring", "Jenil", date(2026, 10, 30), date(2026, 11, 11), "planned"),
    ("Team Meeting 2 - live prototype", "All", date(2026, 11, 12), date(2026, 11, 13), "checkpoint"),
    ("Reproducibility check (clean clone)", "Prakhar", date(2026, 11, 25), date(2026, 12, 2), "planned"),
    ("Conference Day presentation", "All", date(2026, 12, 8), date(2026, 12, 9), "checkpoint"),
]
ISSUE = {"A": "298-19, 298-20", "B": "298-38", "C": "298-11", "D": "298-13, 298-22", "E": "298-12",
         "F": "298-14", "G": "298-21", "H": "298-15, 298-16", "I": "298-24", "J": "298-25"}
COLOURS = {"done": "#2e7d32", "progress": "#1565c0", "planned": "#90a4ae",
           "risk": "#c62828", "checkpoint": "#f9a825"}
LABELS = {"done": "Complete", "progress": "In progress", "planned": "Planned",
          "checkpoint": "Graded checkpoint"}


def wd_to_date(n):
    """Working-day offset from PROJECT_START to a calendar date (start of that day)."""
    return np.busday_offset(np.datetime64(PROJECT_START), n, roll="forward").astype(date)


def compute(network, deadline_wd):
    rows, succ = {}, {n[0]: [] for n in network}
    for ident, label, owner, dur, deps, status in network:
        es = max((rows[d]["EF"] for d in deps), default=0)
        rows[ident] = dict(id=ident, label=label, owner=owner, d=dur, deps=deps,
                           status=status, ES=es, EF=es + dur)
        for d in deps:
            succ[d].append(ident)
    for ident, *_ in reversed(network):
        r = rows[ident]
        r["LF"] = min((rows[s]["LS"] for s in succ[ident]), default=deadline_wd)
        r["LS"] = r["LF"] - r["d"]
        r["float"] = r["LS"] - r["ES"]
    min_float = min(r["float"] for r in rows.values())
    for r in rows.values():
        r["critical"] = r["float"] == min_float
    return rows, succ


def gantt(rows, out):
    items = []
    for r in rows.values():
        name = r["label"].replace("\n", " ")
        if r["id"] in ISSUE:
            name += f" ({ISSUE[r['id']]})"
        items.append((f"{r['id']}  {name}", r["owner"], wd_to_date(r["ES"]),
                      wd_to_date(r["EF"]), r["status"]))
    for label, owner, s, e, st in EXTRA:
        items.append((label, owner, s, e, st))
    items.sort(key=lambda x: (x[2], x[3]))

    fig, ax = plt.subplots(figsize=(20.48, 13.0), dpi=100)
    c0 = PROJECT_START
    k = 1
    while c0 < DEADLINE:
        c1 = c0 + timedelta(days=CYCLE_LEN)
        ax.axvspan(c0, c1, color="#eef3f8" if k % 2 else "#ffffff", zorder=0)
        ax.text(c0 + timedelta(days=7), -1.05, f"Cycle {k}", ha="center", va="bottom",
                fontsize=10, color="#455a64")
        c0, k = c1, k + 1
    for i, (label, owner, s, e, st) in enumerate(items):
        ax.barh(i, (e - s).days, left=s, color=COLOURS[st], height=0.6, zorder=2)
        ax.text(e + timedelta(days=1), i, owner, va="center", fontsize=10, color="#37474f")
    for cp in CHECKPOINTS:
        ax.axvline(cp, color="#f9a825", linestyle="--", linewidth=1.6, zorder=1)
    ax.axvline(STATUS_DATE, color="#263238", linewidth=2, zorder=3)
    ax.text(STATUS_DATE, len(items) - 0.2, "Status date 7 Oct\n(Workbook 1 submitted)",
            ha="center", va="bottom", fontsize=10, color="#263238")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([x[0] for x in items], fontsize=11)
    ax.set_ylim(len(items) + 1.0, -1.3)
    ax.set_xlim(date(2026, 8, 31), date(2026, 12, 14))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(axis="x", labelsize=11)
    ax.grid(axis="x", linestyle=":", color="#b0bec5", zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("Figure 2.4.1  Project schedule, DATA 298A (Team 2, Topic 23) - status as of 7 October 2026",
                 fontsize=15, fontweight="bold", pad=24)
    handles = [Patch(color=COLOURS[k], label=v) for k, v in LABELS.items()]
    handles.append(Patch(facecolor="#eef3f8", edgecolor="#b0bec5", label="Two-week Linear cycle"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=5,
              fontsize=11, frameon=False)
    fig.text(0.01, 0.005, "Generated by scripts/schedule_figures.py. Task letters A-N match Figure 2.4.2; "
             "Linear issue identifiers in parentheses.", fontsize=10, color="#546e7a")
    fig.subplots_adjust(left=0.24, right=0.98, top=0.93, bottom=0.09)
    fig.savefig(out / "fig2_4_1_gantt.png", dpi=100)
    plt.close(fig)


def pert(rows, succ, out):
    pos = {"A": (0, 2.4), "B": (1, 4.0), "C": (2, 4.0), "F": (3, 4.0), "H": (4, 4.0),
           "J": (5, 4.0), "I": (4, 2.4), "K": (5, 2.4), "L": (6, 3.2), "M": (7, 2.4),
           "N": (8, 2.4), "E": (2, 0.8), "G": (3.5, 0.8), "D": (1, -0.6)}
    fig, ax = plt.subplots(figsize=(20.48, 10.39), dpi=100)
    ax.set_xlim(-0.6, 8.6)
    ax.set_ylim(-1.3, 6.0)
    ax.axis("off")
    w, h = 0.86, 1.0
    red, grey = "#c62828", "#78909c"
    for a, bs in succ.items():
        for b in bs:
            (x0, y0), (x1, y1) = pos[a], pos[b]
            crit = rows[a]["critical"] and rows[b]["critical"] and rows[a]["EF"] == rows[b]["ES"]
            ax.annotate("", xy=(x1 - w / 2, y1), xytext=(x0 + w / 2, y0),
                        arrowprops=dict(arrowstyle="-|>", lw=3 if crit else 1.4,
                                        color=red if crit else grey,
                                        connectionstyle="arc3,rad=0.3" if (a, b) == ("D", "M") else "arc3,rad=0.0"), zorder=1)
    for r in rows.values():
        x, y = pos[r["id"]]
        crit = r["critical"]
        box = FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02",
                             fc="#fdecea" if crit else "#eceff1", ec=red if crit else "#607d8b",
                             lw=2.6 if crit else 1.4, zorder=2)
        ax.add_patch(box)
        ax.text(x, y + 0.24, f"{r['id']}  {r['label']}", ha="center", va="center",
                fontsize=10.5, fontweight="bold", zorder=3)
        ax.text(x, y - 0.13, f"d={r['d']}d  float={r['float']}d  {r['owner']}", ha="center",
                va="center", fontsize=9, color="#37474f", zorder=3)
        ax.text(x, y - 0.34, f"ES {r['ES']}  EF {r['EF']}  LF {r['LF']}", ha="center", va="center",
                fontsize=8.5, color="#546e7a", zorder=3)
    path = " -> ".join(r["id"] for r in rows.values() if r["critical"])
    end = max(r["EF"] for r in rows.values())
    flt = min(r["float"] for r in rows.values())
    ax.text(-0.55, 5.95, "Figure 2.4.2  PERT network with critical path, DATA 298A",
            fontsize=16, fontweight="bold", va="top")
    ax.text(-0.55, 5.55,
            f"Critical path {path} (red): {end} working days from Monday 14 Sep 2026, ending "
            f"{wd_to_date(end - 1):%a %d %b}; project float {flt} working days before the 7 Dec deadline.\n"
            "ES = earliest start, EF = earliest finish, LF = latest finish, in working days (Mon-Fri) from 14 Sep. "
            "A-D complete; E, F, I in progress. Generated by scripts/schedule_figures.py.",
            fontsize=11, va="top", color="#37474f")
    fig.savefig(out / "fig2_4_2_pert.png", dpi=100)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/figures")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    deadline_wd = int(np.busday_count(np.datetime64(PROJECT_START), np.datetime64(DEADLINE)))
    rows, succ = compute(NETWORK, deadline_wd)
    gantt(rows, out)
    pert(rows, succ, out)
    with open(out / "fig2_4_2_pert.csv", "w") as f:
        f.write("id,label,owner,duration,deps,ES,EF,LS,LF,float,critical,status\n")
        for r in rows.values():
            f.write(f"{r['id']},{r['label'].replace(chr(10), ' ')},{r['owner']},{r['d']},"
                    f"{' '.join(r['deps'])},{r['ES']},{r['EF']},{r['LS']},{r['LF']},{r['float']},"
                    f"{r['critical']},{r['status']}\n")
    l_ef = wd_to_date(rows["L"]["EF"] - 1)
    print(f"deadline_wd={deadline_wd} end={max(r['EF'] for r in rows.values())} "
          f"L finishes {l_ef} (TM2 {TM2})")
    for r in rows.values():
        print(r["id"], r["ES"], r["EF"], r["LF"], r["float"], r["critical"],
              wd_to_date(r["ES"]), wd_to_date(r["EF"] - 1))


if __name__ == "__main__":
    main()

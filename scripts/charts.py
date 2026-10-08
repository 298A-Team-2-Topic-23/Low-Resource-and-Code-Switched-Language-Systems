#!/usr/bin/env python3
"""Generate Workbook 1 Gantt, PERT and timing evidence. [298-37]

Dates/durations are planning assumptions, not completed-work measurements.
Calendar-day offsets start at 2026-09-28; terminal deadlines are explicit.
"""
import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

START = date(2026, 9, 28)
# id, label, owner, duration (calendar days), predecessors, terminal deadline
NETWORK = [
    ("298-38", "Pipeline", "Yash", 5, (), None),
    ("298-39", "EDA figures", "Sarvesh", 2, ("298-38",), None),
    ("298-42", "Assembly", "Jenil", 2, ("298-39",), None),
    ("submission", "Workbook submission", "Jenil", 0, ("298-42",), 9),
    ("298-40", "Rehearsal window", "Prakhar", 4, ("298-38",), None),
    ("demo", "ISA demo", "All", 0, ("298-40",), 10),
]
# Issue, task, owner, planned start/end, artifact status as observed on main.
TASKS = [
    ("298-32", "Background", "Jenil", 0, 5, "section merged"),
    ("298-33", "Requirements", "Shibin", 0, 5, "section merged"),
    ("298-34", "Surveys / comparison", "Yash", 0, 7, "section absent"),
    ("298-35", "Data management", "Yash", 0, 7, "section absent"),
    ("298-36", "Management plan", "Sarvesh", 0, 7, "section merged"),
    ("298-37", "Resources / schedule", "Prakhar", 2, 8, "this PR"),
    ("298-38", "Pipeline", "Yash", 0, 5, "branch only"),
    ("298-39", "EDA evidence", "Sarvesh", 5, 7, "partial evidence merged"),
    ("298-40", "Rehearsal window", "Prakhar", 5, 9, "team rehearsal pending"),
    ("298-41", "References / checklist", "Shibin", 2, 8, "section merged"),
    ("298-42", "Assembly / submission", "Jenil", 7, 9, "assembly absent"),
    ("298-43", "Meeting minutes", "Jenil", 0, 10, "minutes absent"),
]


def timings(network):
    """Forward/backward pass on a topologically ordered dependency network."""
    rows = {}
    successors = {node[0]: [] for node in network}
    for ident, label, owner, duration, deps, deadline in network:
        es = max((rows[dep]["EF"] for dep in deps), default=0)
        rows[ident] = dict(id=ident, label=label, owner=owner, duration=duration,
                           dependencies=", ".join(deps), ES=es, EF=es + duration)
        for dep in deps:
            successors[dep].append(ident)
    for ident, _, _, duration, _, deadline in reversed(network):
        lf = min((rows[s]["LS"] for s in successors[ident]), default=deadline)
        if lf is None:
            raise ValueError("terminal node needs a deadline: " + ident)
        row = rows[ident]
        row.update(LF=lf, LS=lf - duration)
        row["float"] = row["LS"] - row["ES"]
        if row["float"] < 0:
            raise ValueError("schedule misses deadline: " + ident)
        row["critical"] = row["float"] == 0
    return rows


def generate(outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import FancyArrowPatch, Patch

    outdir.mkdir(parents=True, exist_ok=True)
    rows = timings(NETWORK)
    with (outdir / "workbook1_pert.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(next(iter(rows.values()))))
        writer.writeheader()
        writer.writerows(rows.values())
    red, blue = "#b93838", "#316eaa"
    fig, ax = plt.subplots(figsize=(15, 9))
    ax.axvspan(START, START + timedelta(days=14), color="#e8f1fa", zorder=0)
    ax.axvspan(START + timedelta(days=14), START + timedelta(days=28), color="#f1f4f6", zorder=0)
    labels = []
    for i, (ident, label, owner, start, end, status) in enumerate(TASKS):
        color = red if ident in rows and rows[ident]["critical"] else blue
        ax.barh(i, end-start, left=mdates.date2num(START + timedelta(days=start)), color=color, height=.6)
        labels.append(f"{ident}  {label} | {owner}")
        ax.text(mdates.date2num(START + timedelta(days=end)) + .25, i, status, va="center", fontsize=9)
    ax.set_yticks(range(len(TASKS)), labels)
    ax.invert_yaxis()
    ax.set_xlim(START, START + timedelta(days=28))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.axvline(START + timedelta(days=9), linestyle="--", color=red, alpha=.6)
    ax.axvline(START + timedelta(days=10), linestyle=":", color=blue, alpha=.6)
    ax.grid(axis="x", alpha=.2)
    ax.set_title("Workbook 1 plan | Cycle 2: 28 Sep–12 Oct; Cycle 3: 12–26 Oct", pad=16)
    ax.set_xlabel("2026 calendar dates | submission plan: 7 Oct; ISA demo: 8 Oct")
    ax.legend(handles=[Patch(color=red, label="Zero float in dependency plan"), Patch(color=blue, label="Parallel work")], loc="lower right")
    fig.text(.02, .015, "Planning baseline, not completion evidence. Status is a repository snapshot; live Linear status was not queried.", fontsize=9)
    fig.tight_layout(rect=(0, .035, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(outdir / ("workbook1_gantt." + ext), dpi=160)
    plt.close(fig)

    positions = {"298-38": (1.5, 3), "298-39": (5, 4.5), "298-42": (8.5, 4.5),
                 "submission": (12, 4.5), "298-40": (5, 1.5), "demo": (8.5, 1.5)}
    fig, ax = plt.subplots(figsize=(16, 7))
    for ident, _, _, _, deps, _ in NETWORK:
        x, y = positions[ident]
        for dep in deps:
            dx, dy = positions[dep]
            critical = rows[ident]["critical"] and rows[dep]["critical"]
            ax.add_patch(FancyArrowPatch((dx + 1.15, dy), (x - 1.15, y),
                arrowstyle="-|>", mutation_scale=18, linewidth=2,
                color=red if critical else blue, connectionstyle="arc3,rad=0"))
    for ident, row in rows.items():
        x, y = positions[ident]
        color = red if row["critical"] else blue
        label = (f"{ident} · {row['label']}\n{row['owner']} | duration {row['duration']} d\n"
                 f"ES {row['ES']}  EF {row['EF']}\nLS {row['LS']}  LF {row['LF']} | float {row['float']} d")
        ax.text(x, y, label, ha="center", va="center", fontsize=10,
                bbox=dict(boxstyle="round,pad=.65", facecolor="white", edgecolor=color, linewidth=2))
    ax.set(xlim=(-.2, 13.8), ylim=(0, 6))
    ax.axis("off")
    ax.set_title("PERT | critical path: 298-38 → 298-39 → 298-42 → submission", fontsize=15)
    fig.text(.05, .06, "Calendar-day offsets from 28 Sep 2026. Submission deadline: day 9 (7 Oct); demo deadline: day 10 (8 Oct).\n"
             "Durations are planning assumptions; all red nodes have zero float. Rehearsal has one day of float.\n"
             "Section writing / references must also be ready for assembly; this network isolates the pipeline dependency chain.", fontsize=10)
    fig.tight_layout(rect=(0, .17, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(outdir / ("workbook1_pert." + ext), dpi=160)
    plt.close(fig)
    for row in rows.values():
        print(f"{row['id']}: ES={row['ES']} EF={row['EF']} LS={row['LS']} LF={row['LF']} float={row['float']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path(__file__).resolve().parents[1] / "reports/figures")
    generate(parser.parse_args().outdir)

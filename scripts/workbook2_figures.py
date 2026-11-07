#!/usr/bin/env python3
"""
The imbalance and correlation figures Workbook 2 section 3.6 requires.  [298-65]

The rubric asks for "distribution, imbalance and correlation plots". The four
figures the pipeline already writes (`fig1`-`fig4`) are all distributions, so
two kinds were missing.

These are built from committed artifacts rather than from the corpus:

  reports/data_statistics.json   the real HinGE run of 8 October
  reports/fertility.variants.csv the per-group tokenizer measurement

so anyone can regenerate them from a clean clone with no raw data, which
`data/raw/` being gitignored otherwise prevents. The trade-off is that they show
what the committed aggregates hold: references-per-source as a distribution
rather than per-record, and spelling-variant groups rather than sentences.

Usage
-----
  python scripts/workbook2_figures.py
  python scripts/workbook2_figures.py --stats reports/data_statistics.json \
      --variants reports/fertility.variants.csv --out-dir reports/figures

Correlations are reported as measured. A weak or absent relationship is a
finding and is printed and annotated as one; nothing here is tuned to look
stronger than it is.
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lrcs import repo_relative  # noqa: E402
from lrcs.analysis.eda import (GRID, SERIES_1, SERIES_2, SURFACE,  # noqa: E402
                               TEXT_PRIMARY, TEXT_SECONDARY, _style)

FIGURES = {
    "imbalance": "fig5_references_per_source.png",
    "correlation": "fig6_variant_correlations.png",
}


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _ranks(values):
    """Average ranks, so ties do not distort Spearman."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 3:
        return None
    return pearson(_ranks(xs), _ranks(ys))


def describe(r):
    if r is None:
        return "not computable"
    strength = ("negligible" if abs(r) < 0.1 else
                "weak" if abs(r) < 0.3 else
                "moderate" if abs(r) < 0.5 else
                "strong")
    return "{:+.2f} ({})".format(r, strength)


def load_variants(path):
    """Per-group rows from the tokenizer fertility analysis."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                rows.append({
                    "group": row["group"],
                    "n_variants": int(row["n_variants"]),
                    "mean_tokens": float(row["mean_tokens"]),
                    "spread": int(row["spread"]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def imbalance_figure(stats, outdir, plt):
    """References per source sentence -- the corpus's main imbalance."""
    dist = {int(k): v for k, v in stats["references_per_source"]["distribution"].items()}
    mean = stats["references_per_source"]["mean"]
    counts = sorted(dist.items())
    total_sources = sum(dist.values())
    total_refs = sum(k * v for k, v in dist.items())

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([k for k, _ in counts], [v for _, v in counts],
           color=SERIES_1, edgecolor=SURFACE, linewidth=2)
    ax.axvline(mean, color=TEXT_SECONDARY, linewidth=1, linestyle="--")
    biggest = max(counts, key=lambda kv: kv[1])
    # Both labels are placed in axes fractions on the right, where the
    # distribution's long thin tail leaves room, so they cannot collide with
    # the modal bar or with each other.
    ax.annotate("mean {:.2f} references per source".format(mean),
                (0.97, 0.90), xycoords="axes fraction", ha="right",
                fontsize=8, color=TEXT_SECONDARY)
    ax.annotate("{:,} of {:,} sources ({:.0f}%) have exactly {}".format(
                    biggest[1], total_sources,
                    100.0 * biggest[1] / total_sources, biggest[0]),
                (0.97, 0.82), xycoords="axes fraction", ha="right",
                fontsize=8, color=TEXT_SECONDARY)
    _style(ax, "Human references per source sentence [{}]  "
                "({:,} sources, {:,} references)".format(
                    stats["source"], total_sources, total_refs),
           "references for one source sentence", "source sentences")
    ax.set_xticks([k for k, _ in counts])

    path = outdir / FIGURES["imbalance"]
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(str(path), dpi=150, facecolor=SURFACE)
    plt.close(fig)

    tail = sum(v for k, v in dist.items() if k >= 4)
    return path, {
        "sources": total_sources,
        "references": total_refs,
        "mean": mean,
        "modal_references": biggest[0],
        "modal_share": round(100.0 * biggest[1] / total_sources, 1),
        "four_or_more_share": round(100.0 * tail / total_sources, 1),
    }


def correlation_figure(stats, variants, outdir, plt):
    """Two correlations the hypothesis actually predicts."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    # (a) more spellings of a word <-> more tokens to encode it?
    xs = [r["n_variants"] for r in variants]
    ys = [r["mean_tokens"] for r in variants]
    r_a, rho_a = pearson(xs, ys), spearman(xs, ys)
    axes[0].scatter(xs, ys, s=28, color=SERIES_1, alpha=0.75,
                    edgecolor=SURFACE, linewidth=0.6)
    _style(axes[0], "(a) Spellings per group vs tokens per form  (n={})".format(len(xs)),
           "attested spellings in the group", "mean tokens per form")
    # Spellings per group is a small integer, so the points fall in columns.
    # Integer ticks make that honest rather than looking like a sampling grid;
    # jittering would invent positions the data does not have.
    if xs:
        axes[0].set_xticks(list(range(min(xs), max(xs) + 1)))
    axes[0].annotate("Pearson r = {}\nSpearman rho = {}".format(
                         describe(r_a), describe(rho_a)),
                     (0.97, 0.05), xycoords="axes fraction", ha="right",
                     fontsize=8, color=TEXT_SECONDARY)

    # (b) does a commoner group get spelled more inconsistently?
    top = stats["spelling_variance"].get("top_groups", [])
    xs_b = [g["occurrences"] for g in top]
    ys_b = [g["non_canonical_share"] for g in top]
    r_b, rho_b = pearson(xs_b, ys_b), spearman(xs_b, ys_b)
    axes[1].scatter(xs_b, ys_b, s=28, color=SERIES_2, alpha=0.75,
                    edgecolor=SURFACE, linewidth=0.6)
    _style(axes[1], "(b) Group frequency vs non-canonical share  (n={})".format(len(xs_b)),
           "occurrences in the corpus", "share spelled non-canonically")
    axes[1].annotate("Pearson r = {}\nSpearman rho = {}".format(
                         describe(r_b), describe(rho_b)),
                     (0.97, 0.95), xycoords="axes fraction", ha="right",
                     va="top", fontsize=8, color=TEXT_SECONDARY)

    fig.suptitle("Spelling-variant correlations [{}]".format(stats["source"]),
                 x=0.01, ha="left", fontsize=11, color=TEXT_PRIMARY)
    path = outdir / FIGURES["correlation"]
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(str(path), dpi=150, facecolor=SURFACE)
    plt.close(fig)

    return path, {
        "variants_vs_tokens": {"n": len(xs), "pearson": r_a, "spearman": rho_a},
        "frequency_vs_non_canonical": {"n": len(xs_b), "pearson": r_b,
                                       "spearman": rho_b},
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--stats", default=str(REPO_ROOT / "reports" / "data_statistics.json"))
    p.add_argument("--variants", default=str(REPO_ROOT / "reports" / "fertility.variants.csv"))
    p.add_argument("--out-dir", default=str(REPO_ROOT / "reports" / "figures"))
    p.add_argument("--summary", default=str(REPO_ROOT / "reports" / "workbook2_figures.json"),
                   help="where to write the measured correlations")
    args = p.parse_args(argv)

    stats_path, variants_path = Path(args.stats), Path(args.variants)
    for path in (stats_path, variants_path):
        if not path.exists():
            print("missing input: {}".format(path), file=sys.stderr)
            return 2

    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    if stats.get("synthetic"):
        print("warning: {} is a synthetic run; these figures would not be "
              "reportable".format(repo_relative(stats_path)), file=sys.stderr)
    variants = load_variants(variants_path)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    imb_path, imb = imbalance_figure(stats, outdir, plt)
    cor_path, cor = correlation_figure(stats, variants, outdir, plt)

    summary = {
        "source": stats["source"],
        "synthetic": stats.get("synthetic", False),
        "generated_from": {
            "statistics": repo_relative(stats_path),
            "variants": repo_relative(variants_path),
        },
        "imbalance": imb,
        "correlations": cor,
        "figures": {"imbalance": repo_relative(imb_path),
                    "correlation": repo_relative(cor_path)},
    }
    Path(args.summary).write_text(
        json.dumps(summary, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print("  figure -> {}".format(repo_relative(imb_path)))
    print("  figure -> {}".format(repo_relative(cor_path)))
    print("  summary -> {}".format(repo_relative(Path(args.summary))))
    print("\nimbalance: {:,} sources, {:,} references, mean {:.2f}; "
          "{:.1f}% have exactly {}".format(
              imb["sources"], imb["references"], imb["mean"],
              imb["modal_share"], imb["modal_references"]))
    for name, result in cor.items():
        print("correlation {}: n={} Pearson {} Spearman {}".format(
            name, result["n"], describe(result["pearson"]),
            describe(result["spearman"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

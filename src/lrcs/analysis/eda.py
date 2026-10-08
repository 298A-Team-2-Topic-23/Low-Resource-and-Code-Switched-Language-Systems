"""Stage 4 -- EDA: statistics, spelling variance, four figures.  [298-38]

Rubric component: "EDA was performed". Writes reports/data_statistics.json and
four PNGs under reports/figures/. Every number is computed from the split
records the pipeline just produced; every figure title carries the data source,
so a synthetic run can never be mistaken for a HinGE run.

The spelling-variance section is the project hypothesis seen in the data: for
each word group in analysis/spelling_variants.tsv, how many distinct spellings
actually occur and what share of occurrences use a non-canonical spelling.
"""

import json
import math
import statistics
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from lrcs import repo_relative
from lrcs.analysis.codemixing import corpus_stats
from lrcs.lexicon import form_index
from lrcs.text import dedup_key, word_tokens

FIGURES = OrderedDict([
    ("lengths", "fig1_sentence_lengths.png"),
    ("cmi", "fig2_cmi_distribution.png"),
    ("spf", "fig3_switch_point_fraction.png"),
    ("variants", "fig4_spelling_variants.png"),
])

# Reference palette (dataviz skill, light mode): slots 1-2 validated as a pair.
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SERIES_1 = "#2a78d6"   # blue
SERIES_2 = "#eb6834"   # orange


def _describe(values):
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, int(math.ceil(0.95 * len(ordered))) - 1)]
    return {
        "n": len(values),
        "mean": round(statistics.mean(values), 3),
        "median": statistics.median(values),
        "p95": p95,
        "min": ordered[0],
        "max": ordered[-1],
    }


def _entropy_bits(counts):
    total = sum(counts)
    return -sum((c / total) * math.log2(c / total) for c in counts if c) if total else 0.0


def spelling_variance(records, groups, top=15):
    """Observed spelling variation per lexicon group over Hinglish tokens."""
    index = form_index(groups)
    observed = {}
    for r in records:
        for token in word_tokens(r["hinglish"]):
            low = token.lower()
            label = index.get(low)
            if label is not None:
                observed.setdefault(label, Counter())[low] += 1
    rows = []
    for label, forms in observed.items():
        total = sum(forms.values())
        rows.append({
            "group": label,
            "occurrences": total,
            "distinct_forms": len(forms),
            "non_canonical_share": round(1 - forms.get(label, 0) / total, 4),
            "entropy_bits": round(_entropy_bits(list(forms.values())), 4),
            "forms": dict(forms.most_common()),
        })
    rows.sort(key=lambda row: (-row["occurrences"], row["group"]))
    occ = sum(row["occurrences"] for row in rows)
    non_canonical = sum(row["occurrences"] - row["forms"].get(row["group"], 0) for row in rows)
    return {
        "lexicon_groups": len(groups),
        "groups_observed": len(rows),
        "groups_with_2plus_forms": sum(1 for row in rows if row["distinct_forms"] >= 2),
        "mean_distinct_forms_per_observed_group": (
            round(statistics.mean(row["distinct_forms"] for row in rows), 3) if rows else 0.0
        ),
        "lexicon_token_occurrences": occ,
        "non_canonical_share_overall": round(non_canonical / occ, 4) if occ else 0.0,
        "top_groups": rows[:top],
    }


def compute_statistics(splits, provenance, attrition, split_info, leakage_report,
                       groups, params, manifest_path=None):
    records = [r for recs in splits.values() for r in recs]
    en_len = [len(word_tokens(r["english"])) for r in records]
    hi_len = [len(word_tokens(r["hinglish"])) for r in records]
    hi_types = Counter(t.lower() for r in records for t in word_tokens(r["hinglish"]))
    en_types = Counter(t.lower() for r in records for t in word_tokens(r["english"]))
    refs_per_source = Counter(dedup_key(r["english"]) for r in records)
    cm = corpus_stats([r["tags"] for r in records])
    per_sentence = {"cmi": cm.pop("per_sentence_cmi"), "spf": cm.pop("per_sentence_spf")}

    stats = OrderedDict()
    stats["source"] = provenance["source"]
    stats["synthetic"] = "synthetic" in provenance
    stats["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stats["params"] = params
    stats["provenance"] = {k: v for k, v in provenance.items() if k != "header"}
    stats["attrition"] = attrition
    stats["splits"] = OrderedDict(
        (name, {
            "records": len(recs),
            "unique_sources": len({dedup_key(r["english"]) for r in recs}),
            "groups": len({r["group"] for r in recs}),
        }) for name, recs in splits.items()
    )
    stats["grouping"] = split_info
    stats["leakage_gate"] = leakage_report
    stats["manifest"] = repo_relative(manifest_path)
    stats["lengths_words"] = {
        "english": _describe(en_len),
        "hinglish": _describe(hi_len),
        "hinglish_to_english_ratio_mean": round(
            statistics.mean(h / max(e, 1) for e, h in zip(en_len, hi_len)), 3) if records else 0.0,
    }
    stats["vocabulary"] = {
        "english_types": len(en_types),
        "english_tokens": sum(en_types.values()),
        "hinglish_types": len(hi_types),
        "hinglish_tokens": sum(hi_types.values()),
        "hinglish_type_token_ratio": round(len(hi_types) / max(sum(hi_types.values()), 1), 4),
        "hinglish_top_20": hi_types.most_common(20),
    }
    stats["references_per_source"] = {
        "mean": round(statistics.mean(refs_per_source.values()), 3) if refs_per_source else 0.0,
        "distribution": dict(sorted(Counter(refs_per_source.values()).items())),
    }
    stats["code_mixing"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in cm.items()}
    stats["spelling_variance"] = spelling_variance(records, groups)
    return stats, {"en_len": en_len, "hi_len": hi_len, **per_sentence}


# -------------------------------------------------------------------- figures

def _style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=11, color=TEXT_PRIMARY, pad=10)
    ax.set_xlabel(xlabel, color=TEXT_SECONDARY, fontsize=9)
    ax.set_ylabel(ylabel, color=TEXT_SECONDARY, fontsize=9)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=8, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def write_figures(stats, series, fig_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = Path(fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    tag = "[{}]".format(stats["source"])
    n = sum(s["records"] for s in stats["splits"].values())
    written = OrderedDict()

    def save(fig, key):
        path = fig_dir / FIGURES[key]
        fig.patch.set_facecolor(SURFACE)
        fig.tight_layout()
        fig.savefig(str(path), dpi=150, facecolor=SURFACE)
        plt.close(fig)
        written[key] = repo_relative(path)

    # 1. sentence lengths, English vs Hinglish -- two step outlines, not
    #    overlapping fills, so neither series hides the other
    fig, ax = plt.subplots(figsize=(7, 4))
    top = max(series["en_len"] + series["hi_len"] + [1])
    bins = range(0, top + 2)
    ax.hist(series["en_len"], bins=bins, histtype="step", linewidth=2, color=SERIES_1, label="English source")
    ax.hist(series["hi_len"], bins=bins, histtype="step", linewidth=2, color=SERIES_2, label="Romanized Hinglish")
    ax.legend(frameon=False, fontsize=8, labelcolor=TEXT_PRIMARY)
    _style(ax, "Sentence length in words {}  (n={:,})".format(tag, n), "words per sentence", "sentences")
    save(fig, "lengths")

    # 2. CMI per sentence
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(series["cmi"], bins=[i * 2.5 for i in range(21)], color=SERIES_1,
            edgecolor=SURFACE, linewidth=2)
    mean = stats["code_mixing"]["cmi_mean_all"]
    ax.axvline(mean, color=TEXT_SECONDARY, linewidth=1, linestyle="--")
    ax.annotate("mean {:.1f}".format(mean), (mean, ax.get_ylim()[1] * 0.92),
                xytext=(4, 0), textcoords="offset points", fontsize=8, color=TEXT_SECONDARY)
    _style(ax, "Code-Mixing Index per Hinglish sentence {}".format(tag),
           "CMI (0 = monolingual, 50 = even mix)", "sentences")
    save(fig, "cmi")

    # 3. switch-point fraction per sentence
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(series["spf"], bins=[i * 0.05 for i in range(21)], color=SERIES_1,
            edgecolor=SURFACE, linewidth=2)
    spf = stats["code_mixing"]["switch_point_fraction"]
    ax.axvline(spf, color=TEXT_SECONDARY, linewidth=1, linestyle="--")
    ax.annotate("corpus SPF {:.3f}".format(spf), (spf, ax.get_ylim()[1] * 0.92),
                xytext=(4, 0), textcoords="offset points", fontsize=8, color=TEXT_SECONDARY)
    _style(ax, "Switch-point fraction per Hinglish sentence {}".format(tag),
           "switch points / (language tokens - 1)", "sentences")
    save(fig, "spf")

    # 4. spelling variants: canonical vs other spellings, per word group
    rows = list(reversed(stats["spelling_variance"]["top_groups"]))
    fig, ax = plt.subplots(figsize=(7, max(3.5, 0.32 * len(rows) + 1.2)))
    if rows:
        labels = [r["group"] for r in rows]
        canonical = [r["forms"].get(r["group"], 0) for r in rows]
        other = [r["occurrences"] - c for r, c in zip(rows, canonical)]
        ax.barh(labels, canonical, color=SERIES_1, edgecolor=SURFACE, linewidth=2,
                height=0.6, label="canonical spelling")
        ax.barh(labels, other, left=canonical, color=SERIES_2, edgecolor=SURFACE,
                linewidth=2, height=0.6, label="other spellings")
        for y, r in enumerate(rows):
            ax.annotate("{} forms".format(r["distinct_forms"]), (r["occurrences"], y),
                        xytext=(4, 0), textcoords="offset points", va="center",
                        fontsize=7, color=TEXT_SECONDARY)
        ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=TEXT_PRIMARY)
    else:
        ax.text(0.5, 0.5, "no lexicon words observed", ha="center", va="center",
                transform=ax.transAxes, color=TEXT_SECONDARY)
    _style(ax, "Spelling variants per word group {}".format(tag), "occurrences", "")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    save(fig, "variants")
    return written


def write_statistics(stats, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def print_statistics(stats):
    L, cm, sv, voc = stats["lengths_words"], stats["code_mixing"], stats["spelling_variance"], stats["vocabulary"]
    print("  records           {:,} across {}".format(
        sum(s["records"] for s in stats["splits"].values()),
        ", ".join("{} {:,}".format(k, v["records"]) for k, v in stats["splits"].items())))
    print("  refs per source   {:.2f} mean".format(stats["references_per_source"]["mean"]))
    print("  length (words)    English mean {:.1f} / median {}   Hinglish mean {:.1f} / median {}".format(
        L["english"]["mean"], L["english"]["median"], L["hinglish"]["mean"], L["hinglish"]["median"]))
    print("  vocabulary        Hinglish {:,} types / {:,} tokens (TTR {:.3f})".format(
        voc["hinglish_types"], voc["hinglish_tokens"], voc["hinglish_type_token_ratio"]))
    print("  tagger coverage   {:.1%} of word tokens resolved to lang1/lang2".format(cm["tagger_coverage"]))
    print("  CMI               {:.2f} mean, {:.1%} of sentences mixed".format(
        cm["cmi_mean_all"], cm["frac_sentences_mixed"]))
    print("  SPF               {:.4f}   M-index {:.4f}".format(cm["switch_point_fraction"], cm["m_index"]))
    print("  spelling variance {}/{} lexicon groups seen, {} with 2+ spellings, "
          "{:.1%} of their occurrences non-canonical".format(
              sv["groups_observed"], sv["lexicon_groups"], sv["groups_with_2plus_forms"],
              sv["non_canonical_share_overall"]))

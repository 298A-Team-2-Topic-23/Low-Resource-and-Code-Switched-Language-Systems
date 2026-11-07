#!/usr/bin/env python3
"""
Committed sample records for every pipeline stage.  [298-62]

Workbook 2 sections 3.2 to 3.5 each have a rubric line asking for samples from
that stage -- four of the twelve points. `reports/data_statistics.json` carries
the counts but not the records: the attrition table keeps three record *ids* per
filter, which cites a removal without showing one. This script writes the
records themselves.

Usage
-----
  # the real corpus, which is what the report must quote
  python scripts/convert_hinge_pkl.py data/raw/HinGE.pkl data/raw/hinge.csv
  python scripts/emit_stage_samples.py --input data/raw/hinge.csv --seed 42

  # offline, no corpus needed -- proves the path, not a reportable sample set
  python scripts/emit_stage_samples.py --synthetic --n-synthetic 1200 --seed 42

Output goes to reports/samples/<source>/, one Markdown file per stage plus an
index recording which corpus produced them. Selection is deterministic: records
are sorted by id and drawn with a seeded RNG, so set and dict iteration order
cannot leak in and two runs at the same seed produce byte-identical files.

Samples are chosen to include the awkward rows, not only the tidy ones -- the
longest and shortest kept record, one carrying Devanagari, and one from the
largest near-duplicate group -- because a sample set of clean records
misrepresents a corpus whose attrition table is on the facing page.
"""

import argparse
import random
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for entry in (REPO_ROOT / "src", REPO_ROOT / "common"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from lrcs import repo_relative  # noqa: E402
from lrcs.data import clean as clean_stage  # noqa: E402
from lrcs.data import ingest, splits  # noqa: E402
from lrcs.lexicon import DEFAULT_LEXICON, load_variant_groups  # noqa: E402
from lrcs.text import devanagari_fraction, normalise, word_tokens  # noqa: E402

RAW_FIELDS = ("id", "row", "ref", "english", "hindi", "hinglish")
SPLIT_COLUMNS = ("id", "group", "english", "hindi", "hinglish")

# Why each filter exists, for the 3.3 table. Keyed to clean.FILTER_ORDER.
FILTER_REASONS = {
    "missing_field": "english or hinglish empty after normalisation",
    "not_romanized": "Devanagari share of the reference above max_devanagari; "
                     "the task output is Romanised, so a mostly-Devanagari "
                     "reference is mislabelled rather than hard",
    "untranslated": "reference identical to the source under dedup_key -- the "
                    "English was copied through, not translated",
    "length_bounds": "word count outside [min_words, max_words] on either side",
    "length_ratio": "target/source word ratio outside [1/max_ratio, max_ratio]",
    "exact_duplicate": "(source, target) pair already seen",
}

TRANSFORMATIONS = (
    ("Unicode NFC and whitespace collapse",
     "every field, at ingest",
     "one code point sequence per grapheme, so two spellings differ only when "
     "they really differ; applied once so later stages cannot disagree"),
    ("reference-list expansion",
     "the Hinglish cell, at ingest",
     "HinGE ships multiple human references per source sentence in a single "
     "list-literal cell; one record per reference is what supervision needs"),
    ("record id",
     "derived from (english, hinglish)",
     "content-addressed, so a record is citable across runs and machines "
     "without redistributing the text"),
    ("near-duplicate group id",
     "derived at the split stage",
     "the lexicographically smallest key in the cluster, so the id depends on "
     "content alone and not on iteration order"),
    ("split TSV layout",
     "id, group, english, hindi, hinglish",
     "the five columns the model scripts read; hindi is carried so the baseline "
     "reproduction can run its original two-input condition"),
)


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return out


CELL_LIMIT = 160


def cell(value):
    """Markdown-table-safe single line.

    Long cells are truncated: a record rejected by `length_bounds` can run to
    hundreds of words and would make the table unreadable. The word-count
    columns carry the length, so the truncation loses nothing a reader needs.
    """
    text = "" if value is None else str(value)
    if isinstance(value, int) and not isinstance(value, bool):
        text = "{:,}".format(value)
    text = text.replace("|", "\\|").replace("\n", " ")
    if len(text) > CELL_LIMIT:
        text = text[:CELL_LIMIT - 3].rstrip() + "..."
    return text


def pick(records, k, seed):
    """Deterministic sample. Sorted first so set/dict order cannot leak in."""
    ordered = sorted(records, key=lambda r: r["id"])
    if len(ordered) <= k:
        return ordered
    chosen = random.Random(seed).sample(range(len(ordered)), k)
    return [ordered[i] for i in sorted(chosen)]


def notable(kept, group_sizes=None):
    """The awkward rows: longest, shortest, most Devanagari, biggest group."""
    if not kept:
        return OrderedDict()
    ordered = sorted(kept, key=lambda r: r["id"])
    picks = OrderedDict()
    picks["longest hinglish"] = max(
        ordered, key=lambda r: (len(word_tokens(r["hinglish"])), r["id"]))
    picks["shortest hinglish"] = min(
        ordered, key=lambda r: (len(word_tokens(r["hinglish"])), r["id"]))
    with_deva = [r for r in ordered if devanagari_fraction(r["hinglish"]) > 0]
    if with_deva:
        picks["most Devanagari in a kept reference"] = max(
            with_deva, key=lambda r: (devanagari_fraction(r["hinglish"]), r["id"]))
    if group_sizes:
        biggest = max(sorted(group_sizes), key=lambda g: (group_sizes[g], g))
        in_group = [r for r in ordered if r.get("group") == biggest]
        if in_group:
            picks["from the largest near-duplicate group "
                  "({} records)".format(group_sizes[biggest])] = in_group[0]
    return picks


def write(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    print("  {}".format(repo_relative(path)))


def header(title, issue, provenance, extra=()):
    lines = [
        "# {}".format(title),
        "",
        "Generated by `scripts/emit_stage_samples.py` ({}). Do not edit by hand -- "
        "re-run the script.".format(issue),
        "",
        "Corpus: `{}`, SHA-256 `{}`, {:,} rows in file. Cells longer than {} "
        "characters are truncated; the word-count columns carry the real "
        "length.".format(provenance["path"], provenance["sha256"][:16],
                         provenance["rows_in_file"], CELL_LIMIT),
    ]
    if provenance.get("synthetic"):
        lines += [
            "",
            "> **Synthetic corpus.** These samples prove the emitter runs; they are "
            "not a reportable sample set. Regenerate against `data/raw/hinge.csv` "
            "before any report section quotes them.",
        ]
    lines.extend(extra)
    return lines + [""]


# ------------------------------------------------------------------ raw [3.2]
def emit_raw(records, provenance, outdir, seed, n):
    lines = header("Raw records, as ingested", "section 3.2", provenance, extra=[
        "",
        "Straight out of stage 1. Normalisation has been applied (that is part of "
        "ingest) but no filter has run, so rejected rows are still present. "
        "`row` is the line in the source file and `ref` the index of this "
        "reference within that row's reference list.",
    ])
    lines += ["## {} records drawn at seed {}".format(n, seed), ""]
    lines += table(RAW_FIELDS,
                   [[r[f] for f in RAW_FIELDS] for r in pick(records, n, seed)])
    write(outdir / "raw.md", lines)


# --------------------------------------------------- pre-processed [3.3]
def emit_preprocessed(kept, removed, attrition, provenance, outdir, seed, n):
    lines = header("Pre-processed records, with per-filter rejections",
                   "section 3.3", provenance, extra=[
        "",
        "Stage 2 runs six filters in order. Each record is charged to the first "
        "filter that rejects it, so the removal counts below sum to the total "
        "rather than double-counting a record that two rules would catch.",
    ])

    rows = []
    for row in attrition["table"]:
        rows.append([row["filter"], row["in"], row["removed"], row["out"],
                     "{:.2f}%".format(row["pct_removed"]),
                     FILTER_REASONS.get(row["filter"], "")])
    lines += ["## Attrition: {:,} in, {:,} removed, {:,} kept".format(
        attrition["ingested"], attrition["removed_total"], attrition["kept"]), ""]
    lines += table(("filter", "in", "removed", "out", "% removed", "what it rejects"), rows)
    lines += ["", "Thresholds: " + ", ".join(
        "`{}` = {}".format(k, v) for k, v in sorted(attrition["params"].items())), ""]

    lines += ["## What each filter actually removed", ""]
    for name in clean_stage.FILTER_ORDER:
        dropped = removed.get(name, [])
        lines += ["### `{}` -- {:,} removed".format(name, len(dropped)), ""]
        if not dropped:
            lines += ["No record was rejected by this filter on this corpus.", ""]
            continue
        lines += [FILTER_REASONS.get(name, ""), ""]
        lines += table(("id", "english", "hinglish", "en words", "hi words",
                        "Devanagari share"),
                       [[r["id"], r["english"], r["hinglish"],
                         len(word_tokens(r["english"])), len(word_tokens(r["hinglish"])),
                         "{:.2f}".format(devanagari_fraction(r["hinglish"]))]
                        for r in pick(dropped, 2, seed)])
        lines += [""]

    lines += ["## Records that survived, with language tags", "",
              "Stage 2 also tags every token of a kept reference, LinCE-style. "
              "`lang1` is English, `lang2` Romanised Hindi, `ne` a named entity, "
              "`ambiguous` a form valid in both, `unk` unresolved.", ""]
    lines += table(("id", "english", "hinglish", "tags"),
                   [[r["id"], r["english"], r["hinglish"], " ".join(r.get("tags", []))]
                    for r in pick(kept, n, seed)])
    write(outdir / "preprocessed.md", lines)


# ------------------------------------------------- transformed [3.4]
def emit_transformed(records, kept, derived, provenance, outdir, seed, n):
    lines = header("Transformed records", "section 3.4", provenance, extra=[
        "",
        "Every transformation the pipeline applies, each with the reason it "
        "exists. Normalisation here is structural only -- spelling is never "
        "normalised in the corpus, because orthographic variance is the "
        "phenomenon under study. The metric applies its own normalisation "
        "separately, in `evaluation/run_eval.py`.",
    ])

    lines += ["## Transformations and why", ""]
    lines += table(("transformation", "applied to", "reason"),
                   [[name, where, why] for name, where, why in TRANSFORMATIONS])
    lines += [""]

    lines += ["## Whitespace and NFC normalisation, before and after", ""]
    changed = [r for r in sorted(records, key=lambda r: r["id"])
               if normalise(r["hinglish"]) != r["hinglish"]]
    if changed:
        lines += table(("id", "before", "after"),
                       [[r["id"], repr(r["hinglish"]), repr(normalise(r["hinglish"]))]
                        for r in pick(changed, 3, seed)])
    else:
        lines += ["Normalisation is applied inside stage 1, so by the time a "
                  "record exists it is already normalised and no before/after "
                  "pair survives to be shown here. The transformation is "
                  "evidenced by `tests/` instead; see `lrcs.text.normalise`."]
    lines += [""]

    by_row = OrderedDict()
    for r in sorted(records, key=lambda r: (r["row"], r["ref"])):
        by_row.setdefault(r["row"], []).append(r)
    multi = [rows for rows in by_row.values() if len(rows) > 1]
    lines += ["## Reference-list expansion: one source row to many records", ""]
    if multi:
        group = max(multi, key=len)
        lines += ["Source row {} carries {} human references, so it becomes {} "
                  "records sharing one English source.".format(
                      group[0]["row"], len(group), len(group)), ""]
        lines += table(("id", "ref", "english", "hinglish"),
                       [[r["id"], r["ref"], r["english"], r["hinglish"]] for r in group])
    else:
        lines += ["No source row in this corpus carries more than one reference."]
    lines += [""]

    lines += ["## The split TSV layout the model scripts read", "",
              "`" + "\t".join(SPLIT_COLUMNS) + "` -- {} columns.".format(
                  len(SPLIT_COLUMNS)), ""]
    train = derived.get("train", [])
    lines += table(SPLIT_COLUMNS,
                   [[r[c] for c in SPLIT_COLUMNS] for r in pick(train, n, seed)])
    write(outdir / "transformed.md", lines)


# ---------------------------------------------------- prepared [3.5]
def emit_prepared(derived, info, provenance, outdir, seed, n):
    total = sum(len(v) for v in derived.values())
    lines = header("Prepared splits", "section 3.5", provenance, extra=[
        "",
        "Stage 3 assigns whole near-duplicate groups, never individual records, "
        "so paraphrases of one source sentence cannot straddle a split. That is "
        "why the shares below are not exactly 80/10/10: a group cannot be "
        "divided to hit a target.",
    ])
    lines += table(("split", "records", "% of total", "unique sources", "groups"),
                   [[name,
                     "{:,}".format(len(records)),
                     "{:.2f}%".format(100.0 * len(records) / total) if total else "0%",
                     "{:,}".format(len({r["english"] for r in records})),
                     "{:,}".format(len({r["group"] for r in records}))]
                    for name, records in derived.items()])
    lines += ["",
              "Grouping: {:,} unique sources in {:,} groups, {} near-duplicate "
              "pair(s) merged.".format(info.get("unique_sources", 0),
                                       info.get("groups", 0),
                                       info.get("near_duplicate_pairs", 0)),
              ""]
    for name, records in derived.items():
        lines += ["## {} -- {} of {:,} records, seed {}".format(
            name, min(n, len(records)), len(records), seed), ""]
        lines += table(SPLIT_COLUMNS,
                       [[r[c] for c in SPLIT_COLUMNS] for r in pick(records, n, seed)])
        lines += [""]
    write(outdir / "prepared.md", lines)


# ----------------------------------------------------------------- index
def emit_index(provenance, attrition, derived, outdir, seed, n):
    stages = [
        ["raw", "3.2", "`raw.md`", "{:,}".format(attrition["ingested"]),
         str(len(RAW_FIELDS))],
        ["pre-processed", "3.3", "`preprocessed.md`",
         "{:,}".format(attrition["kept"]), str(len(RAW_FIELDS) + 1)],
        ["transformed", "3.4", "`transformed.md`",
         "{:,}".format(attrition["kept"]), str(len(SPLIT_COLUMNS))],
        ["prepared", "3.5", "`prepared.md`",
         " / ".join("{:,}".format(len(v)) for v in derived.values()),
         str(len(SPLIT_COLUMNS))],
    ]
    lines = header("Stage samples", "298-62", provenance, extra=[
        "",
        "Seed {}, {} records per stage. Selection is deterministic: records are "
        "sorted by id before sampling, so two runs at this seed produce "
        "byte-identical files.".format(seed, n),
        "",
    ])
    lines += table(("stage", "report section", "file", "records", "fields"), stages)
    lines += ["",
              "`fields` counts the fields a record carries at that stage, which is "
              "what the section 3.6 stage table reports as columns. Pre-processed "
              "adds `tags` to the six raw fields; transformed and prepared are the "
              "five-column split TSV.",
              ""]
    write(outdir / "index.md", lines)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="CSV/TSV the pipeline would ingest")
    src.add_argument("--synthetic", action="store_true",
                     help="generate a synthetic corpus (offline; not reportable)")
    p.add_argument("--n-synthetic", type=int, default=1200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-samples", type=int, default=8,
                   help="records per stage; 6-10 is 'sufficient', more is noise")
    p.add_argument("--dup-threshold", type=float, default=0.7)
    p.add_argument("--ratios", type=float, nargs=3, default=[0.8, 0.1, 0.1],
                   metavar=("TRAIN", "DEV", "TEST"))
    p.add_argument("--max-group-frac", type=float, default=0.05)
    p.add_argument("--lexicon", default=str(DEFAULT_LEXICON))
    p.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw"))
    p.add_argument("--out-dir", default=str(REPO_ROOT / "reports" / "samples"))
    return p.parse_args(argv)


def build(args):
    """Run the pipeline stages in memory and write the sample files."""
    lexicon = load_variant_groups(args.lexicon)
    if args.synthetic:
        records, provenance = ingest.ingest_synthetic(
            args.n_synthetic, args.seed, args.raw_dir, lexicon=lexicon)
    else:
        records, provenance = ingest.ingest_file(args.input)

    kept, removed, attrition = clean_stage.partition(records, lexicon=lexicon)
    ratios = OrderedDict(zip(("train", "dev", "test"), args.ratios))
    derived, info = splits.derive_splits(
        kept, ratios, args.dup_threshold, args.seed,
        max_group_frac=args.max_group_frac)

    outdir = Path(args.out_dir) / provenance["source"]
    print("stage samples -> {}".format(repo_relative(outdir)))
    group_sizes = {}
    for records_in_split in derived.values():
        for r in records_in_split:
            group_sizes[r["group"]] = group_sizes.get(r["group"], 0) + 1

    emit_index(provenance, attrition, derived, outdir, args.seed, args.n_samples)
    emit_raw(records, provenance, outdir, args.seed, args.n_samples)
    emit_preprocessed(kept, removed, attrition, provenance, outdir,
                      args.seed, args.n_samples)
    emit_transformed(records, kept, derived, provenance, outdir,
                     args.seed, args.n_samples)
    emit_prepared(derived, info, provenance, outdir, args.seed, args.n_samples)

    extras = notable(
        [r for split in derived.values() for r in split], group_sizes)
    if extras:
        lines = header("Edge cases", "298-62", provenance, extra=[
            "",
            "Deliberately not a random draw. A sample set of tidy records "
            "misrepresents a corpus whose attrition table sits on the facing "
            "page, so these are the rows that strain each assumption.",
            "",
        ])
        lines += table(("why it is here", "id", "english", "hinglish"),
                       [[why, r["id"], r["english"], r["hinglish"]]
                        for why, r in extras.items()])
        write(outdir / "edge_cases.md", lines)
    return outdir


def main(argv=None):
    args = parse_args(argv)
    try:
        build(args)
    except ingest.IngestError as exc:
        print("ingest failed: {}".format(exc), file=sys.stderr)
        return 2
    except splits.SplitError as exc:
        print("split failed: {}".format(exc), file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())

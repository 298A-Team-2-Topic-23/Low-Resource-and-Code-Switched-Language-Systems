#!/usr/bin/env python3
"""
Turn the frozen splits into English-to-Hinglish supervision for MLX LoRA.

Reads the split TSVs that `scripts/run_pipeline.py` wrote, and emits the
chat-format JSONL that `mlx_lm.lora` consumes. It does not re-split anything:
the splits are frozen under SHA-256 in
`data/processed/manifests/hinge_split_manifest.json`, and a training script that
drew its own splits would make every reported number incomparable with the
leakage check.

What it guarantees
------------------
1. **The frozen manifest is the authority.** Record counts and ids are checked
   against it, and the run aborts on a mismatch rather than training on a split
   that is not the one the leakage gate cleared.
2. **Splits read as a true TSV.** `quoting=csv.QUOTE_NONE`, for the reason
   `tests/test_tsv_quoting.py` documents: the default quote character silently
   merged 212 records.
3. **One prompt, fixed and recorded.** The instruction text is written into the
   output manifest, because changing the prompt changes the measurement and a
   prompt that lives only in a shell history is not reproducible.
4. **Multiple references stay multiple rows in training and collapse to a
   reference set in test.** HinGE gives up to eight human renderings of one
   English sentence. For training, each is a legitimate target. For scoring,
   they are alternatives to the *same* source, so chrF++ must see them as a
   reference set; scoring one row per reference would reward whichever spelling
   the model happened to match and count the others as errors.

Usage
-----
  python3 scripts/build_sft_data.py
  python3 scripts/build_sft_data.py --out-dir data/sft/hinge --max-words 60
"""

import argparse
import csv
import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

MANIFEST = REPO_ROOT / "data" / "processed" / "manifests" / "hinge_split_manifest.json"
PROCESSED = REPO_ROOT / "data" / "processed" / "hinge"
DEFAULT_OUT = REPO_ROOT / "data" / "sft" / "hinge"

# Fixed at build time and recorded in the output manifest. Hinglish has no
# standard orthography, so the instruction says Roman script explicitly: without
# it the base model answers a third of the time in Devanagari, which is a
# different task and scores near zero on a Romanised reference.
SYSTEM = ("You translate English into Hinglish: conversational Hindi-English "
          "code-mixed text written in the Roman alphabet. Keep common English "
          "words in English. Never use Devanagari script. Reply with the "
          "translation only.")
USER = "Translate to Hinglish:\n{english}"


class BuildError(RuntimeError):
    pass


def read_split(path):
    """QUOTE_NONE is required; see tests/test_tsv_quoting.py."""
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t",
                                   quoting=csv.QUOTE_NONE, quotechar=None))


def load_manifest():
    if not MANIFEST.exists():
        raise BuildError("{}: not found. Run the pipeline first.".format(MANIFEST))
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verify(split, rows, manifest):
    expected = manifest["splits"][split]["records"]
    if len(rows) != expected:
        raise BuildError(
            "{}: read {} records but the frozen manifest records {}. Refusing to "
            "build supervision from a split that is not the one the leakage gate "
            "cleared. Re-run scripts/run_pipeline.py, and if the counts still "
            "disagree the reader is wrong, not the manifest "
            "(see tests/test_tsv_quoting.py).".format(split, len(rows), expected))
    ids = set(manifest["splits"][split]["ids"])
    unknown = {r["id"] for r in rows} - ids
    if unknown:
        raise BuildError("{}: {} record id(s) absent from the manifest, first {}".format(
            split, len(unknown), sorted(unknown)[:3]))


def chat_row(english, hinglish):
    return {"messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER.format(english=english)},
        {"role": "assistant", "content": hinglish},
    ]}


def build(out_dir, max_words=None):
    manifest = load_manifest()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = OrderedDict([
        ("source_manifest", str(MANIFEST.relative_to(REPO_ROOT))),
        ("input_sha256", manifest["input_sha256"]),
        ("system_prompt", SYSTEM),
        ("user_template", USER),
        ("splits", OrderedDict()),
    ])

    # mlx_lm.lora expects train.jsonl / valid.jsonl / test.jsonl
    name_map = {"train": "train", "dev": "valid", "test": "test"}

    for split, out_name in name_map.items():
        rows = read_split(PROCESSED / "{}.tsv".format(split))
        verify(split, rows, manifest)

        usable, dropped_long, dropped_empty = [], 0, 0
        by_source = defaultdict(list)
        for r in rows:
            en, hg = (r["english"] or "").strip(), (r["hinglish"] or "").strip()
            if not en or not hg:
                dropped_empty += 1
                continue
            if max_words and (len(en.split()) > max_words or len(hg.split()) > max_words):
                dropped_long += 1
                continue
            usable.append((r["id"], en, hg))
            by_source[en].append(hg)

        path = out_dir / "{}.jsonl".format(out_name)
        with path.open("w", encoding="utf-8") as fh:
            for _id, en, hg in usable:
                fh.write(json.dumps(chat_row(en, hg), ensure_ascii=False) + "\n")

        entry = OrderedDict([
            ("file", str(path.relative_to(REPO_ROOT))),
            ("manifest_records", manifest["splits"][split]["records"]),
            ("rows_written", len(usable)),
            ("unique_sources", len(by_source)),
            ("dropped_empty", dropped_empty),
            ("dropped_over_max_words", dropped_long),
        ])

        # Scoring needs one entry per SOURCE carrying every reference.
        if split == "test":
            refs_path = out_dir / "test_references.jsonl"
            with refs_path.open("w", encoding="utf-8") as fh:
                for en, refs in by_source.items():
                    fh.write(json.dumps(
                        {"english": en, "references": refs}, ensure_ascii=False) + "\n")
            entry["reference_set_file"] = str(refs_path.relative_to(REPO_ROOT))
            entry["reference_set_sources"] = len(by_source)
            entry["mean_references_per_source"] = round(
                len(usable) / len(by_source), 3) if by_source else 0.0
        report["splits"][split] = entry

    (out_dir / "manifest.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", default=str(DEFAULT_OUT))
    p.add_argument("--max-words", type=int, default=None,
                   help="drop pairs longer than this on either side (the clean "
                        "stage already caps at 60; use this only to shorten "
                        "sequences for a memory-constrained run)")
    args = p.parse_args(argv)

    try:
        report = build(args.out_dir, args.max_words)
    except BuildError as exc:
        print("build refused: {}".format(exc), file=sys.stderr)
        return 2

    print("\nsupervision -> {}".format(args.out_dir))
    print("{:<8} {:>10} {:>10} {:>9} {:>9}".format(
        "split", "manifest", "written", "sources", "dropped"))
    print("-" * 50)
    for split, e in report["splits"].items():
        print("{:<8} {:>10,} {:>10,} {:>9,} {:>9,}".format(
            split, e["manifest_records"], e["rows_written"], e["unique_sources"],
            e["dropped_empty"] + e["dropped_over_max_words"]))
    t = report["splits"]["test"]
    print("\ntest scoring set: {:,} sources, {} references each on average"
          .format(t["reference_set_sources"], t["mean_references_per_source"]))
    print("prompt recorded in {}/manifest.json -- changing it changes the "
          "measurement".format(args.out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())

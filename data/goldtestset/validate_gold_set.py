#!/usr/bin/env python3
"""Validate the three-column team-authored gold-set CSV."""

import argparse
import csv
import sys
from pathlib import Path


REQUIRED_COLUMNS = (
    "item_id",
    "english_source",
    "devanagari_hindi",
    "romanized_hinglish",
    "needs_review",
    "notes",
)


def validate(path, expected_count=None, allow_empty=False):
    errors = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return ["missing CSV header"]
        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            return [f"missing required column(s): {', '.join(missing)}"]
        rows = list(reader)

    if not rows and not allow_empty:
        errors.append("gold set is empty; pass --allow-empty only for the pre-inventory template")
    if expected_count is not None and len(rows) != expected_count:
        errors.append(f"expected {expected_count} rows, found {len(rows)}")

    seen_ids = set()
    seen_sources = set()
    for row_number, row in enumerate(rows, start=2):
        item_id = row["item_id"].strip()
        source = row["english_source"].strip()
        hindi = row["devanagari_hindi"].strip()
        hinglish = row["romanized_hinglish"].strip()
        needs_review = row["needs_review"].strip().lower()

        if not item_id:
            errors.append(f"row {row_number}: item_id is blank")
        elif item_id in seen_ids:
            errors.append(f"row {row_number}: duplicate item_id {item_id!r}")
        seen_ids.add(item_id)
        if not source:
            errors.append(f"row {row_number}: english_source is blank")
        elif source.casefold() in seen_sources:
            errors.append(f"row {row_number}: duplicate english_source")
        seen_sources.add(source.casefold())
        if not hindi:
            errors.append(f"row {row_number}: devanagari_hindi is blank")
        if not hinglish:
            errors.append(f"row {row_number}: romanized_hinglish is blank")
        if needs_review not in {"", "yes", "no", "true", "false", "1", "0"}:
            errors.append(f"row {row_number}: needs_review must be yes/no when present")
        if needs_review in {"yes", "true", "1"} and not row["notes"].strip():
            errors.append(f"row {row_number}: flagged item needs a notes entry")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()
    errors = validate(args.csv_path, args.expected_count, args.allow_empty)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"valid: {args.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
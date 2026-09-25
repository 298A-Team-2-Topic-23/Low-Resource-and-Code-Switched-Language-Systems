#!/usr/bin/env python3
"""Compute Krippendorff's alpha and pairwise agreement for a pilot CSV."""

import argparse
import csv
import itertools
import sys
from collections import Counter, defaultdict


def ordinal_delta(a, b, counts, levels):
    """Krippendorff's ordinal difference function."""
    lo, hi = sorted((levels.index(a), levels.index(b)))
    total = sum(counts[levels[index]] for index in range(lo, hi + 1))
    total -= (counts[a] + counts[b]) / 2
    return total**2


def nominal_delta(a, b, counts, levels):
    return 0.0 if a == b else 1.0


def krippendorff_alpha(units, scale="ordinal"):
    """Return alpha for units containing one value per participating rater."""
    units = [unit for unit in units if len(unit) >= 2]
    if not units:
        raise ValueError("need at least one item scored by two or more raters")

    counts = Counter(value for unit in units for value in unit)
    levels = sorted(counts)
    total_values = sum(counts.values())
    delta = ordinal_delta if scale == "ordinal" else nominal_delta

    observed_numerator = 0.0
    for unit in units:
        denominator = len(unit) - 1
        for a, b in itertools.permutations(unit, 2):
            observed_numerator += delta(a, b, counts, levels) / denominator
    observed = observed_numerator / total_values

    expected_numerator = 0.0
    for a, b in itertools.permutations(levels, 2):
        expected_numerator += counts[a] * counts[b] * delta(a, b, counts, levels)
    for value in levels:
        expected_numerator += counts[value] * (counts[value] - 1) * delta(
            value, value, counts, levels
        )
    expected = expected_numerator / (total_values * (total_values - 1))
    return 1.0 if expected == 0 else 1.0 - observed / expected


def pairwise_exact(rows, raters):
    """Return exact agreement and shared-item count for each rater pair."""
    result = {}
    for first, second in itertools.combinations(raters, 2):
        both = [
            (row[first].strip(), row[second].strip())
            for row in rows
            if row.get(first, "").strip() and row.get(second, "").strip()
        ]
        if both:
            same = sum(first_value == second_value for first_value, second_value in both)
            result[(first, second)] = (same / len(both), len(both))
    return result


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--csv", required=True, help="CSV containing item and rater columns")
    parser.add_argument("--scale", choices=["ordinal", "nominal"], default="ordinal")
    parser.add_argument("--min-score", type=int, default=1)
    parser.add_argument("--max-score", type=int, default=5)
    parser.add_argument("--id-col", default=None, help="ID column; defaults to the first column")
    parser.add_argument(
        "--rater-cols",
        nargs="+",
        default=None,
        help="rater columns; defaults to every column except the ID column",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.min_score >= args.max_score:
        sys.exit("min-score must be lower than max-score")
    with open(args.csv, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        sys.exit("empty csv")

    columns = list(rows[0])
    id_column = args.id_col or columns[0]
    if id_column not in columns:
        sys.exit(f"unknown id column: {id_column}")
    raters = args.rater_cols or [column for column in columns if column != id_column]
    unknown_raters = [rater for rater in raters if rater not in columns]
    if unknown_raters:
        sys.exit(f"unknown rater column(s): {', '.join(unknown_raters)}")
    if len(raters) < 2:
        sys.exit("need at least two rater columns")

    units = []
    skipped = 0
    for row in rows:
        values = []
        for rater in raters:
            value = (row.get(rater) or "").strip()
            if value:
                try:
                    parsed = int(value) if args.scale == "ordinal" else value
                except ValueError:
                    sys.exit(f"non-integer rating for ordinal scale: {value!r}")
                if args.scale == "ordinal" and not args.min_score <= parsed <= args.max_score:
                    sys.exit(
                        f"rating {parsed} is outside the configured range "
                        f"{args.min_score}-{args.max_score}"
                    )
                values.append(parsed)
        if len(values) >= 2:
            units.append(values)
        else:
            skipped += 1

    try:
        alpha = krippendorff_alpha(units, args.scale)
    except ValueError as error:
        sys.exit(str(error))

    print(f"\nfile    : {args.csv}")
    print(f"raters  : {', '.join(raters)}")
    print(f"items   : {len(rows)} ({len(units)} usable, {skipped} with fewer than 2 ratings)")
    print(f"\nKrippendorff's alpha : {alpha:.3f}")
    if alpha >= 0.67:
        verdict = "usable - proceed to the full set"
    elif alpha >= 0.4:
        verdict = "revise the guidelines before authoring 800 items"
    else:
        verdict = "raters are not applying the same standard - retrain on shared examples"
    print(f"verdict : {verdict}")

    print("\npairwise exact agreement")
    for (first, second), (percentage, count) in pairwise_exact(rows, raters).items():
        print(f"  {first} vs {second}: {percentage * 100:.1f}% on {count} shared items")

    spread = defaultdict(int)
    if args.scale == "ordinal":
        for unit in units:
            spread[max(unit) - min(unit)] += 1
    if spread:
        print("\ndisagreement spread (max rating minus min, per item)")
        for difference in sorted(spread):
            label = "point" if difference == 1 else "points"
            print(f"  {difference} {label}: {spread[difference]} items")
        print("\nItems with a spread of 2 or more should be discussed at reconciliation.")


if __name__ == "__main__":
    main()
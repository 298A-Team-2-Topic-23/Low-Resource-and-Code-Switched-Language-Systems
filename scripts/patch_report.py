"""Patch an already-assembled Progress Report 2 docx in place.

Usage:  python scripts/patch_report.py [--doc reports/progress2/T2.A5.docx]

Two jobs:

1. Replace the highlighted "PART C PENDING" placeholder that
   build_progress_report.py writes when docs/progress2/part_c_work.md is absent, now that
   the file exists (Linear 298-48).
2. Re-render the Part A paragraphs listed in CORRECTIONS, which were assembled from an
   earlier revision of docs/progress2/part_a_status.md.

This script exists only because the department template is not committed, so
`build_progress_report.py --template ...` cannot be re-run from a clean clone. Commit the
template and this script becomes unnecessary -- a full rebuild is the canonical route.

Both jobs are idempotent: a paragraph already carrying the new text is skipped.
"""
import argparse
import sys
from pathlib import Path

import docx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_progress_report import add_inline, insert_after, markdown_blocks  # noqa: E402

PLACEHOLDER = "PART C PENDING"

# (text identifying the stale paragraph, replacement Markdown). The replacements are the
# current wording in docs/progress2/part_a_status.md; keep the two in step.
CORRECTIONS = [
    (
        "runs/ contains two pipeline records and no model records",
        "**4.5 First Model Implementation, Complete 25%.** `models/generate_zeroshot.py` "
        "and `models/train_qlora.py` are merged and their CPU paths are tested, and "
        "`runs/` now holds four model records from a Tesla T4. **But no model has been "
        "trained on the real corpus and no scored run exists at three seeds**: those four "
        "records are a single-seed smoke test on synthetic data with a 0.5B stand-in "
        "model, and `docs/COMPUTE_BUDGET.md` states in terms that none of it is a "
        "reportable result. Issues 298-24 and 298-25 were previously marked Done without "
        "a result and were reset to In Progress on 23 October under 298-45. The scored run "
        "is 298-53, due 3 November, and the QLoRA fine-tune at three seeds is 298-54, due "
        "9 November. Both are blocked on GPU confirmation (298-51).",
    ),
    (
        "those six are being reset under 298-45",
        "A row was only marked above 80% on Complete if an artifact exists on `main` that "
        "a reader can open. Issues marked Done on the Linear board without a "
        "corresponding artifact were treated as incomplete. Eight such issues were found "
        "and reset on 23 October under 298-45 — 298-10, 298-15, 298-16, 298-17, "
        "298-21, 298-23, 298-24 and 298-25 — so that Part C, this table and the "
        "repository agree with each other. The audit is recorded in "
        "`docs/progress2/board_reset_298-45.md`.",
    ),
]


def rewrite(par, markdown):
    """Replace a paragraph's content, keeping the paragraph and its style."""
    for run in list(par.runs):
        run._r.getparent().remove(run._r)
    add_inline(par, markdown)


def patch(doc_path: Path, source: Path):
    doc = docx.Document(doc_path)
    changed = []

    target = next((p for p in doc.paragraphs if PLACEHOLDER in p.text), None)
    if target is not None:
        insert_after(target._p, markdown_blocks(doc, source.read_text()))
        target._p.getparent().remove(target._p)
        changed.append(f"Part C from {source.name}")

    for needle, replacement in CORRECTIONS:
        par = next((p for p in doc.paragraphs if needle in p.text), None)
        if par is not None:
            rewrite(par, replacement)
            changed.append(f"corrected: {needle[:40]}...")

    if not changed:
        print(f"{doc_path}: nothing to patch")
        return
    doc.save(doc_path)
    for line in changed:
        print(f"  {line}")
    print(f"wrote {doc_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", type=Path,
                    default=ROOT / "reports" / "progress2" / "T2.A5.docx")
    ap.add_argument("--source", type=Path,
                    default=ROOT / "docs" / "progress2" / "part_c_work.md")
    args = ap.parse_args()
    patch(args.doc, args.source)

"""Pytest path setup for the repository.

Two things are made importable from anywhere in the test suite, so that no
script needs its own sys.path shim:

  * the repository root, so `from human_eval.agreement import ...` and
    `from data.goldtestset.validate_gold_set import ...` resolve without
    __init__.py files or an installed package
  * common/, so `from repro import set_seed, RunLogger` resolves the same way
    it does when a training script is run directly from the repo root

Without this, test collection depends on pytest's rootdir insertion happening
to put the right directory on the path, which is not something to rely on when
the suite is the gate on a graded reproducibility claim.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for path in (ROOT, ROOT / "common"):
    entry = str(path)
    if entry not in sys.path:
        sys.path.insert(0, entry)

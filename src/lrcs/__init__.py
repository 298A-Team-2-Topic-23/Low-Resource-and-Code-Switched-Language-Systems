"""Low-Resource and Code-Switched Language Systems -- importable package.

Lives under src/ and is not installed. scripts/run_pipeline.py puts src/ on the
path itself, and conftest.py does the same for the test suite, so neither the
demo nor the tests depend on anyone remembering PYTHONPATH=src.
"""

from pathlib import Path

__version__ = "0.1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_relative(path):
    """Path as written into committed outputs: relative to the repo root when it
    is inside the repo, so manifests and statistics carry no machine-specific
    absolute paths."""
    if path is None:
        return None
    p = Path(path).resolve()
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)

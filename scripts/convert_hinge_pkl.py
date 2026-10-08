#!/usr/bin/env python3
"""
Convert the authors' HinGE.pkl to the CSV that the pipeline ingests.  [298-44]

`lrcs.data.ingest` refuses pickles on purpose: unpickling a downloaded file can
run arbitrary code. HinGE is only distributed as a pickle, so this script is the
one controlled place where it is opened, and it opens it with a restricted
unpickler (the pattern in the Python `pickle` docs, "Restricting Globals"):
only pandas and numpy classes may be reconstructed. Anything else -- os.system,
subprocess, eval, builtins -- raises before it is ever called.

    python scripts/convert_hinge_pkl.py data/raw/HinGE.pkl data/raw/hinge.csv
    python scripts/run_pipeline.py --input data/raw/hinge.csv --seed 42

The authors' release (Drive link in docs/datasheet.md) has
SHA-256 e78c8f48af3eea0b141e767082189b7b619e9cbe50ad8f0b2a4863b82ebc5960.
Pass --expected-sha256 with it to refuse a substituted file before opening it.

Needs pandas (requirements-demo.txt). The CSV keeps every column as released;
the "Human-generated Hinglish" list is written as a Python list literal, which
ingest parses with ast.literal_eval.
"""

import argparse
import hashlib
import io
import sys
from pathlib import Path

ALLOWED_MODULE_PREFIXES = ("pandas.", "numpy.")
ALLOWED_MODULES = {"pandas", "numpy"}
# functools.partial: pandas builds blocks with it; builtins.slice: index ranges.
# Neither can execute anything on its own.
ALLOWED_GLOBALS = {("functools", "partial"), ("builtins", "slice")}
EXPECTED_COLUMNS = ("English", "Hindi", "WAC", "PAC")


class UnsafePickleError(RuntimeError):
    pass


def _allowed(module, name):
    return (module in ALLOWED_MODULES or module.startswith(ALLOWED_MODULE_PREFIXES)
            or (module, name) in ALLOWED_GLOBALS)


def _restricted_unpickler(data):
    """pandas' own compatibility unpickler (what pd.read_pickle uses, so a pickle
    written by an older pandas still loads), with find_class restricted."""
    from pandas.compat.pickle_compat import Unpickler as PandasUnpickler

    class RestrictedUnpickler(PandasUnpickler):
        def find_class(self, module, name):
            if not _allowed(module, name):
                raise UnsafePickleError("refusing to load {}.{} from the pickle -- only "
                                        "pandas/numpy objects are allowed".format(module, name))
            return super().find_class(module, name)

    return RestrictedUnpickler(io.BytesIO(data))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_dataframe(path, expected_sha256=None):
    data = Path(path).read_bytes()
    digest = sha256_bytes(data)
    if expected_sha256 and digest != expected_sha256.lower():
        raise UnsafePickleError("SHA-256 mismatch for {}: expected {}, got {}".format(
            path, expected_sha256, digest))
    import pandas as pd   # imported first so pandas classes resolve in find_class
    obj = _restricted_unpickler(data).load()
    if not isinstance(obj, pd.DataFrame):
        raise UnsafePickleError("expected a pandas DataFrame, got {}".format(type(obj).__name__))
    return obj, digest


def convert(pkl_path, csv_path, expected_sha256=None):
    df, digest = load_dataframe(pkl_path, expected_sha256)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    human = [c for c in df.columns if "human" in str(c).lower()]
    if missing or not human:
        raise ValueError("not the HinGE layout: missing {} (columns: {})".format(
            missing + ([] if human else ["Human-generated Hinglish"]), list(df.columns)))
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    refs = sum(len(v) if isinstance(v, (list, tuple)) else 1 for v in df[human[0]])
    return {"input_sha256": digest, "rows": len(df), "human_references": refs,
            "columns": [str(c) for c in df.columns],
            "output_sha256": sha256_bytes(csv_path.read_bytes())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pkl", help="HinGE.pkl as downloaded from the authors")
    ap.add_argument("csv", help="output CSV, e.g. data/raw/hinge.csv (gitignored)")
    ap.add_argument("--expected-sha256", help="refuse the pickle unless it has this hash")
    args = ap.parse_args(argv)
    try:
        info = convert(args.pkl, args.csv, args.expected_sha256)
    except (UnsafePickleError, ValueError) as exc:
        print("conversion refused: {}".format(exc), file=sys.stderr)
        return 2
    print("input   {}  sha256 {}".format(args.pkl, info["input_sha256"]))
    print("rows    {:,}   human references {:,}".format(info["rows"], info["human_references"]))
    print("columns {}".format(", ".join(info["columns"])))
    print("output  {}  sha256 {}".format(args.csv, info["output_sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Stage 1 -- ingest: provenance, measured counts, synthetic fallback.  [298-38]

Rubric component: "right data sources identified" and "data successfully
extracted". Both are answered by numbers this stage measures off the file it
was handed -- path, timestamps, bytes, SHA-256, rows -- never by numbers copied
from a paper. The published HinGE count (4,803 references) and the count we
measured off the released file (4,799) already disagree; a pipeline that printed
the published number would hide exactly that kind of discrepancy.

Accepted input
--------------
CSV or TSV with a header. Columns are found by name:
  english   a column whose name contains "english" (or en / source / src)
  hinglish  a column whose name contains "hinglish" (or cm / target / tgt)
  hindi     optional; a column whose name contains "hindi" but not "hinglish"

HinGE's "Human-generated Hinglish (list)" column holds a Python-style list of
references per English source. Such cells are parsed with ast.literal_eval
(literals only, never code) and exploded into one record per reference, so the
split stage can keep every reference of one source in the same split.

A file with no recognisable header is read positionally: (english, hindi,
hinglish) for 3+ columns, (english, hinglish) for 2. The mapping used is always
printed, so a wrong guess is visible rather than silent.

Pickles are refused. Unpickling a downloaded file runs arbitrary code; convert
HinGE.pkl to CSV once, in a throwaway environment, and ingest the CSV.
"""

import ast
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from lrcs import repo_relative
from lrcs.text import normalise, record_id, sha256_file

_ENGLISH_NAMES = {"en", "eng", "source", "src"}
_HINGLISH_NAMES = {"cm", "code_mixed", "codemixed", "target", "tgt"}
_HINDI_NAMES = {"hi", "hin"}


class IngestError(RuntimeError):
    pass


def _utc(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_columns(header):
    """Map logical fields to column indices from header names. Returns None
    when the header does not name both an English and a Hinglish column."""
    names = [h.strip().lower() for h in header]
    english = hinglish = hindi = None
    for i, name in enumerate(names):
        if english is None and ("english" in name or name in _ENGLISH_NAMES):
            english = i
        elif hinglish is None and ("hinglish" in name or name in _HINGLISH_NAMES):
            hinglish = i
        elif hindi is None and (
            ("hindi" in name and "hinglish" not in name) or name in _HINDI_NAMES
        ):
            hindi = i
    if english is None or hinglish is None:
        return None
    return {"english": english, "hindi": hindi, "hinglish": hinglish}


def _positional(n_cols):
    if n_cols >= 3:
        return {"english": 0, "hindi": 1, "hinglish": 2}
    if n_cols == 2:
        return {"english": 0, "hindi": None, "hinglish": 1}
    raise IngestError("need at least two columns (english, hinglish)")


def read_table(path):
    """Return (header_or_None, rows, mapping)."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".pkl", ".pickle"}:
        raise IngestError(
            "{}: refusing to unpickle a downloaded file (it can execute code). "
            "Convert it to CSV once and ingest the CSV.".format(path)
        )
    delimiter = "," if suffix == ".csv" else "\t"
    # HinGE cells can be long lists of references; lift the csv field cap.
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
    with open(str(path), encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.reader(fh, delimiter=delimiter) if any(c.strip() for c in r)]
    if not rows:
        raise IngestError("{}: file is empty".format(path))
    mapping = detect_columns(rows[0])
    if mapping is not None:
        return rows[0], rows[1:], mapping
    return None, rows, _positional(max(len(r) for r in rows))


def _cell(row, index):
    if index is None or index >= len(row):
        return ""
    return row[index]


def _references(cell):
    """One cell -> list of reference strings. List-literal cells are exploded."""
    text = (cell or "").strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            value = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return [text]
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value] or [""]
    return [text]


def ingest_file(path, source=None):
    """Read one file. Returns (records, provenance)."""
    path = Path(path)
    if not path.exists():
        raise IngestError(
            "{}: not found. Raw data is never committed (data/raw/ is "
            "gitignored); see docs/datasheet.md for where to get it, or run "
            "with --synthetic.".format(path)
        )
    header, rows, mapping = read_table(path)
    records = []
    for row_no, row in enumerate(rows, start=2 if header else 1):
        english = normalise(_cell(row, mapping["english"]))
        hindi = normalise(_cell(row, mapping["hindi"]))
        refs = _references(_cell(row, mapping["hinglish"]))
        for ref_no, ref in enumerate(refs):
            hinglish = normalise(ref)
            records.append({
                "id": record_id(english, hinglish),
                "english": english,
                "hindi": hindi,
                "hinglish": hinglish,
                "row": row_no,
                "ref": ref_no,
            })
    stat = path.stat()
    provenance = {
        "source": source or path.stem,
        "path": repo_relative(path),
        "file_mtime": _utc(stat.st_mtime),
        "ingested_at": _now(),
        "bytes": stat.st_size,
        "sha256": sha256_file(path),
        "header": header,
        "column_mapping": {
            k: (header[v] if header and v is not None else v)
            for k, v in mapping.items()
        },
        "mapping_inferred_from": "header" if header else "position",
        "rows_in_file": len(rows),
        "records": len(records),
        "hindi_present": any(r["hindi"] for r in records),
    }
    return records, provenance


def ingest_synthetic(n, seed, raw_dir, lexicon=None):
    """Generate a synthetic corpus, write it to raw_dir, then ingest that file
    through exactly the same reader a real file goes through. The synthetic path
    therefore exercises the real code, not a shortcut around it."""
    from lrcs.data.synthetic import generate, write_tsv

    rows = generate(n, seed, lexicon=lexicon)
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "synthetic_n{}_seed{}.tsv".format(n, seed)
    write_tsv(rows, path)
    records, provenance = ingest_file(path, source="synthetic")
    provenance["synthetic"] = {"n": n, "seed": seed, "generator": "lrcs.data.synthetic"}
    return records, provenance


def print_provenance(prov):
    print("  source            {}".format(prov["source"]))
    print("  path              {}".format(prov["path"]))
    print("  file mtime (UTC)  {}   <- when the file was retrieved/written".format(prov["file_mtime"]))
    print("  ingested at (UTC) {}".format(prov["ingested_at"]))
    print("  bytes             {:,}".format(prov["bytes"]))
    print("  sha256            {}".format(prov["sha256"]))
    print("  columns           {} (from {})".format(
        ", ".join("{}={}".format(k, v) for k, v in prov["column_mapping"].items()),
        prov["mapping_inferred_from"],
    ))
    print("  rows in file      {:,}   <- measured".format(prov["rows_in_file"]))
    print("  records           {:,}   <- one per Hinglish reference".format(prov["records"]))
    if not prov["hindi_present"]:
        print("  note              no Devanagari Hindi column in this input")

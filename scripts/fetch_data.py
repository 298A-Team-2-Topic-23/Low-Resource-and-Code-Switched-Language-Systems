#!/usr/bin/env python3
"""
Fetch the real raw datasets this project is built on.  [298A phase 3]

Why this script exists
----------------------
Until now `data/raw/` held one file: a seeded synthetic TSV. Meanwhile
`data/processed/manifests/hinge_split_manifest.json` committed SHA-256 hashes
for three HinGE split files, and Workbook 2 section 4.4 pinned the primary
metric to "the HinGE test split". None of it could be regenerated on a clean
clone, because the corpus was never in the repository and had no recorded
download location. This script closes that hole: every dataset the project
cites is fetched here, from a pinned revision, with its hash and licence
recorded.

What it guarantees
------------------
1. **Pinned revisions.** Each file is fetched at an explicit commit SHA, not
   from `main`. A dataset that changes upstream cannot silently change our
   numbers; the fetch fails the hash check instead.
2. **Recorded provenance.** `data/raw/MANIFEST.json` records, per file, the
   URL, the revision, the byte count, the SHA-256, the licence and the
   citation. That manifest is committed; the data itself is not, because
   `.gitignore` excludes `data/raw/` and redistributing a corpus is not ours
   to do.
3. **No unlicensed data.** A dataset with no `licence` field is refused rather
   than downloaded. Section 3.2 has to state the licence of every source, and
   a source we cannot licence is a source we cannot use.

Usage
-----
  python3 scripts/fetch_data.py                 # fetch everything
  python3 scripts/fetch_data.py --only hinge    # one dataset
  python3 scripts/fetch_data.py --verify        # re-check hashes, no download
  python3 scripts/fetch_data.py --samples       # also write the 3.2 sample tables

Standard library only, so it runs on a bare clone before any virtualenv exists.
"""

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
MANIFEST = RAW / "MANIFEST.json"

HF = "https://huggingface.co/datasets/{repo}/resolve/{rev}/{path}"

# Revisions pinned 10 November 2026. To move a dataset forward, change the
# revision here and re-run; the hash check will report what changed.
DATASETS = {
    "hinge": {
        "repo": "LingoIITGN/HinGE",
        "rev": "e25a10382d9adb77f3a4f03b721fbd0a43c0de4c",
        "files": {"HinGE.csv": "hinge/HinGE.csv"},
        "licence": "CC-BY-4.0",
        "homepage": "https://huggingface.co/datasets/LingoIITGN/HinGE",
        "citation": (
            "Srivastava, V. and Singh, M. (2021). HinGE: A Dataset for Generation "
            "and Evaluation of Code-Mixed Hinglish Text. Eval4NLP 2021, 200-208. "
            "https://aclanthology.org/2021.eval4nlp-1.20"
        ),
        "role": (
            "Primary corpus. English / Devanagari Hindi / human Hinglish, plus "
            "WAC and PAC rule-based outputs with 1-10 quality ratings. Supplies "
            "the Devanagari slice requirement AI-6 names and the three-column "
            "structure the gold set was specified as."
        ),
        "note": (
            "docs/datasheet.md recorded this licence as 'Unstated; inherits IIT "
            "Bombay's terms at minimum / non-commercial (inferred) / unresolved'. "
            "The authors' own lab (Lingo Research Group, IIT Gandhinagar) "
            "publishes it as CC-BY-4.0. The datasheet is corrected accordingly."
        ),
    },
    "phinc": {
        "repo": "veezbo/phinc",
        "rev": "a50e9b699599284036f934b3f5ccc42baa6724b7",
        "files": {
            "hinglish_english_parallel_corpus.csv":
                "phinc/hinglish_english_parallel_corpus.csv"
        },
        "licence": "CC-BY-4.0",
        "homepage": "https://huggingface.co/datasets/veezbo/phinc",
        "citation": (
            "Srivastava, V. and Singh, M. (2020). PHINC: A Parallel Hinglish "
            "Social Media Code-Mixed Corpus for Machine Translation. WNUT 2020. "
            "https://aclanthology.org/2020.wnut-1.7 "
            "Original release: https://zenodo.org/record/3605597"
        ),
        "role": (
            "Scale. 13,738 code-mixed Hinglish sentences with human-written "
            "English translations. Reversed, it is English-to-Hinglish training "
            "data. It is also the official MixMT Subtask-2 training set, so it "
            "shares the lineage this project already cites."
        ),
    },
    "cmu_dog": {
        "repo": "festvox/cmu_hinglish_dog",
        "rev": "19796c6fb32020154cb2745d48704fa73e29b17d",
        "files": {
            "data/train-00000-of-00001.parquet": "cmu_dog/train.parquet",
            "data/validation-00000-of-00001.parquet": "cmu_dog/validation.parquet",
            "data/test-00000-of-00001.parquet": "cmu_dog/test.parquet",
        },
        "licence": "CC-BY-SA-3.0 and GFDL",
        "homepage": "https://huggingface.co/datasets/festvox/cmu_hinglish_dog",
        "citation": (
            "Zhou, Y., Kang, Y. and Black, A. W. (2018). A Dataset for Document "
            "Grounded Conversations. EMNLP 2018. Hinglish version distributed by "
            "CMU Festvox and used as the English-to-Hinglish machine translation "
            "task in GLUECoS (Khanuja et al., ACL 2020)."
        ),
        "role": (
            "Baseline reproduction surface. This is the GLUECoS "
            "English-to-Hinglish MT task: published numbers exist and the data "
            "is downloadable, with train/validation/test splits already fixed "
            "upstream. It replaces the MixMT Subtask-1 gate, whose test set was "
            "never released (the WMT22 task page still reads 'Test phase -- TBD')."
        ),
    },
    "trilingual": {
        "repo": "debajyotimaz/trilingual-hinglish-corpus",
        "rev": "ea41ce29c5bb28de330b0abb5768fa5b06a4bb70",
        "files": {
            "data/train-00000-of-00001.parquet": "trilingual/train.parquet",
            "data/test-00000-of-00001.parquet": "trilingual/test.parquet",
        },
        "licence": "CC-BY-NC-SA-4.0",
        "homepage": (
            "https://huggingface.co/datasets/debajyotimaz/trilingual-hinglish-corpus"
        ),
        "citation": (
            "Mazumder, D., Pathak, D., Kodali, P. and Patro, J. (2026). Neither "
            "Here Nor There: Cross-Lingual Representation Dynamics of Code-Mixed "
            "Text in Multilingual Encoders. Findings of EMNLP 2026. "
            "https://arxiv.org/abs/2603.19771"
        ),
        "role": (
            "Second three-column source: 21,139 English / Devanagari Hindi / "
            "Romanised Hinglish triples."
        ),
        "note": (
            "Its own documentation lists PHINC among its sources, so it overlaps "
            "the training corpus above. The section 3.5 leakage check must "
            "therefore run ACROSS datasets, not only across splits. A "
            "within-split check alone would report a clean result that is false."
        ),
        "licence_warning": (
            "NC and SA. Non-commercial use only, and derivatives share alike. "
            "Keep any artefact derived from it separable from the CC-BY-4.0 work."
        ),
    },
}

CHUNK = 1 << 16
RETRIES = 3


class FetchError(RuntimeError):
    pass


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def download(url, dest):
    """Fetch to a temporary file, then move. A partial download must never be
    left where the next run would hash it and call it good."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "lrcs-fetch-data/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, \
                    open(tmp, "wb") as out:
                while True:
                    block = resp.read(CHUNK)
                    if not block:
                        break
                    out.write(block)
            tmp.replace(dest)
            return dest.stat().st_size
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last = exc
            if tmp.exists():
                tmp.unlink()
            if attempt < RETRIES:
                time.sleep(2 * attempt)
    raise FetchError("{}: {}".format(url, last))


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"generated": None, "datasets": {}}


def write_manifest(manifest):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    manifest["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["note"] = (
        "Hashes and licences for the raw corpora. The data itself is not "
        "committed (.gitignore excludes data/raw/); this manifest is what makes "
        "the fetch reproducible and auditable. Regenerate with "
        "scripts/fetch_data.py, re-check with --verify."
    )
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def fetch_one(name, spec, manifest, verify_only):
    if not spec.get("licence"):
        raise FetchError(
            "{}: no licence recorded. Section 3.2 must state the licence of "
            "every source, so an unlicensed dataset is refused rather than "
            "downloaded.".format(name))

    entry = manifest["datasets"].setdefault(name, {})
    entry.update({k: spec[k] for k in ("repo", "rev", "licence", "homepage",
                                       "citation", "role") if k in spec})
    for k in ("note", "licence_warning"):
        if k in spec:
            entry[k] = spec[k]
    files = entry.setdefault("files", {})

    results = []
    for remote, local in spec["files"].items():
        dest = RAW / local
        url = HF.format(repo=spec["repo"], rev=spec["rev"], path=remote)
        known = files.get(local, {}).get("sha256")

        if verify_only:
            if not dest.exists():
                results.append((local, "MISSING", 0))
                continue
            actual = sha256_of(dest)
            state = "ok" if known == actual else ("recorded" if not known
                                                  else "CHANGED")
            results.append((local, state, dest.stat().st_size))
            continue

        if dest.exists() and known and sha256_of(dest) == known:
            results.append((local, "cached", dest.stat().st_size))
            continue

        size = download(url, dest)
        actual = sha256_of(dest)
        if known and known != actual:
            raise FetchError(
                "{}: {} downloaded clean but its hash changed.\n  recorded {}\n"
                "  now      {}\nA pinned revision should be byte-stable. Either "
                "the pin moved or the upstream file was rewritten; resolve that "
                "before trusting any number measured on it.".format(
                    name, local, known, actual))
        files[local] = {
            "url": url,
            "bytes": size,
            "sha256": actual,
            "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        results.append((local, "fetched", size))
    return results


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--only", action="append", choices=sorted(DATASETS),
                   help="fetch just this dataset (repeatable)")
    p.add_argument("--verify", action="store_true",
                   help="re-hash what is on disk; download nothing")
    args = p.parse_args(argv)

    wanted = args.only or sorted(DATASETS)
    manifest = load_manifest()
    failures, rows = [], []

    for name in wanted:
        try:
            for local, state, size in fetch_one(
                    name, DATASETS[name], manifest, args.verify):
                rows.append((name, local, state, size))
        except FetchError as exc:
            failures.append((name, exc))

    if not args.verify:
        write_manifest(manifest)

    width = max([len(r[1]) for r in rows] or [20])
    print("\n{:<12} {:<{w}} {:<9} {:>10}".format(
        "dataset", "file", "state", "bytes", w=width))
    print("-" * (12 + width + 22))
    for name, local, state, size in rows:
        print("{:<12} {:<{w}} {:<9} {:>10,}".format(
            name, local, state, size, w=width))

    total = sum(r[3] for r in rows)
    print("\n{:,} bytes across {} files".format(total, len(rows)))
    if not args.verify:
        print("manifest -> {}".format(MANIFEST.relative_to(REPO_ROOT)))

    bad = [r for r in rows if r[2] in ("CHANGED", "MISSING")]
    if bad:
        print("\n{} file(s) failed verification:".format(len(bad)))
        for name, local, state, _ in bad:
            print("  {:<12} {:<{w}} {}".format(name, local, state, w=width))

    for name, exc in failures:
        print("\n{} FAILED: {}".format(name, exc), file=sys.stderr)

    nc = [n for n in wanted if "NC" in DATASETS[n]["licence"]]
    if nc and not args.verify:
        print("\nNon-commercial sources fetched: {}. Anything derived from them "
              "stays non-commercial and share-alike; keep it separable from the "
              "CC-BY-4.0 work.".format(", ".join(nc)))

    return 1 if (failures or bad) else 0


if __name__ == "__main__":
    sys.exit(main())

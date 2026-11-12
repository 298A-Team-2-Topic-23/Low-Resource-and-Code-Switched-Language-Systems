"""Tests for the synthetic-data contamination check (298-58, shared with 298-76).

The check exists to stop an evaluation sentence reaching training through an
outside corpus. Each test plants one kind of contamination and checks it is
caught, plus the two properties that make the result trustworthy: it reads the
threshold from the frozen manifest, and it refuses split files that are not
the frozen ones.
"""

import json
import sys
from collections import OrderedDict
from pathlib import Path

import numpy
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lrcs.data import contamination  # noqa: E402

SOURCES = OrderedDict([
    ("train", [("The farmers harvested the wheat before the monsoon arrived.", "किसानों ने गेहूं काटा")]),
    ("dev", [("Please submit the application form before the end of the month.", "कृपया आवेदन जमा करें")]),
    ("test", [("The committee will meet again on Monday to review the annual budget.",
               "समिति सोमवार को फिर मिलेगी")]),
])


@pytest.fixture
def index():
    return contamination.ContaminationIndex(SOURCES, threshold=0.7, seed=42)


def test_exact_match_on_test_is_removed(index):
    pairs = [("the committee will meet again on monday to review the annual budget!", "कुछ और")]
    kept, report = contamination.check_pairs(pairs, index)
    assert kept == []
    assert report["hits"]["exact"]["test"] == 1


def test_near_duplicate_on_dev_is_removed(index):
    pairs = [("Please submit the application forms before the end of this month.", "अलग वाक्य")]
    kept, report = contamination.check_pairs(pairs, index)
    assert kept == []
    assert report["hits"]["near"]["dev"] == 1


def test_hindi_side_match_is_removed_even_with_different_english(index):
    # The real case: two English translations of one Hindi verse. English
    # Jaccard misses it; the Hindi side does not.
    pairs = [("A board shall convene once more on the first weekday.", "समिति सोमवार को फिर मिलेगी")]
    kept, report = contamination.check_pairs(pairs, index)
    assert kept == []
    assert report["hits"]["hindi_exact"]["test"] == 1


def test_train_overlap_is_counted_but_kept(index):
    pairs = [("The farmers harvested the wheat before the monsoon arrived.", "x")]
    kept, report = contamination.check_pairs(pairs, index)
    assert kept == [0]
    assert report["hits"]["exact"]["train"] == 1


def test_unrelated_pair_is_kept(index):
    kept, report = contamination.check_pairs([("Rivers carry sediment to the delta.", "नदियाँ")], index)
    assert kept == [0] and report["removed"] == 0


def test_gate_halts_on_any_protected_hit(index):
    with pytest.raises(contamination.ContaminationError):
        contamination.gate([("The committee will meet again on Monday to review the annual budget.", "")],
                           index)
    assert contamination.gate([("Rivers carry sediment to the delta.", "")], index)["passed"]


def _write_splits(root, threshold=0.65):
    from lrcs.text import sha256_file
    split_dir = root / "processed" / "toy"
    split_dir.mkdir(parents=True)
    manifest = {"source": "toy", "params": {"dup_threshold": threshold}, "splits": {}}
    for name, pairs in SOURCES.items():
        path = split_dir / "{}.tsv".format(name)
        lines = ["id\tgroup\tenglish\thindi\thinglish"]
        lines += ["i{}\tg\t{}\t{}\th".format(k, e, h) for k, (e, h) in enumerate(pairs)]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        manifest["splits"][name] = {"sha256": sha256_file(path)}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root / "manifest.json", root / "processed"


def test_threshold_comes_from_the_manifest(tmp_path):
    manifest, processed = _write_splits(tmp_path, threshold=0.65)
    threshold, sources = contamination.load_split_sources(manifest, processed)
    assert threshold == 0.65
    assert sources["test"][0][0].startswith("The committee")


def test_modified_split_is_refused(tmp_path):
    manifest, processed = _write_splits(tmp_path)
    test_file = processed / "toy" / "test.tsv"
    test_file.write_text(test_file.read_text(encoding="utf-8") + "x\tg\textra\t\th\n", encoding="utf-8")
    with pytest.raises(contamination.ContaminationError, match="frozen split"):
        contamination.load_split_sources(manifest, processed)


def _pyarrow_too_old_for_numpy():
    """The installed pyarrow's major version, read WITHOUT importing pyarrow.

    This has to answer before the import, not after. pyarrow before 14 was built
    against numpy 1.x headers; paired with numpy 1.26 the mismatch kills the
    interpreter at shutdown, so the suite prints a full green run and then exits
    139. The damage is done by the import itself, which is why an earlier version
    of this guard -- importorskip first, check the version second -- still
    crashed: it skipped the body after already loading the library.

    importlib.metadata reads the installed distribution's metadata off disk and
    never loads the module, so an incompatible pyarrow is never brought in.
    """
    try:
        from importlib import metadata
    except ImportError:                       # pragma: no cover - Python < 3.8
        return None
    try:
        version = metadata.version("pyarrow")
    except metadata.PackageNotFoundError:
        return None                           # absent; importorskip will skip
    try:
        return version if int(version.split(".")[0]) < 14 else None
    except ValueError:                        # pragma: no cover - odd version string
        return None


def test_prepare_script_removes_planted_test_source(tmp_path):
    old = _pyarrow_too_old_for_numpy()
    if old is not None:
        pytest.skip(
            "pyarrow {} is ABI-incompatible with numpy {} and segfaults the "
            "interpreter at shutdown; it is not imported here. requirements.txt "
            "pins pyarrow==21.0.0, which runs this test."
            .format(old, numpy.__version__))

    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    import prepare_parallel_corpus as prep

    manifest, processed = _write_splits(tmp_path, threshold=0.7)
    filler = [("Sentence {} talks about rivers and hills and roads today.".format(i),
               "वाक्य {} नदियों पहाड़ों और सड़कों के बारे में बात करता है".format(i)) for i in range(40)]
    planted = ("The committee will meet again on Monday to review the annual budget.",
               "समिति सोमवार को फिर से मिलेगी और बजट देखेगी")
    rows = filler + [planted]
    table = pa.table({"idx": list(range(len(rows))), "src": [e for e, _ in rows],
                      "tgt": [h for _, h in rows]})
    shard = tmp_path / "shard.parquet"
    pq.write_table(table, str(shard))
    out, report = tmp_path / "slice.tsv", tmp_path / "report.json"
    rc = prep.main(["--input", str(shard), "--n", str(len(rows)), "--seed", "1",
                    "--manifest", str(manifest), "--processed-dir", str(processed),
                    "--out", str(out), "--report", str(report)])
    assert rc == 0
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["contamination_check"]["removed"] == 1
    assert data["gate"]["passed"] is True
    assert data["whole_shard_exact_overlap"]["test"]["hinge_sources_found_in_shard"] == 1
    assert "annual budget" not in out.read_text(encoding="utf-8")
    assert "annual budget" not in report.read_text(encoding="utf-8")

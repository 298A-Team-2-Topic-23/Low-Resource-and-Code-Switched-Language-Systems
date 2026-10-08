"""Tests for the four-stage data pipeline (298-38).

Everything runs on synthetic or hand-built records: no network, no raw data,
no GPU. The end-to-end test writes only under pytest's tmp_path.
"""

import importlib.util
import json
from collections import OrderedDict
from pathlib import Path

import pytest

from lrcs.analysis import codemixing
from lrcs.data import clean, ingest, leakage, splits, synthetic
from lrcs.lexicon import load_variant_groups
from lrcs.text import dedup_key, record_id

ROOT = Path(__file__).resolve().parent.parent


def _load_run_pipeline():
    spec = importlib.util.spec_from_file_location("run_pipeline", ROOT / "scripts" / "run_pipeline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rec(english, hinglish, hindi=""):
    return {"id": record_id(english, hinglish), "english": english, "hindi": hindi,
            "hinglish": hinglish, "row": 0, "ref": 0}


# ---------------------------------------------------------------- stage 1

def test_synthetic_is_deterministic():
    assert synthetic.generate(200, 7) == synthetic.generate(200, 7)
    assert synthetic.generate(200, 7) != synthetic.generate(200, 8)
    assert len(synthetic.generate(200, 7)) == 200


def test_ingest_explodes_hinge_list_cells(tmp_path):
    path = tmp_path / "hinge.csv"
    path.write_text(
        'English,Hindi,Human-generated Hinglish (list)\n'
        '"I am going home.",मैं घर जा रहा हूँ।,"[\'main ghar ja raha hoon\', \'mai ghar ja rha hu\']"\n'
        '"Call me.",मुझे फ़ोन करो।,"[\'mujhe call karo\']"\n',
        encoding="utf-8",
    )
    records, prov = ingest.ingest_file(path)
    assert prov["rows_in_file"] == 2
    assert prov["records"] == 3
    assert prov["mapping_inferred_from"] == "header"
    assert [r["hinglish"] for r in records][:2] == ["main ghar ja raha hoon", "mai ghar ja rha hu"]
    assert len(prov["sha256"]) == 64


def test_ingest_refuses_pickles(tmp_path):
    path = tmp_path / "HinGE.pkl"
    path.write_bytes(b"not really a pickle")
    with pytest.raises(ingest.IngestError, match="unpickle"):
        ingest.ingest_file(path)


def test_ingest_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(ingest.IngestError, match="--synthetic"):
        ingest.ingest_file(tmp_path / "nope.csv")


# ---------------------------------------------------------------- stage 2

def test_each_filter_removes_its_own_defect():
    good = _rec("I am going to the market today.", "main aaj market ja raha hoon.")
    records = [
        good,
        _rec("Call me later.", ""),                                           # missing_field
        _rec("I am at home.", "मैं घर पर हूँ।"),                              # not_romanized
        _rec("See you at the station.", "See you at the station!"),           # untranslated
        _rec("Yes.", "haan."),                                                # length_bounds
        _rec("Please send me the report and the invoice and the bill today.",
             "report bhejo."),                                                # length_ratio
        dict(good),                                                           # exact_duplicate
    ]
    kept, attrition = clean.clean(records)
    removed = {row["filter"]: row["removed"] for row in attrition["table"]}
    assert removed == {name: 1 for name in clean.FILTER_ORDER}
    assert [r["id"] for r in kept] == [good["id"]]
    assert attrition["ingested"] - attrition["removed_total"] == attrition["kept"]


def test_tagger_rules():
    markers = clean.hindi_markers()
    tagged = clean.tag_tokens("main aaj market ja raha hoon, Rahul.", "I am going to the market today.", markers)
    tags = dict(tagged)
    assert tags["main"] == "lang2"
    assert tags["market"] == "lang1"          # switched-in word from the source
    assert tags["raha"] == "lang2"
    assert tags[","] == "other"
    assert tags["Rahul"] == "ne"


# ---------------------------------------------------------------- code-mixing

def test_codemixing_known_values():
    tags = ["lang1", "lang2", "other", "lang2", "lang1"]
    assert codemixing.cmi(tags) == pytest.approx(50.0)
    assert codemixing.spf(tags) == pytest.approx(2 / 3)
    assert codemixing.m_index(tags) == pytest.approx(1.0)
    assert codemixing.cmi(["lang2", "lang2", "unk"]) == 0.0
    assert codemixing.spf(["lang2"]) is None


# ---------------------------------------------------------------- stage 3

def test_near_duplicates_are_grouped_and_unrelated_are_not():
    keys = sorted({
        dedup_key("I am going to the office today."),
        dedup_key("So I am going to the office today."),
        dedup_key("The printer at the clinic was really noisy."),
    })
    pairs = splits.near_duplicate_pairs(keys, threshold=0.7)
    assert len(pairs) == 1
    i, j, sim = pairs[0]
    assert {keys[i], keys[j]} == {dedup_key("I am going to the office today."),
                                  dedup_key("So I am going to the office today.")}
    assert sim >= 0.7


def _synthetic_clean(n=600, seed=3):
    rows = synthetic.generate(n, seed)
    records = [_rec(en, hi, hd) for en, hd, hi in rows]
    kept, _ = clean.clean(records)
    return kept


def test_splits_are_disjoint_and_keep_references_together():
    kept = _synthetic_clean()
    ratios = OrderedDict([("train", 0.8), ("dev", 0.1), ("test", 0.1)])
    derived, info = splits.derive_splits(kept, ratios, threshold=0.7, seed=42)
    split_of_key = {}
    for name, records in derived.items():
        for r in records:
            key = dedup_key(r["english"])
            assert split_of_key.setdefault(key, name) == name, "source in two splits"
    assert sum(len(v) for v in derived.values()) == len(kept)
    assert leakage.check(derived, threshold=0.7, seed=42)["passed"]


def test_splits_are_reproducible():
    ratios = OrderedDict([("train", 0.8), ("dev", 0.1), ("test", 0.1)])
    a, _ = splits.derive_splits(_synthetic_clean(), ratios, 0.7, seed=42)
    b, _ = splits.derive_splits(_synthetic_clean(), ratios, 0.7, seed=42)
    assert {k: [r["id"] for r in v] for k, v in a.items()} == {k: [r["id"] for r in v] for k, v in b.items()}


def test_degenerate_clustering_halts():
    records = [_rec("I am going to the office today number {}.".format(i),
                    "main aaj office ja raha hoon {}.".format(i)) for i in range(40)]
    ratios = OrderedDict([("train", 0.8), ("dev", 0.1), ("test", 0.1)])
    with pytest.raises(splits.SplitError, match="degenerate"):
        splits.derive_splits(records, ratios, threshold=0.5, seed=1)


def test_leakage_gate_halts_on_exact_and_near_overlap():
    a = _rec("I am going to the market today.", "main aaj market ja raha hoon.")
    b = _rec("I am going to the market today!", "mai aaj market ja rha hu.")
    c = _rec("So I am going to the market today.", "toh main aaj market ja raha hoon.")
    other = _rec("The printer at the clinic was really noisy.", "clinic ka printer bahut noisy tha.")
    with pytest.raises(leakage.LeakageError) as exc:
        leakage.gate(OrderedDict([("train", [a, other]), ("test", [b])]), threshold=0.7)
    assert exc.value.report["exact_overlaps"] == 1
    with pytest.raises(leakage.LeakageError) as exc:
        leakage.gate(OrderedDict([("train", [a, other]), ("test", [c])]), threshold=0.7)
    assert exc.value.report["near_overlaps"] == 1
    assert leakage.gate(OrderedDict([("train", [a]), ("test", [other])]), threshold=0.7)["passed"]


# ---------------------------------------------------------------- end to end

def _dirs(tmp_path):
    return ["--raw-dir", str(tmp_path / "raw"), "--processed-dir", str(tmp_path / "processed"),
            "--manifest-dir", str(tmp_path / "manifests"), "--reports-dir", str(tmp_path / "reports"),
            "--no-run-log"]


def test_pipeline_end_to_end(tmp_path):
    pytest.importorskip("matplotlib")
    run_pipeline = _load_run_pipeline()
    code = run_pipeline.main(["--synthetic", "--n-synthetic", "400", "--seed", "5"] + _dirs(tmp_path))
    assert code == 0
    stats = json.loads((tmp_path / "reports" / "data_statistics.json").read_text(encoding="utf-8"))
    assert stats["synthetic"] is True
    assert stats["leakage_gate"]["passed"] is True
    assert stats["provenance"]["rows_in_file"] == 400
    assert len(stats["attrition"]["table"]) == 6
    assert len(stats["figures"]) == 4
    for path in stats["figures"].values():
        assert Path(path).stat().st_size > 0
    manifest = json.loads((tmp_path / "manifests" / "synthetic_split_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["splits"]) == {"train", "dev", "test"}
    assert all(len(entry["sha256"]) == 64 for entry in manifest["splits"].values())


def test_pipeline_halts_on_injected_leak_and_writes_no_manifest(tmp_path):
    run_pipeline = _load_run_pipeline()
    code = run_pipeline.main(["--synthetic", "--n-synthetic", "400", "--inject-leak", "2", "--no-figures"]
                             + _dirs(tmp_path))
    assert code == 3
    assert not (tmp_path / "manifests" / "synthetic_split_manifest.json").exists()


def test_lexicon_is_available():
    assert len(load_variant_groups()) > 0

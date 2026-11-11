"""Tests for the HinGE reference-count audit (298-77).

The real release is never committed, so a DataFrame in HinGE's layout stands in
for it. Each test plants one defect the audit is meant to detect and checks it
is reported as found rather than ruled out -- an audit that can only ever say
"ruled out" proves nothing.
"""

import json
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import audit_hinge_count as audit  # noqa: E402


def frame(refs):
    n = len(refs)
    return pd.DataFrame({
        "English": ["Sentence number {}.".format(i) for i in range(n)],
        "Hindi": ["वाक्य {}".format(i) for i in range(n)],
        "Human-generated Hinglish": refs,
        "WAC": ["wac {}".format(i) for i in range(n)],
        "PAC": ["pac {}".format(i) for i in range(n)],
    })


def checks_by_name(report):
    return {c["check"]: c for c in report["checks"]}


def test_clean_frame_rules_everything_out():
    report = audit.build_report(frame([["a b", "c d"], ["e f", "g h", "i j"]]), "0" * 64)
    assert report["measured"]["reference_positions"] == 5
    assert all(c["ruled_out"] for c in report["checks"])
    assert report["measured"]["machine_generated_non_empty"] == 4
    assert "not a parsing loss" in report["verdict"]


def test_blank_reference_is_found():
    report = audit.build_report(frame([["a b", "   "], ["c d", "e f"]]), "0" * 64)
    blank = checks_by_name(report)["empty_or_whitespace_references"]
    assert blank["ruled_out"] is False
    assert blank["row_indices"] == [0]
    assert "file-side cause" in report["verdict"]


def test_duplicate_within_row_counts_distinct_lower():
    report = audit.build_report(frame([["a b", "a b", "c d"]]), "0" * 64)
    assert report["measured"]["reference_positions"] == 3
    assert report["measured"]["distinct_references_per_row_summed"] == 2
    assert checks_by_name(report)["duplicate_references_within_a_row"]["row_indices"] == [0]


def test_non_list_cell_is_found():
    report = audit.build_report(frame([["a b", "c d"], "e f"]), "0" * 64)
    assert checks_by_name(report)["cells_not_a_list"]["ruled_out"] is False


def test_single_reference_rows_are_counted():
    report = audit.build_report(frame([["a b"], ["c d", "e f"]]), "0" * 64)
    assert report["measured"]["rows_with_fewer_than_two_references"] == 1


def test_report_holds_no_sentence_text(tmp_path):
    df = frame([["Hinglish reference text kuch", "doosra reference"]])
    path = tmp_path / "HinGE.pkl"
    df.to_pickle(str(path))
    out = tmp_path / "report.json"
    assert audit.main([str(path), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Hinglish reference text kuch" not in text
    assert "Sentence number" not in text
    assert json.loads(text)["measured"]["rows"] == 1


def test_missing_pickle_exits_3(tmp_path):
    assert audit.main([str(tmp_path / "absent.pkl"), "--out", str(tmp_path / "r.json")]) == 3


def _write_dict_pickle(path, mapping):
    import pickle
    path.write_bytes(pickle.dumps(mapping))


def test_hinglisheval_crosscheck_separates_missing_from_corrupted(tmp_path):
    df = frame([["a b", "c d"], ["e f", "g h"]])
    df["English"] = ["The committee will meet again on Monday to review the budget.",
                     "Where the front skin joins the area under it is called the joint."]
    he = tmp_path / "he"
    he.mkdir()
    # One source matches HinGE, one is a one-character corruption of a HinGE
    # source (the real case was "front s4kin"), and one is genuinely absent:
    # only the last should count as missing.
    _write_dict_pickle(he / "train_human_generated.pkl", {
        "The committee will meet again on Monday to review the budget.\n": ["x y", "z w"],
        "Where the front s4kin joins the area under it is called the joint.\n": ["x y", "z w"],
    })
    _write_dict_pickle(he / "test_human_generated.pkl", {
        "A completely different source sentence about rivers.\n": ["p q", "r s"],
    })
    report = audit.build_report(df, "0" * 64, hinglisheval_dir=str(he))
    cross = report["hinglisheval_crosscheck"]
    assert cross["sources_also_in_hinge"] == 1
    assert cross["sources_absent_from_hinge"] == 2
    assert cross["absent_sources_that_are_near_copies_of_a_hinge_source"] == 1
    missing = checks_by_name(report)["source_pairs_missing_from_the_release"]
    assert missing["ruled_out"] is False

"""Tests for the section 3.6 traceability check (298-86)."""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import audit_section_3_6 as audit  # noqa: E402


def _root(tmp_path, kept=4674):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "data_statistics.json").write_text(
        json.dumps({"attrition": {"kept": kept}, "code_mixing": {"tagger_coverage": 0.6816}}),
        encoding="utf-8")
    return tmp_path


CLAIMS = [
    ("| Pre-processed | **4,674**", audit.STATS, audit.S("attrition.kept"), 1, 0),
    ("covering **68.2%**", audit.STATS, audit.S("code_mixing.tagger_coverage"), 100, 1),
]
TEXT = "| Pre-processed | **4,674** | 7 |\nA tagger covering **68.2%** of tokens."


def test_matching_claims_trace(tmp_path):
    results = audit.check(TEXT, _root(tmp_path), CLAIMS)
    assert [r["status"] for r in results] == ["ok", "ok"]


def test_changed_artifact_is_a_mismatch(tmp_path):
    results = audit.check(TEXT, _root(tmp_path, kept=4675), CLAIMS)
    assert results[0]["status"] == "mismatch"
    assert results[0]["artifact_says"] == "4675"


def test_edited_section_is_reported_not_skipped(tmp_path):
    results = audit.check("nothing here", _root(tmp_path), CLAIMS)
    assert {r["status"] for r in results} == {"text_missing"}


def test_every_claim_text_is_in_the_committed_section():
    text = audit.SECTION.read_text(encoding="utf-8")
    missing = [c[0] for c in audit.CLAIMS if c[0] not in text]
    assert missing == []

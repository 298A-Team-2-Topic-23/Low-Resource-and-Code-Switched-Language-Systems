"""Tests for the per-split composition report (298-64).

Section 3.5 quotes this report, so two properties matter: it must describe the
frozen split and nothing else (a split file that no longer matches its manifest
hash is refused), and it must not leak corpus text into a committed file.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_pipeline  # noqa: E402
import split_balance  # noqa: E402


@pytest.fixture(scope="module")
def synthetic_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("balance")
    rc = run_pipeline.main([
        "--synthetic", "--n-synthetic", "400", "--seed", "7",
        "--no-run-log", "--no-figures",
        "--raw-dir", str(root / "raw"),
        "--processed-dir", str(root / "processed"),
        "--manifest-dir", str(root / "manifests"),
        "--reports-dir", str(root / "reports"),
    ])
    assert rc == 0
    return root


def run_balance(root, out):
    return split_balance.main([
        "--source", "synthetic",
        "--processed-dir", str(root / "processed"),
        "--manifest-dir", str(root / "manifests"),
        "--out", str(out),
    ])


def test_report_matches_manifest_counts(synthetic_run, tmp_path):
    out = tmp_path / "balance.json"
    assert run_balance(synthetic_run, out) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    manifest = json.loads(
        (synthetic_run / "manifests" / "synthetic_split_manifest.json").read_text(encoding="utf-8"))
    assert report["stratified"] is False
    assert report["split_files_match_manifest"] is True
    for name in ("train", "dev", "test"):
        assert report["splits"][name]["records"] == manifest["splits"][name]["records"]
        assert report["splits"][name]["unique_sources"] == manifest["splits"][name]["unique_sources"]
        assert report["splits"][name]["groups"] == manifest["splits"][name]["groups"]
    shares = sum(s["share_of_records"] for s in report["splits"].values())
    assert abs(shares - 1.0) < 1e-3


def test_report_carries_no_corpus_text(synthetic_run, tmp_path):
    out = tmp_path / "balance.json"
    assert run_balance(synthetic_run, out) == 0
    text = out.read_text(encoding="utf-8")
    tsv = (synthetic_run / "processed" / "synthetic" / "train.tsv").read_text(encoding="utf-8")
    english = tsv.splitlines()[1].split("\t")[2]
    assert english and english not in text


def test_modified_split_is_refused(synthetic_run, tmp_path):
    # Work on a copy so the module fixture stays intact for the other tests.
    import shutil
    root = tmp_path / "copy"
    shutil.copytree(str(synthetic_run), str(root))
    dev = root / "processed" / "synthetic" / "dev.tsv"
    dev.write_text(dev.read_text(encoding="utf-8") + "x\tx\tx\tx\tx\n", encoding="utf-8")
    assert run_balance(root, tmp_path / "out.json") == 2
    assert not (tmp_path / "out.json").exists()


def test_missing_split_is_refused(tmp_path):
    assert run_balance(tmp_path, tmp_path / "out.json") == 2

"""Tests for scripts/convert_hinge_pkl.py (298-44).

A small DataFrame in HinGE's layout stands in for the real file, which is never
committed. The unsafe-pickle test checks that a payload naming os.system is
refused by the restricted unpickler before anything is called.
"""

import importlib.util
import os
import pickle
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from lrcs.data import ingest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _load_converter():
    spec = importlib.util.spec_from_file_location("convert_hinge_pkl",
                                                  ROOT / "scripts" / "convert_hinge_pkl.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


conv = _load_converter()


def _hinge_like(tmp_path):
    df = pd.DataFrame({
        "English": ["I will call you tomorrow.", "The train is late."],
        "Hindi": ["मैं तुम्हें कल फोन करूंगा।", "ट्रेन लेट है।"],
        "Human-generated Hinglish": [["Main tumhe kal call karunga.", "Mai kal call karunga."],
                                     ["Train late hai."]],
        "WAC": ["Main tumhe kal phone karunga.", "Train deri se hai."],
        "WAC rating1": [7, 6], "WAC rating2": [6, 6],
        "PAC": ["I tumhe kal call karunga.", "The train late hai."],
        "PAC rating1": [4, 5], "PAC rating2": [5, 4],
    })
    path = tmp_path / "HinGE.pkl"
    df.to_pickle(path)
    return path


def test_converted_csv_ingests_with_every_reference(tmp_path):
    info = conv.convert(_hinge_like(tmp_path), tmp_path / "hinge.csv")
    assert (info["rows"], info["human_references"]) == (2, 3)
    records, prov = ingest.ingest_file(tmp_path / "hinge.csv")
    assert prov["rows_in_file"] == 2
    assert len(records) == 3
    assert {r["hinglish"] for r in records} >= {"Main tumhe kal call karunga.", "Train late hai."}


class _Evil:
    def __reduce__(self):
        return (os.system, ("echo should-never-run",))


def test_unsafe_pickle_is_refused_before_execution(tmp_path):
    path = tmp_path / "evil.pkl"
    path.write_bytes(pickle.dumps(_Evil()))
    with pytest.raises(conv.UnsafePickleError):
        conv.load_dataframe(path)
    assert conv.main([str(path), str(tmp_path / "out.csv")]) == 2
    assert not (tmp_path / "out.csv").exists()


def test_hash_mismatch_refused_without_loading(tmp_path):
    with pytest.raises(conv.UnsafePickleError, match="SHA-256 mismatch"):
        conv.load_dataframe(_hinge_like(tmp_path), expected_sha256="0" * 64)

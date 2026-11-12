"""Tests for scripts/model_support_figures.py  [298-67]

The component diagram in section 4.2 claims to be computed from the imports,
so the import resolution is what needs testing, not the pixels.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "model_support_figures", REPO_ROOT / "scripts" / "model_support_figures.py")
msf = importlib.util.module_from_spec(SPEC)
sys.modules["model_support_figures"] = msf
SPEC.loader.exec_module(msf)


@pytest.mark.parametrize("module,names,level,own,expected", [
    ("repro", ["RunLogger"], 0, "models/", "common/repro"),
    ("run_contract", ["ExperimentRun"], 0, "scripts/", "common/repro"),
    ("lrcs", ["repo_relative"], 0, "scripts/", "lrcs"),
    ("lrcs", ["text"], 0, "scripts/", "lrcs.text"),
    ("lrcs.data.splits", ["write_splits"], 0, "scripts/", "lrcs.data"),
    ("lrcs.lexicon", ["load"], 0, "evaluation/", "lrcs.lexicon"),
    ("torch", [], 0, "models/", None),
    ("text", ["normalise"], 2, "lrcs.data", "lrcs.text"),
    ("splits", ["x"], 1, "lrcs.data", "lrcs.data"),
    (None, ["text"], 1, "lrcs", "lrcs.text"),
])
def test_resolve_import(module, names, level, own, expected):
    assert msf.resolve_import(module, names, level, own) == expected


def test_component_of():
    assert msf.component_of(REPO_ROOT / "src/lrcs/data/splits.py") == "lrcs.data"
    assert msf.component_of(REPO_ROOT / "src/lrcs/text.py") == "lrcs.text"
    assert msf.component_of(REPO_ROOT / "src/lrcs/__init__.py") == "lrcs"
    assert msf.component_of(REPO_ROOT / "common/repro.py") == "common/repro"
    assert msf.component_of(REPO_ROOT / "models/train_qlora.py") == "models/"


def test_scan_finds_known_edges_on_a_toy_tree(tmp_path):
    (tmp_path / "src/lrcs/data").mkdir(parents=True)
    (tmp_path / "src/lrcs/__init__.py").write_text("REPO_ROOT = None\n")
    (tmp_path / "src/lrcs/text.py").write_text("from lrcs import REPO_ROOT\n")
    (tmp_path / "src/lrcs/data/__init__.py").write_text("")
    (tmp_path / "src/lrcs/data/clean.py").write_text("from lrcs.text import x\n")
    (tmp_path / "src/lrcs/data/leak.py").write_text("from ..lexicon import y\n")
    (tmp_path / "src/lrcs/lexicon.py").write_text("")
    (tmp_path / "common").mkdir()
    (tmp_path / "common/repro.py").write_text("import torch\n")
    (tmp_path / "models").mkdir()
    (tmp_path / "models/train.py").write_text(
        "import sys\ndef main():\n    from repro import RunLogger\n    import peft\n")

    old = msf.REPO_ROOT
    msf.REPO_ROOT = tmp_path
    try:
        edges, external, files = msf.scan_imports(tmp_path)
    finally:
        msf.REPO_ROOT = old

    assert ("models/", "common/repro") in edges          # import inside a function counts
    assert ("lrcs.data", "lrcs.text") in edges
    assert ("lrcs.data", "lrcs.lexicon") in edges        # relative import resolved
    assert ("lrcs.text", "lrcs") in edges
    assert ("models/", "peft") in external
    assert ("common/repro", "torch") in external
    assert not any(src == dst for src, dst in edges)     # no self-loops


def test_every_component_on_main_has_a_place(tmp_path):
    """The --check guarantee: a new component cannot silently drop off the figure."""
    pytest.importorskip("matplotlib")
    assert msf.main(["--out-dir", str(tmp_path), "--check"]) == 0
    for name in msf.FIGURES.values():
        assert (tmp_path / name).stat().st_size > 10_000
    assert (tmp_path / msf.COMPONENTS_JSON).exists()

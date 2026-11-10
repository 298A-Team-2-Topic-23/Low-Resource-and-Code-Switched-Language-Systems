"""Tests for the Romanisation step and the real-corpus code-mix options (298-76).

Romanisation runs in front of the generator's Devanagari refusal. These tests
pin the rules that matter for Hinglish spelling (schwa deletion, nukta, digits),
the deterministic lexicon choice, that the refusal still fires on anything not
Romanised, and that the generator's contamination gate halts before writing.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lrcs.data import codemix  # noqa: E402
from lrcs.data.transliterate import Romaniser, levenshtein, load_lexicon, rule_romanise  # noqa: E402

FIXTURE = REPO_ROOT / "data" / "codemix" / "parallel_fixture.tsv"


@pytest.mark.parametrize("native, roman", [
    ("समझना", "samajhna"),   # medial schwa deleted in VC_CV
    ("कमल", "kamal"),        # final schwa deleted, medial kept
    ("घर", "ghar"),
    ("लड़का", "ladka"),       # nukta form, final aa shortened
    ("हिंदी", "hindi"),        # anusvara, final ee shortened
    ("किताब", "kitaab"),      # medial long vowel kept
    ("१२३", "123"),          # Devanagari digits
])
def test_rule_romanise(native, roman):
    assert rule_romanise(native) == roman


def test_lexicon_takes_most_attested_and_breaks_ties_alphabetically(tmp_path):
    lex = tmp_path / "lex.tsv"
    lex.write_text("नहीं\tnahin\t1\nनहीं\tnahi\t3\nनहीं\tNahi\t1\n"
                   "घर\tghar\t2\nघर\tgar\t2\n", encoding="utf-8")
    table = load_lexicon(lex)
    assert table["नहीं"] == "nahi"      # 4 votes after lowercasing
    assert table["घर"] == "gar"         # 2-2 tie, alphabetical


def test_romaniser_prefers_lexicon_and_counts_paths():
    r = Romaniser({"घर": "ghar"})
    assert r.sentence("मेरा घर। 5 OK") == "mera ghar. 5 OK"
    s = r.summary()
    assert (s["from_lexicon"], s["from_rules"], s["passthrough_tokens"]) == (1, 1, 2)
    assert s["lexicon_share"] == 0.5


def test_romanised_output_passes_the_generator_refusal(tmp_path):
    hindi = Romaniser({}).sentence("मैं घर जा रहा हूँ")
    path = tmp_path / "pairs.tsv"
    path.write_text("I am going home\t{}\n".format(hindi), encoding="utf-8")
    pairs = codemix.read_parallel(path)
    assert pairs[0][1][0] == "main"


def test_refusal_still_fires_on_unromanised_text(tmp_path):
    path = tmp_path / "pairs.tsv"
    path.write_text("hello\tनमस्ते दोस्त\n", encoding="utf-8")
    with pytest.raises(codemix.CodeMixError, match="romanise_parallel"):
        codemix.read_parallel(path)


def test_levenshtein():
    assert levenshtein("nahi", "nahin") == 1
    assert levenshtein("", "abc") == 3
    assert levenshtein("kitten", "sitting") == 3


# --- generate_codemix.py --gate-manifest / --stats-out --------------------------

def _write_splits(root, test_english):
    from lrcs.text import sha256_file
    split_dir = root / "processed" / "toy"
    split_dir.mkdir(parents=True)
    sources = {"train": "Rivers carry sediment to the delta every year.",
               "dev": "Please submit the application form before the end of the month.",
               "test": test_english}
    manifest = {"source": "toy", "params": {"dup_threshold": 0.7}, "splits": {}}
    for name, english in sources.items():
        path = split_dir / "{}.tsv".format(name)
        path.write_text("id\tgroup\tenglish\thindi\thinglish\ni0\tg\t{}\tx\th\n".format(english),
                        encoding="utf-8")
        manifest["splits"][name] = {"sha256": sha256_file(path)}
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root / "manifest.json", root / "processed"


def _run(tmp_path, test_english):
    import generate_codemix
    manifest, processed = _write_splits(tmp_path, test_english)
    out_dir, stats = tmp_path / "out", tmp_path / "stats" / "s.json"
    rc = generate_codemix.main(["--input", str(FIXTURE), "--out-dir", str(out_dir),
                                "--stats-out", str(stats), "--gate-manifest", str(manifest),
                                "--processed-dir", str(processed)])
    return rc, out_dir, stats


def test_generator_gate_passes_and_records_hashes(tmp_path):
    rc, out_dir, stats = _run(tmp_path, "The committee will meet again on Monday.")
    assert rc == 0
    data = json.loads(stats.read_text(encoding="utf-8"))
    assert data["contamination_gate"]["passed"] is True
    assert len(data["input_sha256"]) == len(data["output_sha256"]) == 64
    assert (out_dir / "codemix_batch.tsv").exists()
    assert not (out_dir / "codemix_stats.json").exists()   # --stats-out took it


def test_generator_gate_halts_before_writing_on_a_test_source(tmp_path):
    # This fixture sentence is known to be generated (it is in the committed batch).
    rc, out_dir, stats = _run(tmp_path, "The boy is reading a book")
    assert rc == 3
    assert not (out_dir / "codemix_batch.tsv").exists()
    assert not stats.exists()


# --- codemix_quality.py ---------------------------------------------------------

def test_quality_flags_repeats_and_inversions(tmp_path):
    import codemix_quality
    batch = tmp_path / "b.tsv"
    header = "source_index\tenglish\thindi\tcodemixed\tblocks\tswitch_points\tspf\talignment_coverage\n"
    rows = ["1\tthe boy reads\tladka padhta hai\tthe boy padhta hai\t2\t1\t0.2\t1.0",
            "2\tnew rules apply\tnaye niyam lagu\tnew new niyam lagu\t2\t1\t0.2\t1.0",
            "3\tshe went home\tvah ghar gayi\thome she gayi\t2\t1\t0.2\t1.0"]
    batch.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    q = codemix_quality.quality(batch)
    assert q["rows"] == 3
    assert q["rows_with_repeated_token"] == 1
    assert q["rows_with_english_order_inversion"] == 1
    assert q["rows_with_neither_defect"] == 1

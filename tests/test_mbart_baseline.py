"""Tests for the reproduced baseline (298-52): models/train_mbart_baseline.py and
models/transliterate.py.

The data, input-assembly and post-processing paths are tested directly. The last
test trains and decodes a tiny randomly initialised mBART on CPU, with a
SentencePiece model built from the fixture text, so the Trainer, label and
decoder-start wiring is exercised without downloading anything. It proves the
code path, not the recipe: the full-size run needs a GPU.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
sys.path.insert(0, str(ROOT / "common"))

import train_mbart_baseline as mb  # noqa: E402
import transliterate as tr  # noqa: E402

HEADER = "id\tgroup\tenglish\thindi\thinglish"
ROWS = [
    ("a1", "g1", "I am going home.", "मैं घर जा रहा हूँ।", "main ghar ja raha hoon."),
    ("a2", "g1", "I am going home.", "मैं घर जा रहा हूँ।", "mai ghar ja rha hu."),
    ("b1", "g2", "Call me tomorrow.", "मुझे कल फोन करना।", "mujhe kal call karna."),
    ("c1", "g3", "The train is late.", "ट्रेन लेट है।", "train late hai."),
]


def _write_split(path, rows=ROWS):
    path.write_text("\n".join([HEADER] + ["\t".join(r) for r in rows]) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------ the recipe
def test_paper_constants_match_section_4():
    assert mb.PAPER == {
        "model": "facebook/mbart-large-cc25", "lr": 3e-5, "adam_beta1": 0.9,
        "adam_beta2": 0.98, "adam_epsilon": 1e-6, "dropout": 0.3, "max_steps": 10000,
        "warmup_steps": 2500, "lr_scheduler": "polynomial"}


def test_assumptions_are_kept_apart_from_the_paper():
    assert not set(mb.ASSUMED) & set(mb.PAPER)


# ----------------------------------------------------------------------- data
def test_read_split_finds_columns_by_header(tmp_path):
    path = tmp_path / "s.tsv"
    path.write_text("hinglish\tenglish\thindi\nkal milte hain\tSee you tomorrow\tकल मिलते हैं\n",
                    encoding="utf-8")
    [rec] = mb.read_split(path)
    assert (rec["english"], rec["hinglish"], rec["id"]) == ("See you tomorrow", "kal milte hain", "1")


def test_read_split_refuses_a_file_without_hindi(tmp_path):
    path = tmp_path / "s.tsv"
    path.write_text("english\thinglish\nhi\thello\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        mb.read_split(path)


def test_build_source_conditions():
    rec = {"id": "x", "english": "Call me.", "hindi": "मुझे फोन करो।", "hinglish": "mujhe call karo."}
    assert mb.build_source(rec, "english") == "Call me."
    assert mb.build_source(rec, "both") == "Call me. </s> मुझे फोन करो।"
    with pytest.raises(ValueError):
        mb.build_source(dict(rec, hindi=""), "both")


def test_unique_sources_decode_each_source_once(tmp_path):
    records = mb.read_split(_write_split(tmp_path / "t.tsv"))
    sources, positions = mb.unique_sources(records, "english")
    assert len(records) == 4 and len(sources) == 3
    assert positions == [0, 0, 1, 2]


# ----------------------------------------------------------- transliteration
def test_only_devanagari_runs_are_transliterated():
    word_fn = {"स्तर": "star", "घर": "ghar"}.get
    assert tr.transliterate_line("jeevan ka aam star(स्तर) uncha", word_fn) == \
        "jeevan ka aam star(star) uncha"
    assert tr.transliterate_line("main घर ja raha hoon।", word_fn) == "main ghar ja raha hoon."
    assert tr.transliterate_line("all roman 123", word_fn) == "all roman 123"


def test_devanagari_digits_are_mapped_without_a_backend():
    assert tr.transliterate_line("१९८५-८६", lambda w: "?") == "1985-86"


def test_transliterate_file_reports_script_before_and_after(tmp_path, monkeypatch):
    monkeypatch.setitem(tr.BACKENDS, "stub", lambda: (lambda w: "x"))
    src = tmp_path / "raw.txt"
    src.write_text("main घर\nall roman\n", encoding="utf-8")
    info = tr.transliterate_file(src, tmp_path / "auto.txt", "stub")
    assert info["before"]["lines_with_devanagari"] == 1
    assert info["after"]["lines_with_devanagari"] == 0
    assert info["paper_backend"] is False
    assert (tmp_path / "auto.txt").read_text(encoding="utf-8") == "main x\nall roman\n"


def test_sanscript_backend_gives_plain_lower_case_roman():
    pytest.importorskip("indic_transliteration")
    fn = tr.sanscript_backend()
    # final inherent vowel silent, anusvara as n / m, long vowels doubled only inside a word
    expected = {"घर": "ghar", "स्तर": "star", "मैं": "main", "अंबर": "ambar",
                "बात": "baat", "ज़मीन": "zameen", "पता": "pata", "हूँ": "hoon", "क्या": "kya"}
    assert {w: fn(w) for w in expected} == expected


# ------------------------------------------------- end to end, tiny, on CPU
def test_tiny_mbart_trains_and_decodes_on_cpu(tmp_path, monkeypatch):
    torch = pytest.importorskip("torch")
    transformers = pytest.importorskip("transformers")
    spm = pytest.importorskip("sentencepiece")
    import repro

    corpus = tmp_path / "corpus.txt"
    corpus.write_text("\n".join(f"{r[2]}\n{r[3]}\n{r[4]}" for r in ROWS) * 20, encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(corpus), model_prefix=str(tmp_path / "sp"),
                                   vocab_size=60, character_coverage=1.0, model_type="unigram",
                                   bos_id=0, pad_id=1, eos_id=2, unk_id=3)
    tok = transformers.MBartTokenizer(vocab_file=str(tmp_path / "sp.model"))
    cfg = transformers.MBartConfig(vocab_size=len(tok), d_model=16, encoder_layers=1,
                                   decoder_layers=1, encoder_attention_heads=2,
                                   decoder_attention_heads=2, encoder_ffn_dim=32,
                                   decoder_ffn_dim=32, max_position_embeddings=64,
                                   pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id,
                                   bos_token_id=tok.bos_token_id)
    tiny = tmp_path / "tiny-mbart"
    torch.manual_seed(0)
    transformers.MBartForConditionalGeneration(cfg).save_pretrained(tiny)
    tok.save_pretrained(tiny)

    split = _write_split(tmp_path / "split.tsv")
    monkeypatch.setattr(repro, "DEFAULT_RUNS_DIR", tmp_path / "runs")
    out = tmp_path / "out"
    mb.main(["--condition", "both", "--train", str(split), "--dev", str(split),
             "--test", str(split), "--out", str(out), "--model", str(tiny),
             "--max-steps", "4", "--warmup-steps", "1", "--batch-size", "2",
             "--max-target-len", "12", "--num-beams", "2"])

    raw = (out / "both.s13.raw.txt").read_text(encoding="utf-8").splitlines()
    ref = (out / "test.ref.txt").read_text(encoding="utf-8").splitlines()
    assert len(raw) == len(ref) == len(ROWS)
    assert raw[0] == raw[1]                     # one source, decoded once, used twice
    assert (out / "both.s13.best").is_dir()
    [record] = list((tmp_path / "runs").glob("*_baseline-gahoi-both_seed13.json"))
    assert '"status": "ok"' in record.read_text(encoding="utf-8")

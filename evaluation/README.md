# Evaluation harness

One command scores model outputs against references for Hinglish (romanized
Hindi–English) or Hindi (Devanagari) generation.

## Setup

```bash
pip install -r evaluation/requirements.txt
```

## Run

```bash
# Hinglish, two seeds -> per-seed scores plus mean ± std
python evaluation/run_eval.py --ref evaluation/samples/ref.hinglish \
    --hyp evaluation/samples/hyp.seed1 evaluation/samples/hyp.seed2 \
    --out results/hinglish.json

# Hindi (Devanagari), single run
python evaluation/run_eval.py --lang hindi --ref evaluation/samples/ref.hindi \
    --hyp evaluation/samples/hyp.hindi
```

Input files are plain text, one sentence per line. Hypothesis line *i* is
scored against reference line *i*, so every hypothesis file must have exactly
as many lines as the reference file.

## Metrics

| Metric | What it measures |
|---|---|
| BLEU | n-gram overlap with the reference (sacrebleu; `13a` tokenizer for Hinglish, `intl` for Hindi) |
| chrF++ | character n-gram F-score plus word bigrams; tolerant of romanization spelling variants (`yeh`/`ye`) |
| CMI | Code-Mixing Index (Das & Gambäck, 2014), sentence average. 0 = monolingual, higher = more mixed. Reported for both hypotheses and reference so you can check whether the model mixes as much as real speakers do. |

**CMI caveat:** token language is tagged heuristically: Devanagari counts as
Hindi, Latin tokens in a small English word list count as English, and all
other Latin tokens count as romanized Hindi. That's fine for comparing models
against each other, but use a trained language-ID model before you report
final CMI values.

The files in `samples/` are toy data for smoke-testing the harness, not
project results.

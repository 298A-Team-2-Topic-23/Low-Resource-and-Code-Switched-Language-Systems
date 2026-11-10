# Reproducing Gahoi et al. (2022), MixMT Subtask-1

Linear **298-52**. Written by Thomas Lnu, Shibin Biji.

This is the project's quality gate. Until the evaluation harness reproduces a published
number, no model result can be interpreted (Workbook 2, section 4.4). This file records
what the paper specifies, what it leaves out and what we assumed in its place, and what the
reproduction can and cannot be compared with. It was written **before** the reproduction ran.

Source read: Gahoi, Duneja, Padhi, Mangale, Rajput, Kamble, Sharma and Varma (2022), *Gui at
MixMT 2022: English-Hinglish — An MT approach for translation of code mixed data*, WMT 2022,
pages 1126–1130 (ACL Anthology `2022.wmt-1.112`). Quotations below are from that PDF.

## 1. What the paper reports

Table 2, "ROUGE-L and WER scores after different post processing tasks", on a 500-sentence
test set that "also had both English sentence and its corresponding Hindi sentence":

| Row | Post processing | ROUGE-L | WER |
|---|---|---|---|
| 1 | Normal Output | 0.39091 | 0.81884 |
| 2 | With Automated Transliteration | 0.48376 | 0.72561 |
| 3 | With Automated Transliteration + Dictionary Based Transliteration | **0.61667** | **0.63342** |

The project's target, 0.617 / 0.633, is row 3. The model's own output is row 1, at 0.391:
all 0.226 ROUGE-L between row 1 and row 3 comes from post-processing applied after the
model, and 0.133 of it from the dictionary step alone. Row 3 depends on "a dictionary of most
common words and numbers with their corresponding transliterated Roman text", and that
dictionary was not released. **Row 3 cannot be rebuilt by anyone outside the authors' team.**
The reproduction is therefore compared with rows 1 and 2. `--check-baseline` still prints
its verdict against 0.617, and a miss against row 3 is the expected result, not a harness
failure.

## 2. The recipe: specified, assumed, and deviating

**Specified by the paper, and followed** (`models/train_mbart_baseline.py`, `PAPER`):

| Item | Paper | Here |
|---|---|---|
| Model | mBART, "12 encoder layers and 12 decoder layers", "text from 25 languages", fairseq | `facebook/mbart-large-cc25`, Hugging Face |
| Input | English and the corresponding Hindi sentence | `--condition both` |
| Loss | "label smoothed cross entropy" | `label_smoothing_factor` |
| Optimiser | Adam, β1 0.9, β2 0.98, ε 10⁻⁶ | same |
| Schedule | "polynomial decay learning rate scheduling" | `polynomial`, power 1, to 0 |
| Learning rate, dropout | 3 × 10⁻⁵, 0.3 | same |
| Length | "10000 steps with 2500 warm up steps" | same |
| Selection | "validate the model on each epoch … select the model with the lowest loss" | eval and save every epoch, best `eval_loss` kept |
| Post-processing | "transliteration function from indicate library" | `models/transliterate.py --backend indicate`, indicate 0.1.0 |

**Not specified by the paper, and assumed** (`ASSUMED`; each run record lists them):

| Item | Assumed | Why |
|---|---|---|
| How English and Hindi are combined | `english </s> hindi`, source code `en_XX` | The paper says "we process the input data … as explained above", but no explanation precedes it. mBART's own end-of-sentence token is the least invented boundary |
| Target language code | `hi_IN` | The paper reports raw output "in a mixed script (Roman + Devanagari)", which is what a Hindi target code produces on Romanised targets |
| Label-smoothing value | 0.1 | Common fairseq translation setting; the paper gives none |
| Beam size | 5 | fairseq's default; the paper gives none |
| "batch size of 512 tokens" | 8 sentences | Hugging Face batches by sentence. HinGE averages ~15 words per side, so 8 two-input pairs is roughly 512 tokens |
| ROUGE-L and WER tooling | `evaluation/run_eval.py`: sentence-level ROUGE-L F1 averaged, corpus WER, both on case- and punctuation-folded tokens | The paper describes both metrics in prose but names no tool or tokenisation |

**Known deviations**, which bound how close the reproduction can get:

| Deviation | Effect |
|---|---|
| **Vocabulary.** The paper reduced mBART's vocabulary to tokens in the task data, the IIT Bombay corpus and Dakshina. That vocabulary was not released, so the full vocabulary is used | A larger model with the same pretrained weights. Probably small for quality; it costs memory |
| **Training data.** The paper used HinGE's synthetic and human parts: 3,263 + 1,800 train and 396 + 376 validation sentences (Table 1). The project's splits hold human references only: 3,738 train and 468 dev records over 1,549 and 192 sources | Less and differently distributed supervision. The paper's human count (2,176 sentences) also differs from the 1,976 rows of the release we hold, so the organisers' split was not the public file |
| **Test set.** The MixMT Subtask-1 test references are not in the repository | Until they are, the test set is the HinGE test split: 468 records over 197 sources, scored per record. The comparison with Table 2 is then **indicative, not like-for-like**, and every result row says which test set it used |
| **Transliterator version.** The paper does not say which indicate release it used. 0.1.0 (22 August 2022) was current at submission; it needs TensorFlow. If it cannot be installed, the notebook falls back to `sanscript` and labels the row a deviation | A sanscript row is not the paper's row 2 |

## 3. Two conditions

| Condition | Input | Purpose |
|---|---|---|
| `both` | English and Hindi | The paper's setting, for comparability with Table 2 |
| `english` | English only | Our own reference point: Models 1 to 4 see English only, so this is the baseline they are fairly compared with |

## 4. How a result will be read

Decided now, before any number exists:

- **Raw output against row 1, transliterated output against row 2.** These two rows are the
  reproduction. Within 0.01 ROUGE-L of row 2, on the MixMT test set, counts as reproduced.
- **On the HinGE test split,** no tolerance applies. The numbers are reported as an
  indicative comparison, with the test-set difference stated next to them.
- **Row 3 is reported as unreachable,** with the reason above. If the reproduction misses
  rows 1 and 2 as well, that is a finding about the harness or the recipe, reported with the
  evidence. Model results are then presented as uninterpreted measurements, as Progress
  Report 2 Part D committed.
- **Three seeds** (13, 42, 1337) for any reported number, as for every model (section 4.4).

## 5. Results

Not run yet: no GPU was available to this work. Fill this table from `results/results.jsonl`
and cite the run records.

| Condition | Stage | Test set | Seeds | ROUGE-L | WER | Paper row | Run records |
|---|---|---|---|---|---|---|---|
| both | raw | | | | | 1: 0.39091 / 0.81884 | |
| both | transliterated | | | | | 2: 0.48376 / 0.72561 | |
| english | raw | | | | | — | |
| english | transliterated | | | | | — | |

## 6. How to run it

`notebooks/baseline_gahoi_colab.ipynb` runs everything on a Colab GPU: splits verified
against the manifest, both conditions, transliteration, scoring and the results table.
Start with `PROFILE = "smoke"` to prove the path, then `"full"`. By hand:

```bash
python models/train_mbart_baseline.py --condition both \
    --train data/processed/hinge/train.tsv --dev data/processed/hinge/dev.tsv \
    --test data/processed/hinge/test.tsv --out out/baseline --seed 13
python models/transliterate.py out/baseline/both.s13.raw.txt out/baseline/both.s13.auto.txt
python evaluation/run_eval.py --hyp out/baseline/both.s13.auto.txt \
    --ref out/baseline/test.ref.txt --system "Gahoi repro, both, auto" --check-baseline
```

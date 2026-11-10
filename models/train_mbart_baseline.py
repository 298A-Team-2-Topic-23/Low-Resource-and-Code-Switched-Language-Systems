#!/usr/bin/env python3
"""
Reproduced baseline: Gahoi et al. (2022), MixMT Subtask-1.  [Linear 298-52, owner: Shibin]

The project's quality gate. Until the evaluation harness reproduces a published
number, no model result can be interpreted (Workbook 2, section 4.4). The baseline
is a reference point, not one of the four models.

What the paper specifies, and is followed here (section 4, "Experimental Setup"):

  mBART, 12 encoder + 12 decoder layers, 25 languages     facebook/mbart-large-cc25
  label-smoothed cross-entropy                            yes
  Adam, beta1 0.9, beta2 0.98, eps 1e-6                   yes
  polynomial-decay learning-rate schedule                 yes (power 1, to 0)
  learning rate 3e-5, dropout 0.3                         yes
  10,000 steps, 2,500 warm-up steps                       yes
  validate every epoch, keep the lowest-loss checkpoint   yes
  English and Hindi both given as input                   --condition both

What the paper does not specify, and is therefore an assumption here. Each one is
recorded in the run record, and docs/baseline/gahoi_reproduction.md argues it:

  how English and Hindi are combined     "english </s> hindi", source code en_XX
  target language code                   hi_IN: consistent with the paper's report
                                         that raw output came out in mixed script
  label-smoothing value                  0.1
  beam size                              5 (fairseq's default)
  "batch size of 512 tokens"             approximated as 8 sentences per batch;
                                         HinGE averages ~60 subword tokens per pair

Known deviations, which bound how close the reproduction can get:

  * The paper reduced mBART's vocabulary to tokens seen in the task data, IIT-B
    and Dakshina. That vocabulary was not released; the full vocabulary is used.
  * The paper trained on HinGE's synthetic and human parts (3,263 + 1,800 train
    sentences, Table 1). The project's splits hold the human references only.
  * The paper scored a 500-sentence MixMT test set. Its references are not in the
    repository; until they are, --test is the HinGE test split and the comparison
    with Table 2 is indicative, not like-for-like.

Usage
-----
  # the paper's condition, then our English-only reference point
  python models/train_mbart_baseline.py --condition both \\
      --train data/processed/hinge/train.tsv --dev data/processed/hinge/dev.tsv \\
      --test data/processed/hinge/test.tsv --out out/baseline --seed 13
  python models/train_mbart_baseline.py --condition english ... --seed 13

  # smoke test before committing a GPU to 10,000 steps
  python models/train_mbart_baseline.py --condition both ... --limit 64 --max-steps 20

Then post-process and score (Table 2, rows 1 and 2):

  python models/transliterate.py out/baseline/both.s13.raw.txt \\
      out/baseline/both.s13.auto.txt --backend indicate
  python evaluation/run_eval.py --hyp out/baseline/both.s13.auto.txt \\
      --ref out/baseline/test.ref.txt --system "Gahoi repro, both" --check-baseline

NOT YET RUN ON A GPU. The data, input-assembly and decoding paths are covered by
tests/test_mbart_baseline.py, including a CPU run of a tiny randomly initialised
mBART; the full-size run is unverified until it happens.
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))   # for transliterate.py

# Section 4 of the paper, verbatim where it gives a number.
PAPER = {
    "model": "facebook/mbart-large-cc25",
    "lr": 3e-5,
    "adam_beta1": 0.9,
    "adam_beta2": 0.98,
    "adam_epsilon": 1e-6,
    "dropout": 0.3,
    "max_steps": 10000,
    "warmup_steps": 2500,
    "lr_scheduler": "polynomial",
}
# Not given in the paper; see the module docstring.
ASSUMED = {
    "label_smoothing": 0.1,
    "num_beams": 5,
    "batch_size": 8,
    "src_lang": "en_XX",
    "tgt_lang": "hi_IN",
    "separator": " </s> ",
}
CONDITIONS = ("both", "english")
FIELDS = ("english", "hindi", "hinglish")


def read_split(path, limit=None):
    """Records from a split TSV. Columns are found by header name, so the HinGE
    splits and a MixMT test file laid out as english/hindi/hinglish both load."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines:
        sys.exit("empty split file: {}".format(path))
    header = [h.strip().lower() for h in lines[0].split("\t")]
    missing = [f for f in FIELDS if f not in header]
    if missing:
        sys.exit("{} has no {} column (header: {})".format(path, "/".join(missing), header))
    col = {name: header.index(name) for name in header}
    records = []
    for n, line in enumerate(lines[1:], 1):
        parts = line.split("\t")
        if len(parts) < len(header):
            continue
        rec = {f: parts[col[f]].strip() for f in FIELDS}
        rec["id"] = parts[col["id"]] if "id" in col else str(n)
        if rec["english"] and rec["hinglish"]:
            records.append(rec)
    if limit:
        records = records[:limit]
    if not records:
        sys.exit("no usable records in {}".format(path))
    return records


def build_source(record, condition, separator=ASSUMED["separator"]):
    """Model input for one record. The paper gives the model English and Hindi
    but not how they are joined; mBART's own end-of-sentence token is used as the
    boundary, so no new token has to be learned."""
    if condition == "english":
        return record["english"]
    if condition == "both":
        if not record["hindi"]:
            raise ValueError("record {} has no Hindi; --condition both needs it".format(
                record["id"]))
        return record["english"] + separator + record["hindi"]
    raise ValueError("unknown condition: {}".format(condition))


def unique_sources(records, condition):
    """Distinct model inputs in first-seen order, and each record's index into
    them. HinGE has several references per source, so the test split's 468
    records need only ~197 decodes."""
    order, index = [], {}
    positions = []
    for r in records:
        src = build_source(r, condition)
        if src not in index:
            index[src] = len(order)
            order.append(src)
        positions.append(index[src])
    return order, positions


def output_paths(out_dir, condition, seed):
    out = Path(out_dir)
    return {"raw": out / "{}.s{}.raw.txt".format(condition, seed),
            "ref": out / "test.ref.txt",
            "checkpoint": out / "{}.s{}.ckpt".format(condition, seed)}


def pick_precision(torch):
    """fp16 on Turing (T4), bf16 only where it is native; see train_qlora.py."""
    if not torch.cuda.is_available():
        return "fp32"
    try:
        native_bf16 = torch.cuda.is_bf16_supported(including_emulation=False)
    except TypeError:
        native_bf16 = torch.cuda.get_device_capability()[0] >= 8
    return "bf16" if native_bf16 else "fp16"


def decode(model, tok, sources, args, device):
    import torch
    start = tok.convert_tokens_to_ids(ASSUMED["tgt_lang"])
    outputs = []
    model.eval()
    for i in range(0, len(sources), args.decode_batch):
        batch = tok(sources[i:i + args.decode_batch], return_tensors="pt", padding=True,
                    truncation=True, max_length=args.max_source_len).to(device)
        with torch.no_grad():
            gen = model.generate(**batch, decoder_start_token_id=start,
                                 num_beams=args.num_beams, max_length=args.max_target_len)
        outputs.extend(t.strip() for t in tok.batch_decode(gen, skip_special_tokens=True))
    return outputs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--condition", choices=CONDITIONS, required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--dev", required=True, help="validated every epoch; lowest loss is kept")
    ap.add_argument("--test", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=PAPER["model"])
    ap.add_argument("--seed", type=int, default=13, help="one of 13, 42, 1337")
    ap.add_argument("--max-steps", type=int, default=PAPER["max_steps"])
    ap.add_argument("--warmup-steps", type=int, default=PAPER["warmup_steps"])
    ap.add_argument("--batch-size", type=int, default=ASSUMED["batch_size"])
    ap.add_argument("--label-smoothing", type=float, default=ASSUMED["label_smoothing"])
    ap.add_argument("--num-beams", type=int, default=ASSUMED["num_beams"])
    ap.add_argument("--max-source-len", type=int, default=256)
    ap.add_argument("--max-target-len", type=int, default=128)
    ap.add_argument("--decode-batch", type=int, default=16)
    ap.add_argument("--limit", type=int, help="first N records of each split (smoke test)")
    ap.add_argument("--gradient-checkpointing", action="store_true",
                    help="trade speed for memory if a 16 GB card runs out")
    ap.add_argument("--predict-only", metavar="CHECKPOINT",
                    help="skip training and decode the test split with this checkpoint")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT / "common"))
    try:
        from repro import set_seed, RunLogger
    except ImportError:
        sys.exit("common/repro.py must be importable")
    set_seed(args.seed)

    try:
        import torch
        from transformers import (AutoModelForSeq2SeqLM, AutoTokenizer,
                                  DataCollatorForSeq2Seq, Seq2SeqTrainer,
                                  Seq2SeqTrainingArguments)
    except ImportError as exc:
        sys.exit("missing dependency: {}\npip install -r requirements.txt".format(exc))

    train = read_split(args.train, args.limit)
    dev = read_split(args.dev, args.limit)
    test = read_split(args.test, args.limit)
    paths = output_paths(args.out, args.condition, args.seed)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    precision = pick_precision(torch)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("condition {}  train {:,}  dev {:,}  test {:,}  precision {}".format(
        args.condition, len(train), len(dev), len(test), precision))

    cfg = dict(PAPER, **{k: v for k, v in ASSUMED.items()})
    cfg.update({"model": args.model, "condition": args.condition, "seed": args.seed,
                "max_steps": args.max_steps, "warmup_steps": args.warmup_steps,
                "batch_size": args.batch_size, "label_smoothing": args.label_smoothing,
                "num_beams": args.num_beams, "precision": precision,
                "n_train": len(train), "n_dev": len(dev), "n_test": len(test),
                "train_file": args.train, "test_file": args.test,
                "assumed": sorted(ASSUMED), "predict_only": bool(args.predict_only)})

    with RunLogger("baseline-gahoi-{}".format(args.condition), seed=args.seed, config=cfg) as run:
        t0 = time.time()
        source = args.predict_only or args.model
        tok = AutoTokenizer.from_pretrained(source, src_lang=ASSUMED["src_lang"],
                                            tgt_lang=ASSUMED["tgt_lang"])
        model = AutoModelForSeq2SeqLM.from_pretrained(source, dropout=PAPER["dropout"])

        if not args.predict_only:
            def encode(records):
                srcs = [build_source(r, args.condition) for r in records]
                enc = tok(srcs, text_target=[r["hinglish"] for r in records],
                          truncation=True, max_length=args.max_source_len)
                return [{"input_ids": i, "attention_mask": a,
                         "labels": l[:args.max_target_len]}
                        for i, a, l in zip(enc["input_ids"], enc["attention_mask"],
                                           enc["labels"])]

            targs = Seq2SeqTrainingArguments(
                output_dir=str(paths["checkpoint"]),
                per_device_train_batch_size=args.batch_size,
                per_device_eval_batch_size=args.batch_size,
                max_steps=args.max_steps,
                learning_rate=PAPER["lr"],
                lr_scheduler_type=PAPER["lr_scheduler"],
                warmup_steps=args.warmup_steps,
                adam_beta1=PAPER["adam_beta1"],
                adam_beta2=PAPER["adam_beta2"],
                adam_epsilon=PAPER["adam_epsilon"],
                weight_decay=0.0,
                label_smoothing_factor=args.label_smoothing,
                eval_strategy="epoch",
                save_strategy="epoch",
                save_only_model=True,
                save_total_limit=1,
                load_best_model_at_end=True,
                metric_for_best_model="eval_loss",
                greater_is_better=False,
                fp16=precision == "fp16",
                bf16=precision == "bf16",
                gradient_checkpointing=args.gradient_checkpointing,
                logging_steps=50,
                report_to=[],
                seed=args.seed,
                data_seed=args.seed,
            )
            trainer = Seq2SeqTrainer(
                model=model, args=targs, train_dataset=encode(train), eval_dataset=encode(dev),
                data_collator=DataCollatorForSeq2Seq(tok, model=model))
            result = trainer.train()
            model = trainer.model
            best = trainer.state.best_metric
            run.log_metric("train_loss", round(float(result.training_loss), 4))
            run.log_metric("steps", int(result.global_step))
            run.log_metric("best_eval_loss", None if best is None else round(float(best), 4))
            run.log_metric("best_checkpoint", trainer.state.best_model_checkpoint)
            final = Path(args.out) / "{}.s{}.best".format(args.condition, args.seed)
            trainer.save_model(str(final))
            tok.save_pretrained(str(final))

        model.to(device)
        sources, positions = unique_sources(test, args.condition)
        print("decoding {:,} distinct sources for {:,} test records".format(
            len(sources), len(test)))
        decoded = decode(model, tok, sources, args, device)
        hyps = [decoded[p] for p in positions]
        paths["raw"].write_text("\n".join(hyps) + "\n", encoding="utf-8")
        paths["ref"].write_text("\n".join(r["hinglish"] for r in test) + "\n", encoding="utf-8")

        from transliterate import script_stats
        stats = script_stats(hyps)
        run.log_metric("raw_lines_with_devanagari", stats["lines_with_devanagari"])
        run.log_metric("decoded_sources", len(sources))
        run.note("Gahoi et al. (2022) recipe, condition {}; assumptions: {}".format(
            args.condition, json.dumps(ASSUMED)))
        run.note("deviations: full mBART vocabulary (paper's reduced vocabulary unreleased); "
                 "human HinGE references only; test file {}".format(args.test))
        print("raw output -> {}  ({} of {} lines contain Devanagari)".format(
            paths["raw"], stats["lines_with_devanagari"], stats["lines"]))
        print("references -> {}".format(paths["ref"]))
        print("elapsed {:.2f} GPU-hours -- record this in docs/COMPUTE_BUDGET.md".format(
            (time.time() - t0) / 3600))


if __name__ == "__main__":
    main()

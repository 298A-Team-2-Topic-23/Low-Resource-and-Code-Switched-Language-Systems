#!/usr/bin/env python3
"""
Model 2: QLoRA parameter-efficient fine-tune.  [Linear 298-54, owner: Sarvesh]

The course requires the first of four models to be trained, fine-tuned or adapted by the
team. A prompted zero-shot backbone does not satisfy that, so this is the deliverable that
Team Meeting 2 checks.

The recipe is not a free choice -- it was fixed in the technology survey before any result
existed, and M2 vs M3 later has to isolate vocabulary and continued pretraining, which only
works if M2's recipe is held constant:

  rank 32, alpha 64, dropout 0.05
  ALL linear projections (q,k,v,o + gate,up,down), not attention-only
  LR 2e-4, cosine schedule, 3% warmup, 2-3 epochs, effective batch 32-64
  bf16, gradient checkpointing, 4-bit NF4 base with double quantisation
  loss masked to completion tokens only

Two of those are the ones people get wrong. Targeting attention-only underperforms and is
the common mistake. Computing loss over the prompt as well as the completion teaches the
model to generate the instruction back, which quietly costs a point or two of chrF++.

Usage
-----
  python models/train_qlora.py \
      --train data/processed/hinge/train.tsv \
      --out out/m2-seed13 --seed 13

  # smoke test on 64 examples and 10 steps before committing a GPU to the full run
  python models/train_qlora.py --train data/processed/hinge/train.tsv \
      --out /tmp/smoke --limit 64 --max-steps 10

Then generate and score with the existing tools:

  python models/generate_zeroshot.py --src data/test.en.txt --out out/m2.s13.txt \
      --adapter out/m2-seed13 --seed 13
  python evaluation/run_eval.py --hyp out/m2.s13.txt --ref data/test.hinglish.txt \
      --system "Model 2 QLoRA"

NOT YET RUN ON A GPU. The CPU paths (argument handling, data loading, prompt assembly and
label masking) are covered by tests/test_train_qlora.py; the training loop itself is
unverified until 298-51 confirms the allocation. Treat the first run as a smoke test.
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT = (
    "You translate English into Hinglish: Hindi written in Roman script, mixed "
    "naturally with English words the way bilingual speakers actually write on "
    "messaging apps. Do not use Devanagari. Do not translate into formal Hindi. "
    "Output only the Hinglish sentence, nothing else."
)

# The adapter targets every linear projection, not just attention. Attention-only
# adapters underperform on generation and the difference is large enough to confound
# the M2 vs M3 comparison this arm exists to support.
TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj",
                  "gate_proj", "up_proj", "down_proj"]


def read_pairs(path, src_col=0, tgt_col=1, limit=None):
    """TSV of (english, hinglish). Extra columns are ignored."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) <= max(src_col, tgt_col):
            continue
        src, tgt = parts[src_col].strip(), parts[tgt_col].strip()
        if src and tgt:
            rows.append((src, tgt))
    if not rows:
        sys.exit("no usable (source, target) pairs in {}".format(path))
    # A header row survives the checks above, so drop it by name rather than by position.
    if rows and rows[0][0].lower() in ("english", "source_en", "english_source"):
        rows = rows[1:]
    return rows[:limit] if limit else rows


def build_example(tokenizer, src, tgt, max_len):
    """One training example with the loss masked to the completion.

    The prompt is rendered through the model's own chat template so training and
    generation see the same framing; `generate_zeroshot.py` builds its prompt the same
    way. Everything before the assistant's turn is labelled -100 so no loss is taken on
    it -- otherwise the model learns to reproduce the instruction.
    """
    prompt = tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": src}],
        tokenize=False, add_generation_prompt=True,
    )
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    target_ids = tokenizer(tgt, add_special_tokens=False)["input_ids"]
    if tokenizer.eos_token_id is not None:
        target_ids = target_ids + [tokenizer.eos_token_id]

    input_ids = prompt_ids + target_ids
    labels = [-100] * len(prompt_ids) + list(target_ids)

    # Truncate from the left so the completion always survives; a right truncation would
    # drop the very tokens the loss is computed on.
    if len(input_ids) > max_len:
        input_ids = input_ids[-max_len:]
        labels = labels[-max_len:]
    return {"input_ids": input_ids, "labels": labels}


class Collator:
    """Pads a batch and keeps -100 in the label padding so it stays masked."""

    def __init__(self, pad_id):
        self.pad_id = pad_id

    def __call__(self, features):
        import torch
        width = max(len(f["input_ids"]) for f in features)
        input_ids, labels, attention = [], [], []
        for f in features:
            gap = width - len(f["input_ids"])
            input_ids.append(f["input_ids"] + [self.pad_id] * gap)
            labels.append(f["labels"] + [-100] * gap)
            attention.append([1] * len(f["input_ids"]) + [0] * gap)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
            "attention_mask": torch.tensor(attention, dtype=torch.long),
        }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", required=True, help="training split, TSV")
    ap.add_argument("--out", required=True, help="where the adapter is written")
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--seed", type=int, default=13, help="one of 13, 42, 1337")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=32)
    ap.add_argument("--alpha", type=int, default=64)
    ap.add_argument("--dropout", type=float, default=0.05)
    ap.add_argument("--batch-size", type=int, default=4, help="per device")
    ap.add_argument("--grad-accum", type=int, default=8,
                    help="effective batch = batch-size x grad-accum; keep it in 32-64")
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--src-col", type=int, default=0)
    ap.add_argument("--tgt-col", type=int, default=1)
    ap.add_argument("--limit", type=int, help="first N examples only (smoke test)")
    ap.add_argument("--max-steps", type=int, help="stop after N steps (smoke test)")
    ap.add_argument("--no-4bit", action="store_true",
                    help="bf16 base instead of 4-bit NF4; needs far more memory")
    args = ap.parse_args()

    effective = args.batch_size * args.grad_accum
    if not 16 <= effective <= 128:
        print("warning: effective batch {} is outside the 32-64 the recipe fixes; "
              "M2 vs M3 only isolates vocabulary if this is held constant"
              .format(effective), file=sys.stderr)

    sys.path.insert(0, str(REPO_ROOT / "common"))
    try:
        from repro import set_seed, RunLogger
    except ImportError:
        sys.exit("common/repro.py must be importable")
    set_seed(args.seed)

    try:
        import torch
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  BitsAndBytesConfig, Trainer, TrainingArguments)
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    except ImportError as exc:
        sys.exit("missing dependency: {}\npip install -r requirements.txt".format(exc))

    pairs = read_pairs(args.train, args.src_col, args.tgt_col, args.limit)
    print("training pairs: {:,}".format(len(pairs)))

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = None if args.no_4bit else BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    cfg = {
        "model": args.model, "seed": args.seed, "rank": args.rank, "alpha": args.alpha,
        "dropout": args.dropout, "lr": args.lr, "epochs": args.epochs,
        "effective_batch": effective, "max_len": args.max_len,
        "quantisation": "bf16" if args.no_4bit else "nf4-double",
        "target_modules": TARGET_MODULES, "n_train": len(pairs),
    }

    with RunLogger("model2-qlora", seed=args.seed, config=cfg) as run:
        t0 = time.time()
        print("loading {} ...".format(args.model))
        model = AutoModelForCausalLM.from_pretrained(
            args.model, quantization_config=quant,
            torch_dtype=torch.bfloat16, device_map="auto")
        model.config.use_cache = False          # incompatible with gradient checkpointing

        if not args.no_4bit:
            model = prepare_model_for_kbit_training(
                model, use_gradient_checkpointing=True)

        model = get_peft_model(model, LoraConfig(
            r=args.rank, lora_alpha=args.alpha, lora_dropout=args.dropout,
            target_modules=TARGET_MODULES, bias="none", task_type="CAUSAL_LM"))
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters())
        print("trainable {:,} of {:,} parameters ({:.3%})"
              .format(trainable, total, trainable / total))
        run.log_metric("trainable_parameters", trainable)

        dataset = [build_example(tok, s, t, args.max_len) for s, t in pairs]
        masked = sum(1 for d in dataset if all(x == -100 for x in d["labels"]))
        if masked:
            sys.exit("{} examples have no unmasked label after truncation -- raise "
                     "--max-len".format(masked))

        targs = TrainingArguments(
            output_dir=args.out,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps if args.max_steps else -1,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            bf16=True,
            gradient_checkpointing=True,
            logging_steps=10,
            save_strategy="no",
            report_to=[],
            seed=args.seed,
            data_seed=args.seed,
        )
        trainer = Trainer(model=model, args=targs, train_dataset=dataset,
                          data_collator=Collator(tok.pad_token_id))
        result = trainer.train()

        Path(args.out).mkdir(parents=True, exist_ok=True)
        model.save_pretrained(args.out)
        tok.save_pretrained(args.out)
        (Path(args.out) / "train_config.json").write_text(
            json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

        elapsed = time.time() - t0
        run.log_metric("train_loss", round(float(result.training_loss), 4))
        run.log_metric("steps", int(result.global_step))
        run.note("QLoRA r{} a{} on all linear projections, effective batch {}"
                 .format(args.rank, args.alpha, effective))
        print("\nadapter -> {}".format(args.out))
        print("elapsed {:.2f} GPU-hours -- record this in docs/COMPUTE_BUDGET.md "
              "in the same commit as the run".format(elapsed / 3600))


if __name__ == "__main__":
    main()

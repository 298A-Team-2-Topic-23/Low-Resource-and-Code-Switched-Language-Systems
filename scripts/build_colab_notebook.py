#!/usr/bin/env python3
"""
Generate notebooks/m1_m2_colab.ipynb.

The notebook is written from this script rather than edited by hand, because a
28-cell JSON document edited in place is where stale instructions survive. The
previous version told the reader to upload `HinGE.pkl` and offered a synthetic
fallback; both became wrong on 10 November, when `scripts/fetch_data.py` started
fetching the corpus from the authors' own CC-BY-4.0 release. Regenerate with:

    python3 scripts/build_colab_notebook.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "notebooks" / "m1_m2_colab.ipynb"
BRANCH = "sarvesh/298-real-data-foundation"

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {},
                  "source": text.strip("\n").splitlines(keepends=True)})


def code(text):
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
                  "outputs": [], "source": text.strip("\n").splitlines(keepends=True)})


md(f"""
# Models 1 and 2 on a GPU — the spec-faithful NF4 QLoRA run

**Linear 298-53 (Model 1) and 298-54 (Model 2).** Runtime → Change runtime type → GPU.

## Do you need this notebook?

**Not for a first result.** M1 and M2 have already been trained and scored on real data on an
Apple M4 laptop via MLX: chrF++ 43.270 → 57.808, +14.538 with a 95% CI of [10.776, 18.241] and
p < 0.0001 over a 2,000-sample paired bootstrap. See `reports/m1_m2_comparison.md`. That cost
1.33 GPU-hours and needed no allocation.

**Run this notebook for the three things the laptop cannot give you:**

1. **The recipe as section 4.1 specifies it.** `bitsandbytes` 4-bit NF4 with double
   quantisation is CUDA-only. The laptop run substituted MLX affine 4-bit, which is recorded as
   a deviation in the Workbook 2 carry-forward table. Running here removes that deviation.
2. **Three seeds.** 298-54 asks for three; the laptop run did one. Seed variance is required
   before any M1-to-M2 claim goes in the final report.
3. **A longer run, to settle an open question.** The laptop M2 improved chrF++ by 14.5 points
   while its code-mixing index *fell* from 15.40 to 11.88 against a human target of 25.86. That
   M2 saw about 500 examples (~0.16 epochs). Whether the regression is undertraining or
   something the recipe does is the most important open question for Team Meeting 2, and only a
   full-epoch run answers it.

`models/train_qlora.py` has **never run on a GPU**. Its CPU paths are covered by
`tests/test_train_qlora.py`; the training loop is unverified. Run the `smoke` profile first.

## What you need to upload

**Nothing.** The repository is public and the corpus is fetched from Hugging Face at a pinned
revision. Clone, install, run top to bottom.
""")

md("## 1. The GPU you were given")
code("""
!nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
import sys
try:
    import torch
    print("torch", torch.__version__, "| cuda", torch.cuda.is_available())
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        print(f"{p.name}, {p.total_memory/2**30:.1f} GB, compute {p.major}.{p.minor}")
        print("bf16 supported:", torch.cuda.is_bf16_supported())
    else:
        print("NO GPU. Runtime -> Change runtime type -> GPU, then run from the top.")
except ImportError:
    print("torch not installed yet; the install cell below handles it")
""")

md("""
## 2. Profile

`smoke` proves the path in minutes and its numbers mean nothing. Run it first, every time: this
trainer has never completed a GPU run, and finding that out after 40 minutes of a T4 is worse
than finding it out after three.

A T4 (16 GB) cannot hold 7B in 4-bit plus optimiser state at a useful sequence length, so the
`t4` profile runs one seed at a shorter sequence length. Three seeds at full length want an A100
or an L4.
""")
code("""
PROFILE = "smoke"          # "smoke" | "t4" | "a100"

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"   # docs/workbook1/section_1_4.md
SEEDS    = [13, 42, 1337]               # the project's fixed seeds

CFG = {
  "smoke": dict(model="Qwen/Qwen2.5-0.5B-Instruct", train_limit=256, max_steps=30,
                epochs=1, bsz=1, accum=16, maxlen=256, test_limit=48, seeds=[13],
                save_steps=0),
  "t4":    dict(model=MODEL_ID, train_limit=None, max_steps=None,
                epochs=1, bsz=1, accum=32, maxlen=320, test_limit=None, seeds=[42],
                save_steps=20),
  "a100":  dict(model=MODEL_ID, train_limit=None, max_steps=None,
                epochs=3, bsz=4, accum=8,  maxlen=512, test_limit=None, seeds=SEEDS,
                save_steps=50),
}[PROFILE]

print(f"profile={PROFILE}")
for k, v in CFG.items():
    print(f"  {k:12s} {v}")
print(f"\\n  effective batch = {CFG['bsz'] * CFG['accum']}")
if CFG["save_steps"]:
    print(f"  checkpoint every {CFG['save_steps']} steps -- a severed session costs "
          f"minutes, not the run")
if PROFILE == "smoke":
    print("\\n  SMOKE: a 0.5B stand-in on 256 examples. Nothing from this profile is")
    print("  reportable -- docs/COMPUTE_BUDGET.md already records three such runs that way.")
""")

md("""
## 3. Keep finished work across a disconnect

Colab will drop the runtime. Set `PERSIST_DIR` to a Drive path before any run you do not want
to repeat; finished seeds are restored instead of retrained.
""")
code("""
PERSIST_DIR = None          # e.g. "/content/drive/MyDrive/lrcs_runs" for the a100 run

import pathlib
if PERSIST_DIR:
    from google.colab import drive
    drive.mount("/content/drive")
    PERSIST = pathlib.Path(PERSIST_DIR); PERSIST.mkdir(parents=True, exist_ok=True)
    done = sorted(q.name for q in PERSIST.glob("m2-seed*") if (q/"adapter_config.json").exists())
    print("persisting to", PERSIST, "| already finished:", done or "none")
else:
    PERSIST = None
    print("no persistence -- a disconnect loses this session's work")
""")

md("## 4. Clone the repository")
code(f"""
import os, subprocess, pathlib

REPO   = "https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git"
BRANCH = "{BRANCH}"     # -> "main" once the real-data branch merges
ROOT   = pathlib.Path("/content/lrcs")

if ROOT.exists():
    import shutil; shutil.rmtree(ROOT)   # a stale clone is silently the wrong branch
subprocess.run(["git","clone","--depth","1","--branch",BRANCH,REPO,str(ROOT)], check=True)
os.chdir(ROOT)

head = subprocess.run(["git","rev-parse","--short","HEAD"],
                      capture_output=True, text=True).stdout.strip()
print("cwd:", os.getcwd(), "| branch:", BRANCH, "| HEAD:", head)

# Fail here, not two steps later with a confusing "no such file".
need = ("models/train_qlora.py", "models/generate_zeroshot.py", "scripts/run_pipeline.py",
        "scripts/fetch_data.py", "scripts/validate_raw.py", "scripts/build_sft_data.py",
        "scripts/score_codemixing.py", "evaluation/run_eval.py")
missing = [f for f in need if not pathlib.Path(f).exists()]
assert not missing, f"missing on this branch: {{missing}} -- check BRANCH"

assert "--adapter" in pathlib.Path("models/generate_zeroshot.py").read_text()
assert "--ref-jsonl" in pathlib.Path("evaluation/run_eval.py").read_text(), (
    "the harness has no --ref-jsonl flag, so it cannot score multi-reference as "
    "section 4.4 commits. Wrong branch.")
print("trainer, --adapter and multi-reference scoring all present")
""")

md("## 5. Install")
code("""
# transformers is pinned to the last 4.x on purpose: v5 restructured TrainingArguments
# and the trainer fails with "unexpected keyword argument 'warmup_ratio'". A floating
# ">=4.51" resolves to 5.x and breaks the training cell.
%pip install -q "transformers==4.57.6" "peft==0.17.1" "bitsandbytes>=0.47" \\
               "accelerate==1.10.1" datasketch sacrebleu sentencepiece

# Resolver complaints about diffusers, gradio and huggingface-hub concern Colab's own
# preinstalled packages. Nothing here imports them, so they are noise.

import transformers, peft
print("transformers", transformers.__version__, "| peft", peft.__version__)
assert transformers.__version__.startswith("4."), (
    f"transformers {transformers.__version__} is loaded, but the trainer needs 4.x.\\n"
    "Runtime -> Restart session, then run from the top. A pip install cannot replace a "
    "module this session has already imported.")
""")

md("""
## 6. Fetch the corpus

No upload. HinGE is published by the authors' own lab (Lingo Research Group, IIT Gandhinagar)
at `LingoIITGN/HinGE` under **CC-BY-4.0**, and is fetched at a pinned revision with its hash,
licence and citation recorded in `data/raw/MANIFEST.json`.

The project's datasheet previously recorded that licence as *"Unstated … non-commercial
(inferred) … Unresolved"*, which is why earlier notebooks asked you to upload a pickle by hand.
""")
code("""
import subprocess, sys
def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], **kw).returncode

assert run([sys.executable, "scripts/fetch_data.py", "--only", "hinge"]) == 0
assert run([sys.executable, "scripts/fetch_data.py", "--verify", "--only", "hinge"]) == 0
""")

md("""
## 7. Validate the corpus before building on it

Section 3.3 requires cleaning and validation tools. This one found that a different corpus's
Devanagari column was misaligned with its own English column, so it runs before the pipeline
rather than after.
""")
code("""
import shutil, pathlib
pathlib.Path("data/raw/hinge.csv").write_bytes(
    pathlib.Path("data/raw/hinge/HinGE.csv").read_bytes())   # the path the pipeline ingests
assert run([sys.executable, "scripts/validate_raw.py", "--only", "hinge", "--samples"]) == 0
""")

md("""
## 8. Build the splits, and prove they are the committed ones

The hashes printed below must match `data/processed/manifests/hinge_split_manifest.json` as
committed. If they do not, **stop**: the splits are not the ones the leakage gate cleared, and
nothing measured on them is comparable with anything else in the project.
""")
code("""
SOURCE = "hinge"
assert run([sys.executable, "scripts/run_pipeline.py",
            "--input", "data/raw/hinge.csv", "--seed", "42", "--no-figures"]) == 0

import json, subprocess
committed = json.loads(subprocess.run(
    ["git", "show", f"HEAD:data/processed/manifests/{SOURCE}_split_manifest.json"],
    capture_output=True, text=True, check=True).stdout)
fresh = json.loads(pathlib.Path(
    f"data/processed/manifests/{SOURCE}_split_manifest.json").read_text())

ok = True
print(f"{'split':<8}{'records':>9}{'committed sha':>18}{'this run':>18}  match")
for s in ("train", "dev", "test"):
    c, f = committed["splits"][s], fresh["splits"][s]
    same = c["sha256"] == f["sha256"] and c["records"] == f["records"]
    ok &= same
    print(f"{s:<8}{f['records']:>9}{c['sha256'][:16]:>18}{f['sha256'][:16]:>18}  {same}")
print("input sha256 match:", committed["input_sha256"] == fresh["input_sha256"])
assert ok and committed["input_sha256"] == fresh["input_sha256"], (
    "the splits this run produced are NOT the committed ones. Do not train on them.")
print("\\nsplits reproduce the committed manifest exactly")
""")

md("""
## 9. Build supervision and the evaluation files

`build_sft_data.py` verifies record counts and ids against the frozen manifest and refuses to
build from a split the leakage gate never cleared. It also writes
`data/sft/hinge/test_references.jsonl`, one entry per **source** carrying all of its references
— 197 sources over 468 references, mean 2.376 each.

Hypotheses are aligned to that file's order, which is what makes multi-reference scoring
possible. Section 4.4: *"The committed method is to score each source once, against all of its
references"*, because scoring per reference counts a five-reference source five times.
""")
code("""
assert run([sys.executable, "scripts/build_sft_data.py"]) == 0

import json, pathlib
out = pathlib.Path("out"); out.mkdir(exist_ok=True)

srcs = [json.loads(l)["english"]
        for l in open("data/sft/hinge/test_references.jsonl", encoding="utf-8") if l.strip()]
refs_path = "data/sft/hinge/test_references.jsonl"

if CFG["test_limit"]:
    srcs = srcs[:CFG["test_limit"]]
    # The reference file must be sliced to match, or scoring misaligns silently.
    kept = [l for l in open(refs_path, encoding="utf-8") if l.strip()][:CFG["test_limit"]]
    refs_path = "out/test_references.smoke.jsonl"
    pathlib.Path(refs_path).write_text("".join(kept), encoding="utf-8")

pathlib.Path("out/test.en.txt").write_text("\\n".join(srcs) + "\\n", encoding="utf-8")

# Few-shot examples come from TRAIN only, never dev or test. Split on tabs, not with the
# csv module: these files are written unquoted, and csv defaults merge 57 quote-bearing
# rows (tests/test_tsv_quoting.py).
with open("out/train.fewshot.tsv", "w", encoding="utf-8") as fh:
    for line in open(f"data/processed/{SOURCE}/train.tsv", encoding="utf-8").read().splitlines()[1:]:
        p = line.split("\\t")
        if len(p) >= 5 and p[2].strip() and p[4].strip():
            fh.write(f"{p[2]}\\t{p[4]}\\n")

print(f"test sources {len(srcs)} | references {refs_path}")
print("few-shot pool:", sum(1 for _ in open('out/train.fewshot.tsv', encoding='utf-8')), "rows")
""")

md("""
## 10. Model 1 — zero-shot (298-53)

0-shot and 5-shot are **separate conditions** and are reported separately: the success criterion
(+3 chrF++ over zero-shot with non-overlapping error bars) is defined against one of them, so
which is meant has to be unambiguous.
""")
code("""
import time
t0 = time.time()
for seed in CFG["seeds"]:
    assert run([sys.executable, "models/generate_zeroshot.py", "--src", "out/test.en.txt",
                "--out", f"out/m1.0shot.s{seed}.txt", "--model", CFG["model"],
                "--shots", "0", "--seed", seed]) == 0
print(f"\\n{time.time()-t0:.0f}s")
""")
code("""
for seed in CFG["seeds"]:
    assert run([sys.executable, "models/generate_zeroshot.py", "--src", "out/test.en.txt",
                "--out", f"out/m1.5shot.s{seed}.txt", "--model", CFG["model"],
                "--shots", "5", "--examples", "out/train.fewshot.tsv", "--seed", seed]) == 0
""")
code("""
label = "SMOKE, NOT REPORTABLE " if PROFILE == "smoke" else ""
for shots in ("0shot", "5shot"):
    hyps = [f"out/m1.{shots}.s{s}.txt" for s in CFG["seeds"]
            if pathlib.Path(f"out/m1.{shots}.s{s}.txt").exists()]
    if hyps:
        run([sys.executable, "evaluation/run_eval.py", "--hyp", *hyps,
             "--ref-jsonl", refs_path, "--bootstrap", 1000,
             "--system", f"{label}M1 {shots} {CFG['model']}",
             "--out", "results/results.jsonl"])
""")

md("""
## 11. Model 2 — QLoRA (298-54)

The recipe is fixed and must not be tuned here: rank 32, alpha 64, dropout 0.05, **all seven**
linear projections, LR 2e-4, 4-bit NF4 with double quantisation, loss masked to the completion.
M2 against M3 later has to isolate vocabulary and continued pretraining, which only works if
M2's recipe is held constant.

`--src-col 2 --tgt-col 4` are the `english` and `hinglish` columns of
`id, group, english, hindi, hinglish`.
""")
code("""
import shutil

for seed in CFG["seeds"]:
    local = pathlib.Path(f"out/m2-seed{seed}")

    # Where training writes. With PERSIST set, it writes STRAIGHT TO DRIVE, so the
    # intermediate checkpoints survive the runtime that produced them. Copying
    # afterwards -- what this cell used to do -- only protects a run that finished,
    # and a full epoch on a hosted T4 is longer than a hosted session.
    target = (PERSIST / local.name) if PERSIST else local

    if (target / "adapter_config.json").exists():
        if target != local:
            shutil.copytree(target, local, dirs_exist_ok=True)
        print(f"seed {seed}: finished adapter already in {target}, skipping training\\n")
        continue

    ckpts = sorted(target.glob("checkpoint-*"), key=lambda q: int(q.name.split("-")[1]))
    if ckpts:
        print(f"seed {seed}: unfinished run found, resuming from {ckpts[-1].name}")

    cmd = [sys.executable, "models/train_qlora.py",
           "--train", f"data/processed/{SOURCE}/train.tsv",
           "--src-col", 2, "--tgt-col", 4,
           "--out", target, "--model", CFG["model"], "--seed", seed,
           "--epochs", CFG["epochs"], "--batch-size", CFG["bsz"],
           "--grad-accum", CFG["accum"], "--max-len", CFG["maxlen"]]
    if CFG["train_limit"]: cmd += ["--limit", CFG["train_limit"]]
    if CFG["max_steps"]:   cmd += ["--max-steps", CFG["max_steps"]]
    if CFG["save_steps"]:  cmd += ["--save-steps", CFG["save_steps"], "--resume"]
    rc = run(cmd)
    assert rc == 0 and (target/"adapter_config.json").exists(), (
        f"training failed for seed {seed} -- read the stderr above; "
        f"runs/*model2-qlora_seed{seed}.json records the exception. Do not continue: "
        "the next cell would score an adapter that was never written.\\n"
        + (f"Checkpoints are in {target}; re-run this cell to resume from the newest."
           if CFG["save_steps"] else
           "This profile writes no checkpoints, so the run restarts from zero."))
    if target != local:
        shutil.copytree(target, local, dirs_exist_ok=True)
    print("adapter at", target)
""")
code("""
for seed in CFG["seeds"]:
    assert run([sys.executable, "models/generate_zeroshot.py", "--src", "out/test.en.txt",
                "--out", f"out/m2.s{seed}.txt", "--model", CFG["model"],
                "--adapter", f"out/m2-seed{seed}", "--shots", "0", "--seed", seed]) == 0

hyps2 = [f"out/m2.s{s}.txt" for s in CFG["seeds"] if pathlib.Path(f"out/m2.s{s}.txt").exists()]
hyps1 = [f"out/m1.0shot.s{s}.txt" for s in CFG["seeds"]
         if pathlib.Path(f"out/m1.0shot.s{s}.txt").exists()]

# --vs-hyp makes this a PAIRED bootstrap over test items, not two separate
# intervals compared by eye. Non-overlapping per-system intervals are weaker
# evidence than a paired test and the report has to say so if this is skipped.
cmd = [sys.executable, "evaluation/run_eval.py", "--hyp", *hyps2,
       "--ref-jsonl", refs_path, "--bootstrap", 1000,
       "--system", f"{label}M2 QLoRA NF4 {CFG['model']}", "--out", "results/results.jsonl"]
if hyps1:
    cmd += ["--vs-hyp", *hyps1, "--vs-system", f"{label}M1 0shot {CFG['model']}"]
run(cmd)
""")

md("""
## 12. Is M2 actually code-switching?

This is the cell the laptop run makes necessary. There, M2 beat M1 by 14.5 chrF++ **while its
code-mixing index fell from 15.40 to 11.88** against a human target of 25.86, and its
switch-point fraction more than halved. chrF++ cannot see that: English and Hinglish share most
of their English words, so a model that copies the source earns a respectable score against a
Hinglish reference.

Compare each system against both anchors. **A system near the English floor is not performing
the task, whatever its chrF++ says.**
""")
code("""
# Smoke writes somewhere else on purpose. This script's default output is
# reports/codemixing_systems.json, which holds the 7B numbers that
# reports/m1_m2_comparison.md cites -- and section 14 zips that file. A smoke run
# left on the default would put 48-sentence 0.5B numbers into the zip under the
# real file's name, and unzipping over the clone would silently replace the
# numbers the report quotes.
CM_OUT = ("out/codemixing_smoke.json" if PROFILE == "smoke"
          else "reports/codemixing_systems.json")

args = [sys.executable, "scripts/score_codemixing.py",
        "--sources", refs_path, "--out", CM_OUT]
for s in CFG["seeds"]:
    if pathlib.Path(f"out/m1.0shot.s{s}.txt").exists():
        args += ["--hyp", f"M1 0shot s{s}=out/m1.0shot.s{s}.txt"]
    if pathlib.Path(f"out/m2.s{s}.txt").exists():
        args += ["--hyp", f"M2 QLoRA s{s}=out/m2.s{s}.txt"]
run(args)
print("\\nwrote", CM_OUT)
""")

md("""
## 13. The comparison, and the laptop run to beat

Success criterion: **+3 chrF++ over zero-shot with non-overlapping error bars**, and three seeds
reported with their spread.
""")
code("""
run([sys.executable, "evaluation/run_eval.py", "--report", "results/results.jsonl"])

print("\\nThe MLX laptop run, for comparison (reports/m1_m2_comparison.md):")
print("  M1 zero-shot   chrF++ 43.270  [40.324, 46.461]   CMI 15.40   SPF 0.2007")
print("  M2 LoRA it500  chrF++ 57.808  [55.592, 60.026]   CMI 11.88   SPF 0.0951")
print("  paired diff    +14.538 [10.776, 18.241], p < 0.0001   (1 seed, ~0.16 epochs)")
print("  human target                                      CMI 25.86   SPF 0.2366")
print("\\nIf a full-epoch NF4 run on three seeds raises chrF++ AND moves CMI toward 25.86,")
print("the laptop regression was undertraining. If CMI stays low, it is the recipe, and that")
print("is a finding for section 4.3 rather than a problem to hide.")
""")

md("""
## 14. Collect what to commit

Download `commit_me.zip`, unzip it over your clone, and push on a branch. Keep the run records:
a number without one is not reportable.

`results/results.jsonl` is append-only, so unzipping it over the clone adds rows rather than
replacing them. On the smoke profile the code-mixing scores arrive as `out/codemixing_smoke.json`,
which is gitignored and cannot overwrite the 7B numbers `reports/m1_m2_comparison.md` quotes.
""")
code("""
import zipfile, json
z = pathlib.Path("/content/commit_me.zip")
# The generated text is the PRIMARY artefact: every score is derived from it,
# the qualitative reading in reports/m1_m2_comparison.md section 2 came from it,
# and re-scoring or a later paired test needs it. An earlier version of this cell
# zipped only the derived numbers, so the 11 November A100 outputs died with the
# runtime and cannot be re-examined. They are small -- 197 lines each.
outputs = sorted(pathlib.Path("out").glob("m1.*.txt")) + \
          sorted(pathlib.Path("out").glob("m2.*.txt"))
keep = sorted(pathlib.Path("runs").glob("*.json")) + outputs + [
    p for p in (pathlib.Path("results/results.jsonl"),
                pathlib.Path(CM_OUT),
                pathlib.Path("data/sft/hinge/manifest.json"),
                pathlib.Path("reports/raw_validation.json")) if p.exists()]
assert outputs, ("no generated outputs found in out/ -- the zip would carry scores "
                 "with nothing to verify them against")
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in keep:
        zf.write(p, p.as_posix()); print("+", p)

print("\\nGPU-hours this session:")
tot = 0.0
for p in sorted(pathlib.Path("runs").glob("*.json")):
    d = json.loads(p.read_text())
    h = d.get("gpu_hours", 0) or 0
    if h:
        tot += h
        print(f"  {str(d.get('name') or d.get('system'))[:34]:<36} seed {d.get('seed')}  {h:.3f} h")
print(f"  {'TOTAL':<36}         {tot:.3f} h")
if PROFILE == "smoke":
    print("\\nSMOKE profile: label every row [SMOKE, NOT REPORTABLE] before committing,")
    print("as results/results.jsonl already does for the 22 October runs.")

from google.colab import files; files.download(str(z))
""")

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")
print("wrote {} ({} cells: {} markdown, {} code)".format(
    OUT.relative_to(REPO_ROOT), len(cells),
    sum(1 for c in cells if c["cell_type"] == "markdown"),
    sum(1 for c in cells if c["cell_type"] == "code")))

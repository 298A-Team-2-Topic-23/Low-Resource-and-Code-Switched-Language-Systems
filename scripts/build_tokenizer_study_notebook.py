#!/usr/bin/env python3
"""
Generate notebooks/tokenizer_root_cause_study.ipynb.

The notebook is generated rather than hand-edited for the same reason the figures
are: a notebook nobody can regenerate cannot be checked against the repository it
claims to describe, and a hand-edited .ipynb accumulates stale output nobody
notices. Every code cell here is `ast.parse`d at build time, so a syntax error
cannot reach Colab.

What the notebook does, and why it is shaped this way
-----------------------------------------------------
It answers one question the Team Meeting 2 feedback asked for directly: **is the
cost of Romanized Hinglish a property of the script, of the lexicon, or of
compute?**

The project already measures two of those. What it has never done is separate
them *across tokenizers*, which is the measurement that decides whether the
bottleneck is fixable by choosing a different backbone. A two-tokenizer probe run
on 15 November found Devanagari fertility varying 3.10x (Qwen 4.636, mBART 1.493)
while spelling-variant burden varied 1.09x (1.832, 1.681). If that holds across a
wider panel it is the project's central result, and it is cheap: tokenizer
properties need no GPU.

The GPU half tests the link that matters. Burden varying across tokenizers is
only interesting if burden *predicts* downstream quality. Zero-shot generation
across N backbones gives N points for that correlation at inference cost only.

**On zero-shot.** It is used here as an instrument, not as a proposed model. The
feedback to drop prompting as a technique is accepted; measuring an untrained
backbone is how you read the tokenizer's effect before adaptation confounds it.

Usage
-----
  python3 scripts/build_tokenizer_study_notebook.py
  -> notebooks/tokenizer_root_cause_study.ipynb
"""

import argparse
import ast
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BRANCH = "main"
REPO = "https://github.com/298A-Team-2-Topic-23/Low-Resource-and-Code-Switched-Language-Systems.git"

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {},
                  "source": text.strip("\n").splitlines(keepends=True)})


def code(text):
    body = text.strip("\n")
    if not any(l.lstrip().startswith(("!", "%")) for l in body.splitlines()):
        ast.parse(body)          # fail the build, not the demonstration
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                  "outputs": [], "source": body.splitlines(keepends=True)})


# ----------------------------------------------------------------- 0. framing

md(f"""
# Where does the cost come from?

### A tokenizer-level root-cause study for Romanized Hinglish

**The question.** Quality drops on English→Romanized Hinglish. Three explanations compete:
the **script** the text is written in, the **lexicon** (one word, many spellings), and
**compute**. This notebook separates the first two across a panel of tokenizers, then tests
whether what it finds predicts downstream quality.

**Why this is the right experiment.** Script cost and spelling cost are both measurable without
training anything — they are properties of a tokenizer. If script cost varies across tokenizers
but spelling cost does not, then one problem is solved by picking a different backbone and the
other is not. That distinction decides what the rest of the project should work on.

**What is claimed and what is not.** Zero-shot generation is used here as an *instrument* for
reading a tokenizer's effect before adaptation confounds it. It is not proposed as a model.

**Structure.** Part A is CPU only and takes about a minute. Part B needs a GPU and is inference
only — no training. Part C scores and plots.

| Part | Needs GPU | What it produces |
|---|---|---|
| A — tokenizer panel | no | fertility and burden per tokenizer x slice; the decomposition |
| B — model panel | **yes** | per-byte NLL and zero-shot output per backbone |
| C — analysis | no | the burden-to-quality correlation, tables, figures |

Runtime → Change runtime type → **GPU** before Part B.
""")

# ----------------------------------------------------------- 1. provenance

md("""
## 1 · Provenance

Nothing below is reportable without this cell. It records what ran, on what, from which commit.
""")

code(f'''
import json, os, platform, subprocess, sys, time, textwrap
from datetime import datetime, timezone

RUN = {{"started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(), "platform": platform.platform()}}

try:
    import torch
    RUN["torch"] = torch.__version__
    RUN["cuda"] = torch.cuda.is_available()
    if torch.cuda.is_available():
        p = torch.cuda.get_device_properties(0)
        RUN["gpu"] = f"{{p.name}}, {{p.total_memory / 2**30:.1f}} GB, compute {{p.major}}.{{p.minor}}"
        # is_bf16_supported() counts EMULATED bf16 by default, so a T4 answers True
        # and then runs through a software path. Ask for native support only.
        try:
            RUN["bf16_native"] = torch.cuda.is_bf16_supported(including_emulation=False)
        except TypeError:
            RUN["bf16_native"] = torch.cuda.get_device_capability()[0] >= 8
    else:
        RUN["gpu"] = None
        print("No GPU. Part A still runs; Part B will stop with a clear message.")
except ImportError:
    RUN["torch"] = None
    print("torch not installed yet - the install cell below handles it.")

print(json.dumps(RUN, indent=2))
''')

# ------------------------------------------------------------- 2. the repo

md(f"""
## 2 · Clone and install

Pinned versions, for the reason recorded in `notebooks/m1_m2_colab.ipynb`: an unpinned
`transformers` resolves to 5.x in Colab and breaks `TrainingArguments`.
""")

code(f'''
import pathlib, subprocess, sys, os

REPO   = "{REPO}"
BRANCH = "{BRANCH}"
ROOT   = pathlib.Path("/content/lrcs")

if ROOT.exists():
    import shutil; shutil.rmtree(ROOT)      # a stale clone is silently the wrong branch
subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, REPO, str(ROOT)], check=True)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

HEAD = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
RUN["commit"] = HEAD
print("cwd:", os.getcwd(), "| HEAD:", HEAD[:12])

need = ("analysis/tokenizer_fertility.py", "evaluation/run_eval.py",
        "scripts/fetch_data.py", "analysis/spelling_variants.tsv",
        "src/lrcs/analysis/codemixing.py")
missing = [f for f in need if not pathlib.Path(f).exists()]
assert not missing, f"missing on this branch: {{missing}}"
print("all required sources present")
''')

code('''
%pip install -q "transformers==4.57.6" "tokenizers>=0.22" "sentencepiece==0.2.0" \\
               "sacrebleu==2.6.0" "bitsandbytes>=0.47" "accelerate==1.10.1" \\
               protobuf matplotlib

import transformers
print("transformers", transformers.__version__)
assert transformers.__version__.startswith("4."), (
    f"transformers {transformers.__version__} is loaded but 4.x is required.\\n"
    "Runtime -> Restart session, then run from the top. A pip install cannot replace a "
    "module this session has already imported.")
''')

# ------------------------------------------------------------- 3. the data

md("""
## 3 · Corpus and slices

`fetch_data.py` pulls HinGE at a pinned revision and verifies its SHA-256. The four slices are
the ones requirement AI-6 names: English, Devanagari Hindi, Romanized Hindi, Hinglish.
""")

code('''
def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], **kw).returncode

assert run([sys.executable, "scripts/fetch_data.py", "--only", "hinge"]) == 0
assert run([sys.executable, "scripts/fetch_data.py", "--verify", "--only", "hinge"]) == 0

import shutil
shutil.copyfile("data/raw/hinge/HinGE.csv", "data/raw/hinge.csv")

SLICES = {name: f"data/slices/{name}.txt"
          for name in ("en", "hi_deva", "hi_roman", "hinglish")}
for name, path in SLICES.items():
    n = sum(1 for _ in open(path, encoding="utf-8"))
    print(f"  {name:<10} {n:>6,} lines")

# hi_roman is a 30-line team fixture: no corpus here has a Romanised-Hindi column.
# It is kept because AI-6 names four slices, and flagged wherever it is used.
SMALL_SLICES = {n for n, p in SLICES.items()
                if sum(1 for _ in open(p, encoding="utf-8")) < 100}
if SMALL_SLICES:
    print(f"\\n  NOTE: {sorted(SMALL_SLICES)} under 100 lines - indicative, not corpus-grade.")
''')

# ------------------------------------------------------- 4. pre-registration

md("""
## 4 · Pre-registration

**Run this before looking at any result.** It writes the decision rules to disk so the
interpretation cannot drift to fit what came out. §4.4 of the report commits the project to this
practice; this is the same discipline applied to a new experiment.

The rules state what each outcome would *mean*, including the outcome that would weaken the
project's own hypothesis.
""")

code('''
DECISION_RULES = {
  "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
  "commit": RUN.get("commit"),
  "H1": {
    "claim": "Script cost is tokenizer-dependent; spelling cost is not.",
    "test":  "ratio of max/min across the panel, for hi_deva fertility vs spelling_variant_burden",
    "supports_H1":  "fertility ratio >= 2.0 AND burden ratio <= 1.25",
    "refutes_H1":   "burden ratio >= 2.0  (spelling cost is also a backbone choice)",
    "inconclusive": "anything else - reported as inconclusive, not reinterpreted",
  },
  "H2": {
    "claim": "Spelling burden predicts zero-shot quality across backbones.",
    "test":  "Spearman rho between spelling_variant_burden and zero-shot chrF++",
    "supports_H2":  "rho <= -0.6 with n >= 4 backbones",
    "refutes_H2":   "rho >= 0 (higher burden does not cost quality)",
    "inconclusive": "n < 4, or |rho| < 0.6 - a weak link is reported as weak",
  },
  "notes": [
    "n is small by construction. A correlation over 4-6 points is suggestive, not conclusive,",
    "and is reported that way whatever its sign.",
    "hi_roman is a 30-line fixture; H1 is judged on hi_deva, which is corpus-grade.",
  ],
}
pathlib.Path("out").mkdir(exist_ok=True)
pathlib.Path("out/decision_rules.json").write_text(
    json.dumps(DECISION_RULES, indent=2), encoding="utf-8")
print(json.dumps(DECISION_RULES, indent=2))
''')

# --------------------------------------------------- 5. Part A: tokenizers

md("""
---

# Part A · The tokenizer panel

CPU only. Tokenizers are a few megabytes each; no model weights are loaded.

Some backbones are **gated** on Hugging Face and need an accepted licence plus a token. The panel
records a skip with its reason rather than failing — a missing row is data about availability,
not a crash.
""")

code('''
# repo id -> short label. Open models first so the panel is never empty.
PANEL = {
    "Qwen/Qwen2.5-7B-Instruct":      "Qwen2.5-7B",      # the project's backbone
    "facebook/mbart-large-cc25":     "mBART-cc25",      # the reproduced baseline's model
    "google/mt5-base":               "mT5-base",        # multilingual, SentencePiece
    "bigscience/bloomz-560m":        "BLOOMZ",          # multilingual, includes Hindi
    "ai4bharat/IndicBARTSS":         "IndicBART",       # Indic-specialised
    "meta-llama/Llama-3.1-8B-Instruct": "Llama-3.1-8B", # gated: needs HF token
    "google/gemma-2-9b-it":          "Gemma-2-9B",      # gated: needs HF token
}

# Optional. Without it the two gated rows are skipped and the panel still stands.
HF_TOKEN = os.environ.get("HF_TOKEN") or ""
if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN
    print("HF token present - gated models will be attempted.")
else:
    print("No HF_TOKEN set. Gated models will be skipped with a recorded reason.\\n"
          "To include them: accept the licence on huggingface.co, then set\\n"
          '  os.environ["HF_TOKEN"] = "hf_..."  and re-run this cell.')
''')

code('''
from transformers import AutoTokenizer

def load_tokenizer(repo):
    """Return (tokenizer, None) or (None, reason). A gate is data, not an error."""
    try:
        kw = {"trust_remote_code": False}
        if HF_TOKEN:
            kw["token"] = HF_TOKEN
        return AutoTokenizer.from_pretrained(repo, **kw), None
    except Exception as exc:                      # noqa: BLE001 - we want the reason
        msg = str(exc).split("\\n")[0][:140]
        kind = ("gated / needs licence acceptance" if "gated" in msg.lower()
                or "401" in msg or "403" in msg else type(exc).__name__)
        return None, f"{kind}: {msg}"

AVAILABLE, SKIPPED = {}, {}
for repo, label in PANEL.items():
    tok, why = load_tokenizer(repo)
    if tok is None:
        SKIPPED[label] = why
        print(f"  skip  {label:<14} {why[:88]}")
    else:
        AVAILABLE[repo] = label
        print(f"  ok    {label:<14} vocab {len(tok):,}")
    del tok

assert len(AVAILABLE) >= 2, "need at least two tokenizers for a comparison"
print(f"\\n{len(AVAILABLE)} available, {len(SKIPPED)} skipped")
''')

code('''
# Reuse the project's own measurement rather than reimplementing it: the same
# definitions produced every fertility number already in the report.
cmd = [sys.executable, "analysis/tokenizer_fertility.py"]
for name, path in SLICES.items():
    cmd += ["--corpus", f"{name}={path}"]
for repo in AVAILABLE:
    cmd += ["--tokenizer", repo]
cmd += ["--out", "out/fertility_panel.csv"]

t0 = time.time()
assert run(cmd) == 0, "fertility panel failed"
print(f"\\npanel computed in {time.time() - t0:.1f}s on CPU")
''')

code('''
import csv, collections

rows = list(csv.DictReader(open("out/fertility_panel.csv", encoding="utf-8")))
LABEL = dict(AVAILABLE)
P = collections.defaultdict(dict)
for r in rows:
    P[LABEL.get(r["tokenizer"], r["tokenizer"])][r["slice"]] = r

def val(label, slice_, field):
    return float(P[label][slice_][field])

hdr = f"{'tokenizer':<14}{'burden':>9}{'en':>8}{'hi_deva':>9}{'hi_roman':>10}{'hinglish':>10}{'deva/en':>9}"
print(hdr); print("-" * len(hdr))
for label in P:
    b  = val(label, "en", "spelling_variant_burden")
    en = val(label, "en", "fertility")
    hd = val(label, "hi_deva", "fertility")
    hr = val(label, "hi_roman", "fertility")
    hg = val(label, "hinglish", "fertility")
    print(f"{label:<14}{b:>9.3f}{en:>8.3f}{hd:>9.3f}{hr:>10.3f}{hg:>10.3f}{hd/en:>8.2f}x")
''')

# ------------------------------------------------- 6. the decomposition

md("""
## 6 · The decomposition

The claim under test: **script cost moves with the tokenizer, spelling cost does not.**

Fertility is a per-slice property and compares tokenizers directly. Burden is computed from the
72-group spelling lexicon and needs no corpus, so it is comparable across tokenizers by
construction. Both ratios are max/min across the panel.
""")

code('''
import statistics as st

deva  = {l: val(l, "hi_deva", "fertility") for l in P}
hing  = {l: val(l, "hinglish", "fertility") for l in P}
burd  = {l: val(l, "en", "spelling_variant_burden") for l in P}

def spread(d):
    lo, hi = min(d.values()), max(d.values())
    return hi / lo, min(d, key=d.get), max(d, key=d.get)

r_deva, lo_d, hi_d = spread(deva)
r_hing, lo_h, hi_h = spread(hing)
r_burd, lo_b, hi_b = spread(burd)

print(f"Devanagari fertility   {r_deva:>5.2f}x  ({lo_d} {deva[lo_d]:.3f} -> {hi_d} {deva[hi_d]:.3f})")
print(f"Hinglish fertility     {r_hing:>5.2f}x  ({lo_h} {hing[lo_h]:.3f} -> {hi_h} {hing[hi_h]:.3f})")
print(f"Spelling burden        {r_burd:>5.2f}x  ({lo_b} {burd[lo_b]:.3f} -> {hi_b} {burd[hi_b]:.3f})")

rule = DECISION_RULES["H1"]
if r_deva >= 2.0 and r_burd <= 1.25:
    verdict = "SUPPORTS H1: script cost is a backbone choice; spelling cost is not."
elif r_burd >= 2.0:
    verdict = "REFUTES H1: spelling cost is also a backbone choice."
else:
    verdict = "INCONCLUSIVE under the pre-registered rule. Reported as such."
print("\\n" + "=" * 78); print(verdict); print("=" * 78)

H1 = {"deva_ratio": r_deva, "hinglish_ratio": r_hing, "burden_ratio": r_burd,
      "verdict": verdict, "n_tokenizers": len(P), "rule": rule}
pathlib.Path("out/h1_decomposition.json").write_text(json.dumps(H1, indent=2), encoding="utf-8")
''')

code('''
# Which spellings are expensive, and is that consistent across tokenizers?
# A cost that every tokenizer pays is a property of the writing system, not of one vendor.
var_rows = list(csv.DictReader(open("out/fertility_panel.variants.csv", encoding="utf-8")))
by_group = collections.defaultdict(dict)
for r in var_rows:
    lab = LABEL.get(r["tokenizer"], r["tokenizer"])
    key = r.get("group") or r.get("canonical") or r.get("word")
    cost = r.get("mean_tokens") or r.get("tokens_per_form") or r.get("burden")
    if key and cost:
        by_group[key][lab] = float(cost)

universal = {g: v for g, v in by_group.items() if len(v) == len(P)}
if universal:
    ranked = sorted(universal.items(), key=lambda kv: -st.mean(kv[1].values()))
    print(f"{'group':<14}{'mean':>7}{'min':>7}{'max':>7}   paid by every tokenizer?")
    print("-" * 62)
    for g, v in ranked[:12]:
        m, lo, hi = st.mean(v.values()), min(v.values()), max(v.values())
        print(f"{g:<14}{m:>7.2f}{lo:>7.2f}{hi:>7.2f}   {'yes' if lo > 1.01 else 'no'}")
    paid_by_all = sum(1 for _, v in universal.items() if min(v.values()) > 1.01)
    print(f"\\n{paid_by_all} of {len(universal)} groups cost more than one token on EVERY tokenizer.")
else:
    print("variant-level detail not available in this build of the fertility tool")
''')

# ------------------------------------------------------ 7. Part B: GPU

md("""
---

# Part B · The model panel  ·  needs a GPU

Part A establishes how tokenizers differ. **That only matters if the difference reaches
downstream quality**, which is what this part measures.

Two measurements per backbone, both inference only:

1. **Per-byte negative log-likelihood** on the Hinglish test references. Per-*token* NLL is not
   comparable across models with different vocabularies — per-byte is, which is why requirement
   AI-7 commits to it. This is the measurement that links a tokenizer property to model
   behaviour without any training.
2. **Zero-shot chrF++** on the same test set, as the instrument described at the top.

Models load sequentially in 4-bit and are freed between runs. Budget roughly 5–8 minutes each on
a T4, less on an A100.
""")

code('''
import torch, gc

if not torch.cuda.is_available():
    raise SystemExit(
        "Part B needs a GPU.\\n"
        "Runtime -> Change runtime type -> GPU, then run from the top.\\n"
        "Part A's results are already written to out/ and are complete without this.")

# 7B at 4-bit is ~4.5 GB; a 16 GB T4 holds one at a time comfortably.
GEN_PANEL = [r for r in AVAILABLE if any(
    k in r for k in ("Qwen2.5-7B", "Llama-3.1-8B", "gemma-2-9b", "bloomz"))]
print("backbones for generation:", [AVAILABLE[r] for r in GEN_PANEL])
if len(GEN_PANEL) < 2:
    print("\\nWARNING: fewer than 2 generative backbones available. H2 needs n>=4 to be "
          "anything more than anecdote; the verdict cell will say so.")
''')

code('''
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

QUANT = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                           bnb_4bit_use_double_quant=True,
                           bnb_4bit_compute_dtype=torch.float16)

def free(*objs):
    for o in objs:
        del o
    gc.collect(); torch.cuda.empty_cache()

def load_causal(repo):
    kw = {"quantization_config": QUANT, "device_map": "auto",
          "torch_dtype": torch.float16}
    if HF_TOKEN:
        kw["token"] = HF_TOKEN
    tok = AutoTokenizer.from_pretrained(repo, **({"token": HF_TOKEN} if HF_TOKEN else {}))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    return AutoModelForCausalLM.from_pretrained(repo, **kw), tok

@torch.no_grad()
def per_byte_nll(model, tok, lines, limit=200):
    """Sum NLL over a corpus, divided by its length in BYTES.

    Per-token NLL rewards a tokenizer that simply uses fewer, longer tokens.
    Per-byte does not: the denominator is the text itself, identical for every
    model, so two models with different vocabularies become comparable.
    """
    total_nll, total_bytes = 0.0, 0
    for line in lines[:limit]:
        line = line.strip()
        if not line:
            continue
        ids = tok(line, return_tensors="pt").input_ids.to(model.device)
        if ids.shape[1] < 2:
            continue
        out = model(ids, labels=ids)
        total_nll += out.loss.item() * (ids.shape[1] - 1)
        total_bytes += len(line.encode("utf-8"))
    return total_nll / total_bytes if total_bytes else float("nan")
''')

code('''
SYSTEM = ("You translate English into Hinglish: conversational Hindi-English code-mixed text "
          "written in the Roman alphabet. Keep common English words in English. Never use "
          "Devanagari script. Reply with the translation only.")

@torch.no_grad()
def zero_shot(model, tok, sources, max_new_tokens=96):
    outs = []
    for src in sources:
        msgs = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Translate to Hinglish:\\n{src}"}]
        try:
            prompt = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                             tokenize=False)
        except Exception:                      # no chat template: fall back to plain
            prompt = f"{SYSTEM}\\n\\nEnglish: {src}\\nHinglish:"
        ids = tok(prompt, return_tensors="pt").to(model.device)
        gen = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=tok.pad_token_id)
        text = tok.decode(gen[0][ids.input_ids.shape[1]:], skip_special_tokens=True)
        outs.append(next((l.strip() for l in text.strip().splitlines() if l.strip()), ""))
    return outs
''')

code('''
# Test sources and their reference sets, built from the frozen splits.
assert run([sys.executable, "scripts/run_pipeline.py", "--input", "data/raw/hinge.csv",
            "--seed", "42", "--no-figures"]) == 0
assert run([sys.executable, "scripts/build_sft_data.py"]) == 0

REFS_PATH = "data/sft/hinge/test_references.jsonl"
refs_recs = [json.loads(l) for l in open(REFS_PATH, encoding="utf-8") if l.strip()]
SOURCES  = [r["english"] for r in refs_recs]
HINGLISH = [l.strip() for l in open(SLICES["hinglish"], encoding="utf-8") if l.strip()]
print(f"{len(SOURCES)} test sources, {sum(len(r['references']) for r in refs_recs)} references")

N_SOURCES = int(os.environ.get("N_SOURCES", len(SOURCES)))   # lower it for a smoke pass
SOURCES_RUN = SOURCES[:N_SOURCES]
pathlib.Path("out/test.en.txt").write_text("\\n".join(SOURCES_RUN) + "\\n", encoding="utf-8")
if N_SOURCES < len(SOURCES):
    kept = [l for l in open(REFS_PATH, encoding="utf-8") if l.strip()][:N_SOURCES]
    REFS_PATH = "out/test_references.subset.jsonl"
    pathlib.Path(REFS_PATH).write_text("".join(kept), encoding="utf-8")
    print(f"NOTE: running on a {N_SOURCES}-source subset - not the reportable test set.")
''')

code('''
MODEL_RESULTS = {}
for repo in GEN_PANEL:
    label = AVAILABLE[repo]
    print(f"\\n=== {label} ===")
    t0 = time.time()
    try:
        model, tok = load_causal(repo)
    except Exception as exc:                   # noqa: BLE001
        print(f"  load failed: {str(exc).splitlines()[0][:120]}")
        SKIPPED[label] = f"load failed: {type(exc).__name__}"
        continue
    load_s = time.time() - t0

    t1 = time.time(); nll = per_byte_nll(model, tok, HINGLISH); nll_s = time.time() - t1
    print(f"  per-byte NLL {nll:.4f}   ({nll_s:.0f}s)")

    t2 = time.time(); hyps = zero_shot(model, tok, SOURCES_RUN); gen_s = time.time() - t2
    out_path = f"out/zeroshot.{label.replace('/', '_')}.txt"
    pathlib.Path(out_path).write_text("\\n".join(hyps) + "\\n", encoding="utf-8")
    print(f"  generated {len(hyps)} lines ({gen_s:.0f}s) -> {out_path}")
    print(f"  sample: {hyps[0][:90]}")

    MODEL_RESULTS[label] = {
        "repo": repo, "per_byte_nll": nll, "hyp_file": out_path,
        "seconds": {"load": round(load_s, 1), "nll": round(nll_s, 1), "gen": round(gen_s, 1)},
        "gpu_hours": round((load_s + nll_s + gen_s) / 3600, 4),
    }
    free(model, tok)

pathlib.Path("out/model_panel.json").write_text(
    json.dumps(MODEL_RESULTS, indent=2), encoding="utf-8")
print(f"\\n{len(MODEL_RESULTS)} backbones measured, "
      f"{sum(v['gpu_hours'] for v in MODEL_RESULTS.values()):.3f} GPU-hours")
''')

# ----------------------------------------------- 8. Part C: metric suite

md("""
---

# Part C · Scoring, with a wider metric suite

The feedback asked for more than chrF++. Each metric below answers a different question about the
*same* output, which is the point — a single scalar cannot separate "wrong word" from "wrong
spelling" from "wrong meaning".

| Metric | What it isolates | Direction |
|---|---|---|
| **chrF++** | character n-gram overlap, primary | higher |
| chrF++ normalised | the same with spelling variants collapsed | higher |
| **spelling gap** = normalised − raw | **how much of the error is orthographic, not semantic** | lower is better |
| BLEU | exact word match; understates here by design | higher |
| ROUGE-L | longest common subsequence, recall-leaning | higher |
| WER | word-level edit operations | lower |
| **TER** | edit operations normalised by reference length | lower |
| **CMI / SPF / M-index** | is it code-switching *like a person*, not just scoring well | toward human |
| **per-byte NLL** | model cost, comparable across vocabularies | lower |

The spelling gap is the one worth watching: it is this project's own instrument for separating
orthographic error from semantic error, and it is why normalised chrF++ exists.
""")

code('''
from sacrebleu.metrics import CHRF, BLEU, TER

_chrf, _bleu, _ter = CHRF(word_order=2), BLEU(), TER()

sys.path.insert(0, str(pathlib.Path("evaluation").resolve()))
import run_eval                                     # the project's committed harness
from lrcs.analysis.codemixing import cmi, spf, m_index, LANG_TAGS
from lrcs.data.clean import hindi_markers, tag_tokens
from lrcs.lexicon import load_variant_groups

MARKERS = hindi_markers(load_variant_groups("analysis/spelling_variants.tsv"))
REF_SETS = [r["references"] for r in refs_recs][:len(SOURCES_RUN)]

def ref_streams(sets):
    width = max(len(s) for s in sets)
    return [[(s[i] if i < len(s) else None) for s in sets] for i in range(width)]

STREAMS = ref_streams(REF_SETS)

def score_system(hyps, sources):
    """Every metric for one system. Multi-reference where the metric supports it."""
    out = {}
    out["chrf++"] = _chrf.corpus_score(hyps, STREAMS).score
    out["bleu"]   = _bleu.corpus_score(hyps, STREAMS).score
    # TER and ROUGE-L/WER take the best-matching reference per item, as section 4.4 commits.
    out["ter"]    = st.mean([min(_ter.sentence_score(h, s).score for s in sets)
                             for h, sets in zip(hyps, REF_SETS)])
    norm_h = [run_eval.normalise(h) for h in hyps]
    norm_s = [[run_eval.normalise(r) for r in s] for s in REF_SETS]
    out["chrf++_norm"] = _chrf.corpus_score(norm_h, ref_streams(norm_s)).score
    out["spelling_gap"] = out["chrf++_norm"] - out["chrf++"]
    # code-mixing: is it switching like a person?
    tagged = [[t for _, t in tag_tokens(h, s, MARKERS)] for h, s in zip(hyps, sources)]
    out["cmi"] = st.mean([cmi(t) for t in tagged])
    spfs = [spf(t) for t in tagged if spf(t) is not None]
    out["spf"] = st.mean(spfs) if spfs else float("nan")
    out["m_index"] = st.mean([m_index(t) for t in tagged])
    resolved = sum(sum(1 for x in t if x in LANG_TAGS) for t in tagged)
    words    = sum(sum(1 for x in t if x != "punct") for t in tagged)
    out["tagger_coverage"] = resolved / words if words else float("nan")
    out["devanagari_outputs"] = sum(
        1 for h in hyps if any("\\u0900" <= c <= "\\u097f" for c in h))
    return out

# Human references as the target, and the English source as the floor.
HUMAN = [s[0] for s in REF_SETS]
print("anchors computed on the same scorer:")
for name, hyps in (("human reference", HUMAN), ("English source (floor)", SOURCES_RUN)):
    s = score_system(hyps, SOURCES_RUN)
    print(f"  {name:<24} CMI {s['cmi']:>6.2f}  SPF {s['spf']:>6.4f}  M {s['m_index']:>6.4f}")
''')

code('''
SCORES = {}
for label, info in MODEL_RESULTS.items():
    hyps = [l.rstrip("\\n") for l in open(info["hyp_file"], encoding="utf-8")]
    hyps = (hyps + [""] * len(SOURCES_RUN))[:len(SOURCES_RUN)]
    s = score_system(hyps, SOURCES_RUN)
    s["per_byte_nll"] = info["per_byte_nll"]
    s["burden"] = burd.get(label, float("nan"))
    s["hinglish_fertility"] = hing.get(label, float("nan"))
    SCORES[label] = s

cols = ["chrf++", "chrf++_norm", "spelling_gap", "bleu", "ter", "cmi", "spf",
        "per_byte_nll", "burden"]
hdr = f"{'backbone':<14}" + "".join(f"{c:>14}" for c in cols)
print(hdr); print("-" * len(hdr))
for label, s in sorted(SCORES.items(), key=lambda kv: -kv[1]["chrf++"]):
    print(f"{label:<14}" + "".join(f"{s[c]:>14.3f}" for c in cols))

pathlib.Path("out/scores.json").write_text(json.dumps(SCORES, indent=2), encoding="utf-8")
''')

# ------------------------------------------------------- 9. H2 verdict

md("""
## 9 · Does burden predict quality?

The pre-registered rule is Spearman ρ ≤ −0.6 with n ≥ 4 to support H2. **n is small by
construction** — one point per backbone — so this is reported as suggestive whatever it shows.
A bootstrap interval over backbones is included to make the fragility visible rather than
implied.
""")

code('''
import random

def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1.0
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")

labels = [l for l in SCORES if not (SCORES[l]["burden"] != SCORES[l]["burden"])]
x = [SCORES[l]["burden"] for l in labels]
y = [SCORES[l]["chrf++"] for l in labels]
n = len(labels)

if n >= 3:
    rho = spearman(x, y)
    rng = random.Random(12345)
    boot = []
    for _ in range(2000):
        idx = [rng.randrange(n) for _ in range(n)]
        if len(set(idx)) > 2:
            boot.append(spearman([x[i] for i in idx], [y[i] for i in idx]))
    boot.sort()
    lo, hi = boot[int(0.025 * len(boot))], boot[int(0.975 * len(boot))]
    print(f"n = {n} backbones")
    print(f"Spearman rho(burden, chrF++) = {rho:+.3f}   95% CI [{lo:+.3f}, {hi:+.3f}]")
    rho_nll = spearman([SCORES[l]["per_byte_nll"] for l in labels], y)
    print(f"Spearman rho(per-byte NLL, chrF++) = {rho_nll:+.3f}")

    if n >= 4 and rho <= -0.6:
        v = "SUPPORTS H2: higher spelling burden tracks lower zero-shot quality."
    elif rho >= 0:
        v = "REFUTES H2: burden does not cost quality in this panel."
    else:
        v = f"INCONCLUSIVE under the pre-registered rule (n={n}, rho={rho:+.3f})."
    print("\\n" + "=" * 78); print(v); print("=" * 78)
    print("\\nn is small by construction. Read this as a direction, not a coefficient.")
    pathlib.Path("out/h2_correlation.json").write_text(json.dumps(
        {"n": n, "labels": labels, "rho_burden_chrf": rho, "ci95": [lo, hi],
         "rho_nll_chrf": rho_nll, "verdict": v}, indent=2), encoding="utf-8")
else:
    print(f"Only {n} backbones scored - too few for a correlation. Reported as not tested.")
''')

# ----------------------------------------------------------- 10. figures

md("""
## 10 · Figures

Two figures, each making one claim. Exported at 150 dpi for the deck and the report.
""")

code('''
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, MUTED, ACC, WARN = "#16161a", "#5a5a66", "#2a5db0", "#b4420f"
SURFACE, GRID = "#fbfbfd", "#e2e2e8"

# --- Figure 1: the decomposition -------------------------------------------
labels_f = list(P)
fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150)
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
xs = range(len(labels_f))
w = 0.26
ax.bar([i - w for i in xs], [deva[l] for l in labels_f], w, label="Devanagari Hindi",
       color=WARN, zorder=3)
ax.bar(list(xs),            [hing[l] for l in labels_f], w, label="Hinglish (Roman)",
       color=ACC, zorder=3)
ax.bar([i + w for i in xs], [burd[l] for l in labels_f], w, label="spelling-variant burden",
       color="#6b6b76", zorder=3)
ax.set_xticks(list(xs)); ax.set_xticklabels(labels_f, fontsize=9)
ax.set_ylabel("tokens per word  /  per spelling", fontsize=10, color=INK)
ax.set_title("Script cost moves with the tokenizer. Spelling cost does not.",
             fontsize=13, color=INK, pad=14, loc="left")
ax.text(0, 1.015, f"Devanagari varies {r_deva:.2f}x across the panel; burden varies "
        f"{r_burd:.2f}x.  n = {len(P)} tokenizers, CPU only.",
        transform=ax.transAxes, fontsize=8.5, color=MUTED)
ax.grid(axis="y", color=GRID, zorder=0); ax.set_axisbelow(True)
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig("out/fig_decomposition.png", facecolor=SURFACE)
print("wrote out/fig_decomposition.png")
plt.close(fig)
''')

code('''
# --- Figure 2: burden against quality --------------------------------------
if len(SCORES) >= 3:
    fig, ax = plt.subplots(figsize=(8.4, 5.2), dpi=150)
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    for l in SCORES:
        if SCORES[l]["burden"] == SCORES[l]["burden"]:
            ax.scatter(SCORES[l]["burden"], SCORES[l]["chrf++"], s=90, color=ACC, zorder=3)
            ax.annotate(l, (SCORES[l]["burden"], SCORES[l]["chrf++"]),
                        textcoords="offset points", xytext=(8, 4),
                        fontsize=9, color=INK)
    ax.set_xlabel("spelling-variant burden  (tokens per spelling)", fontsize=10)
    ax.set_ylabel("zero-shot chrF++", fontsize=10)
    ax.set_title("Does a costlier tokenizer produce worse Hinglish?",
                 fontsize=13, color=INK, pad=14, loc="left")
    sub = (f"Spearman rho = {rho:+.3f}, 95% CI [{lo:+.3f}, {hi:+.3f}], n = {n}. "
           "Zero-shot is an instrument here, not a proposed model.")
    ax.text(0, 1.015, sub, transform=ax.transAxes, fontsize=8.5, color=MUTED)
    ax.grid(color=GRID, zorder=0); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig("out/fig_burden_vs_quality.png", facecolor=SURFACE)
    print("wrote out/fig_burden_vs_quality.png")
    plt.close(fig)
else:
    print("fewer than 3 scored backbones - correlation figure skipped")
''')

# ------------------------------------------------------------- 11. export

md("""
## 11 · Export

One zip, with a manifest recording what ran, on what hardware, from which commit, and which
tokenizers were unavailable and why. A result without that is not reportable.
""")

code('''
RUN["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
RUN["tokenizers_available"] = list(AVAILABLE.values())
RUN["tokenizers_skipped"] = SKIPPED
RUN["n_sources_scored"] = len(SOURCES_RUN)
RUN["gpu_hours"] = round(sum(v["gpu_hours"] for v in MODEL_RESULTS.values()), 4)
RUN["decision_rules"] = DECISION_RULES
pathlib.Path("out/run_manifest.json").write_text(json.dumps(RUN, indent=2), encoding="utf-8")

import zipfile
z = pathlib.Path("/content/tokenizer_study.zip")
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(pathlib.Path("out").rglob("*")):
        if p.is_file():
            zf.write(p, p.as_posix()); print("  +", p)

print(f"\\n{z}  ({z.stat().st_size / 1024:.0f} KB)")
print(f"GPU-hours this session: {RUN['gpu_hours']:.4f}")
if SKIPPED:
    print("\\nUnavailable, recorded rather than hidden:")
    for k, v in SKIPPED.items():
        print(f"  {k:<14} {v[:92]}")

try:
    from google.colab import files
    files.download(str(z))
except Exception:
    print("\\n(not in Colab - download out/ manually)")
''')

md("""
---

## What to take from this

Read the two verdict cells, not the prettiest number.

- **H1** says whether the script problem and the spelling problem are the same kind of problem.
  If script cost varies across tokenizers and spelling cost does not, then one is a procurement
  decision and the other is a research problem — and the project is about the second.
- **H2** says whether that research problem actually costs quality. With n of 4–6 it is a
  direction, not a coefficient, and the bootstrap interval is there to keep you honest about it.

If either comes out against the hypothesis, that is the result. The rules were written to disk
before the numbers existed, so there is nothing to argue with.
""")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", default=str(REPO_ROOT / "notebooks" /
                                        "tokenizer_root_cause_study.ipynb"))
    args = p.parse_args(argv)

    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                      "name": "python3"},
                       "language_info": {"name": "python"},
                       "accelerator": "GPU", "colab": {"provenance": []}},
          "nbformat": 4, "nbformat_minor": 5}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8")
    n_md = sum(1 for c in cells if c["cell_type"] == "markdown")
    print(f"wrote {out} ({len(cells)} cells: {n_md} markdown, {len(cells) - n_md} code)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

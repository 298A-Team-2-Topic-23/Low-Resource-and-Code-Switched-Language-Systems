# Notebooks

Three notebooks, with different jobs. Only the first is meant to be *read*; the other two are
meant to be *run* on a GPU.

## `tm1_data_pipeline_demo.ipynb` — the walkthrough notebook (298-44)

Runs the team pipeline (`src/lrcs`, the same code as `scripts/run_pipeline.py`) one stage per
section on the real HinGE corpus: extraction, cleaning (missing values, transformations,
validation), splits with the leakage gate, and EDA with every figure.

It is committed **with outputs** from the real-corpus run, so it reads on GitHub without being
run. Section 3 compares its split hashes against
`data/processed/manifests/hinge_split_manifest.json`, so a re-run shows directly whether it
reproduced the committed splits byte for byte. Section 5 runs the test suite in-notebook.

To re-run it:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-demo.txt notebook
python scripts/fetch_data.py --only hinge     # downloads HinGE at a pinned revision, SHA-256 verified
jupyter notebook notebooks/tm1_data_pipeline_demo.ipynb      # Kernel -> Restart & Run All
```

Running it writes only to `out/notebook_run/` (gitignored) and never modifies the committed
`reports/`.

## `m1_m2_colab.ipynb` — Models 1 and 2 on a GPU (298-53, 298-54)

The spec-faithful `bitsandbytes` NF4 QLoRA run, which is CUDA-only and so cannot run on the
laptop. Open in Colab, set the runtime to GPU, run top to bottom. It clones this repository,
fetches and validates the corpus, verifies the regenerated splits against the committed manifest
hashes, builds supervision, then runs M1 and M2 and scores both with multi-reference chrF++ and
the code-mixing metrics.

Committed **without outputs**, because it has not been run on a GPU yet. The laptop results it
exists to reproduce and extend are in [`reports/m1_m2_comparison.md`](../reports/m1_m2_comparison.md);
the notebook prints those numbers as the target to beat.

Start with `PROFILE = "smoke"` (~3 minutes, 0.5B stand-in) before any long run, and set
`PERSIST_DIR` to a Drive path so a disconnect does not lose the adapters.

## `baseline_gahoi_colab.ipynb` — the published baseline (298-52)

Gahoi et al. (2022). See the correction note in section 4: the MixMT Subtask-1 test references
were never publicly released, so the reproduction target is CMU Hinglish DoG instead. The
reasoning and the published numbers are in [`docs/baseline_reproduction.md`](../docs/baseline_reproduction.md).
Also committed without outputs.

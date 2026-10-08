# Notebooks

`tm1_data_pipeline_demo.ipynb` (298-44) runs the team pipeline (`src/lrcs`, the same code as
`scripts/run_pipeline.py`) one stage per section on the real HinGE corpus: conversion, extraction,
cleaning (missing values, transformations, validation), splits with the leakage gate, and EDA.

It is committed **with outputs** from the real-corpus run, so it reads on GitHub without being run.
To re-run it:

```bash
pip install -r requirements-demo.txt notebook
# put the authors' HinGE.pkl (or a converted hinge.csv) in data/raw/ -- see docs/datasheet.md
jupyter notebook notebooks/tm1_data_pipeline_demo.ipynb      # Kernel -> Restart & Run All
```

Running it writes only to `out/notebook_run/` (gitignored) and never modifies the committed `reports/`.
Its split hashes are compared against `data/processed/manifests/hinge_split_manifest.json`, so a re-run
shows directly whether it reproduced the committed splits.

# Tests

Everything automated lives here, so one command runs the whole suite:

```bash
python -m pytest tests/
```

`conftest.py` at the repository root puts the root and `common/` on the import
path, which is why a test can do `from human_eval.agreement import ...` or
`from repro import set_seed` without any `__init__.py` files, an installed
package, or a per-file `sys.path` shim.

Scripts that carry their own `--selftest` are checked separately, because they
verify numbers rather than code paths and are meant to be runnable on a cluster
node with nothing installed:

```bash
python common/repro.py --selftest
python analysis/tokenizer_fertility.py --selftest
```

Neither needs a GPU, a model download, or any dataset.

# 298-70 — source-to-warehouse demo entry points.
# Prefer these over remembering flag combinations. Gate failure (exit 3) means
# no manifest and no warehouse load; do not bypass it.

PYTHON ?= python3
SEED ?= 42
N_SYNTHETIC ?= 1200
DB ?= data/warehouse/lrcs.sqlite
STATS ?= reports/data_statistics.json

.PHONY: pipeline-synthetic warehouse warehouse-demo monitor demo-298-70 test-warehouse help

help:
	@echo "Targets:"
	@echo "  pipeline-synthetic  run the four-stage pipeline offline"
	@echo "  warehouse           load pipeline outputs into SQLite"
	@echo "  warehouse-demo      print the six demo SQL queries"
	@echo "  monitor             write reports/pipeline_monitor.json"
	@echo "  demo-298-70         pipeline -> load -> queries -> monitor"
	@echo "  test-warehouse      pytest for the warehouse package"

pipeline-synthetic:
	$(PYTHON) scripts/run_pipeline.py --synthetic --n-synthetic $(N_SYNTHETIC) --seed $(SEED)

warehouse:
	$(PYTHON) scripts/load_warehouse.py --stats $(STATS) --db $(DB)

warehouse-demo:
	$(PYTHON) scripts/warehouse_demo.py --db $(DB)

monitor:
	$(PYTHON) scripts/monitor_pipeline.py --stats $(STATS) --out reports/pipeline_monitor.json

demo-298-70: pipeline-synthetic warehouse warehouse-demo monitor
	@echo "demo-298-70 OK"

test-warehouse:
	$(PYTHON) -m pytest tests/test_warehouse.py -q

demo:  ## ISA row 5: live prototype, audience picks the input (http://127.0.0.1:8000)
	$(PYTHON) scripts/serve_demo.py --warm

demo-light:  ## same, M2 only -- about half the memory
	$(PYTHON) scripts/serve_demo.py --warm --no-m1

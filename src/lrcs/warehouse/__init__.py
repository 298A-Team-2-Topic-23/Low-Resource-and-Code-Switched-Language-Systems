"""SQLite warehouse for the source-to-warehouse demo.  [298-70]

The four-stage pipeline still writes local files. This package loads those
outputs into a queryable store so the rubric's "data warehouse" and the Team
Meeting 2 demo have something to point at. The database holds sentences and is
gitignored; only the schema, the loader and the aggregate monitor report are
committed.
"""

from lrcs.warehouse.schema import DEFAULT_DB_PATH, SCHEMA_SQL, connect, init_db
from lrcs.warehouse.load import load_from_pipeline_outputs, make_run_id

__all__ = [
    "DEFAULT_DB_PATH",
    "SCHEMA_SQL",
    "connect",
    "init_db",
    "load_from_pipeline_outputs",
    "make_run_id",
]

"""Load the system exports under data/raw into DuckDB (schema raw), one table per export file.

The per-stroke and per-minute press monitor exports are Parquet and are read in place by the staging models.

Usage: python -m pipeline.load.load_exports
"""
from pathlib import Path

import dlt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "spc.duckdb"
SYSTEMS = ["erp", "spc", "press_monitor", "qms", "die_room", "calibration"]


def rows(path, chunk=50000):
    for df in pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], chunksize=chunk):
        yield df.astype(object).where(df.notna(), None).to_dict("records")


def export_tables():
    """One resource per export file, named <system>__<table>. Columns load as text; staging casts them."""
    for system in SYSTEMS:
        for path in sorted(list((RAW / system).glob("*.csv")) + list((RAW / system).glob("*.csv.gz"))):
            name = f"{system}__{path.name.split('.')[0]}"
            header = pd.read_csv(path, dtype=str, nrows=0).columns
            columns = {c: {"data_type": "text", "nullable": True} for c in header}
            yield dlt.resource(rows(path), name=name, write_disposition="replace", columns=columns)


def main():
    pipeline = dlt.pipeline(pipeline_name="spc_exports", destination=dlt.destinations.duckdb(str(DB)), dataset_name="raw")
    info = pipeline.run(list(export_tables()))
    print(info)


if __name__ == "__main__":
    main()

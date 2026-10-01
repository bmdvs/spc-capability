"""Read access to the marts."""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "spc.duckdb"


def query(sql, params=None):
    """Run a query against the marts and return a DataFrame. Queries state their own ordering."""
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()

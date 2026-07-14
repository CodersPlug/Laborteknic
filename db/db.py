"""Shared DuckDB connection helpers for Laborteknic agent DB."""

from pathlib import Path
import duckdb

DB = Path(__file__).resolve().parent / "laborteknic.duckdb"
DIM = 384
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def configure_hnsw(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("LOAD hnsw_acorn")
    con.execute("SET hnsw_enable_experimental_persistence = true")
    con.execute("SET hnsw_acorn_threshold      = 0.6")
    con.execute("SET hnsw_bruteforce_threshold = 0.01")


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB), read_only=read_only)
    try:
        configure_hnsw(con)
    except Exception:
        pass
    return con

import sqlite3
from pathlib import Path
from typing import Generator

from app.core.config import DATABASE_PATH

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        schema_sql = _SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()
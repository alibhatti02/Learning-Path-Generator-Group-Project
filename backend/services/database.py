import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

# Store the SQLite file next to main.py; override with DATABASE_PATH for deployments (e.g. Azure mounted volume)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DATABASE_PATH", os.path.join(_BACKEND_DIR, "courseforge.db"))


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Yields a connection that commits on success and always closes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Creates the users table on first boot. Passwords are only ever stored as bcrypt hashes."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

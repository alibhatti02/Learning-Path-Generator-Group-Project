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
    # SQLite has FK enforcement OFF by default per-connection — without this, every
    # "ON DELETE CASCADE" in the schema below is silently a no-op and deletes leave orphans.
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Creates all tables on first boot. Passwords are only ever stored as bcrypt hashes."""
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
        # Saved roadmap sessions — one row per generated path, newest first in the UI
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                topic TEXT NOT NULL,
                experience_level TEXT NOT NULL,
                hours_per_day INTEGER NOT NULL,
                roadmap_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # YouTube search cache — repeated queries cost 0 quota units instead of 100
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_cache (
                query TEXT PRIMARY KEY,
                results_json TEXT NOT NULL,
                cached_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # ===================== Group Skills feature =====================

        # A group is a shared topic up to 6 people compete on. invite_code is how others join.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                skill_topic TEXT NOT NULL,
                experience_level TEXT NOT NULL DEFAULT 'beginner',
                invite_code TEXT NOT NULL UNIQUE,
                created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                max_members INTEGER NOT NULL DEFAULT 6,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )

        # One row per (group, user). hourly_commitment / calculated_weeks / roadmap_json are
        # PRIVATE fields — group_service.py must never let these leave the owning user's own request.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                hourly_commitment REAL,
                calculated_weeks INTEGER,
                roadmap_json TEXT,
                current_week INTEGER NOT NULL DEFAULT 0,
                total_points INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending_hours',
                completed_at TEXT,
                joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (group_id, user_id)
            )
            """
        )

        # One row per member per week — backs both the leaderboard and each member's own pace view.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                week_number INTEGER NOT NULL,
                quiz_score INTEGER,
                quiz_total INTEGER,
                points_earned INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (group_id, user_id, week_number)
            )
            """
        )

        # One row per quiz the user generates. questions_json holds the full questions
        # WITH their correct answers and is NEVER sent to the client — grading loads it
        # here server-side. group_id is set for group quizzes, null for standalone ones.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
                milestone TEXT NOT NULL,
                week_number INTEGER NOT NULL,
                questions_json TEXT NOT NULL,
                score INTEGER,
                total INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )




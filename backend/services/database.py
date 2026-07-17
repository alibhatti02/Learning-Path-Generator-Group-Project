import os
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.dialects import mssql
from sqlalchemy.engine import Connection

# Unbounded unicode text. Plain UnicodeText renders as the DEPRECATED NTEXT on
# SQL Server, so map it to NVARCHAR(MAX) there; stays TEXT on SQLite.
BIG_TEXT = UnicodeText().with_variant(mssql.NVARCHAR(None), "mssql")

# ---------------------------------------------------------------------------
# Engine — driven entirely by DATABASE_URL so the same code runs on SQLite
# locally and Azure SQL in production.
#
#   Local (default):  sqlite:///<backend>/courseforge.db
#   Azure SQL:        mssql+pyodbc://<user>:<pass>@<server>.database.windows.net:1433/
#                       <db>?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no
#
# pool_pre_ping recovers connections Azure silently drops after idle periods.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_SQLITE = f"sqlite:///{os.path.join(_BACKEND_DIR, 'courseforge.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", _DEFAULT_SQLITE)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)


# SQLite disables foreign-key enforcement per-connection, so ON DELETE CASCADE
# would silently do nothing without this. Azure SQL enforces FKs natively, so
# this hook is scoped to the SQLite dialect only.
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fks(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


metadata = MetaData()

# Column type choices:
#   Unicode / UnicodeText  -> NVARCHAR on SQL Server: any column holding raw user
#     or AI text (names, topics, milestones, search queries, JSON payloads) so
#     emoji and non-Latin characters survive. VARCHAR would corrupt them.
#   String                 -> VARCHAR: machine/ASCII-only values (bcrypt hash,
#     hex invite code, enum-ish status/level). Cheaper, and never non-ASCII.
# Index/PK/UNIQUE string columns must be length-bounded (SQL Server caps key size;
# NVARCHAR keys cap at 450 chars).

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("email", Unicode(254), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

# Saved roadmap sessions — one row per generated path, newest first in the UI
learning_paths = Table(
    "learning_paths", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("title", Unicode(300), nullable=False),
    Column("topic", Unicode(300), nullable=False),
    Column("experience_level", String(50), nullable=False),
    Column("hours_per_day", Integer, nullable=False),
    Column("roadmap_json", BIG_TEXT, nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

# YouTube search cache — repeated queries cost 0 quota units instead of 100
youtube_cache = Table(
    "youtube_cache", metadata,
    Column("query", Unicode(450), primary_key=True),
    Column("results_json", BIG_TEXT, nullable=False),
    Column("cached_at", DateTime, default=datetime.utcnow, nullable=False),
)

# A group is a shared topic up to 6 people compete on. invite_code is how others join.
groups = Table(
    "groups", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Unicode(100), nullable=False),
    Column("skill_topic", Unicode(200), nullable=False),
    Column("experience_level", String(50), nullable=False, default="beginner"),
    Column("invite_code", String(32), nullable=False, unique=True),
    Column("created_by", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("max_members", Integer, nullable=False, default=6),
    Column("status", String(20), nullable=False, default="active"),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

# One row per (group, user). hourly_commitment / calculated_weeks / roadmap_json are
# PRIVATE fields — group_service.py must never let these leave the owning user's own request.
group_members = Table(
    "group_members", metadata,
    Column("id", Integer, primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("hourly_commitment", Float),
    Column("calculated_weeks", Integer),
    Column("roadmap_json", BIG_TEXT),
    Column("current_week", Integer, nullable=False, default=0),
    Column("total_points", Integer, nullable=False, default=0),
    Column("status", String(20), nullable=False, default="pending_hours"),
    Column("completed_at", DateTime),
    Column("joined_at", DateTime, default=datetime.utcnow, nullable=False),
    UniqueConstraint("group_id", "user_id", name="uq_group_member"),
)

# One row per member per week — backs both the leaderboard and each member's own pace view.
group_progress = Table(
    "group_progress", metadata,
    Column("id", Integer, primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("week_number", Integer, nullable=False),
    Column("quiz_score", Integer),
    Column("quiz_total", Integer),
    Column("points_earned", Integer, nullable=False, default=0),
    Column("completed_at", DateTime, default=datetime.utcnow, nullable=False),
    UniqueConstraint("group_id", "user_id", "week_number", name="uq_group_week"),
)

# One row per quiz the user generates. questions_json holds the full questions WITH
# their correct answers and is NEVER sent to the client — grading loads it here
# server-side. group_id is set for group quizzes, null for standalone ones.
quiz_attempts = Table(
    "quiz_attempts", metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE")),
    Column("milestone", Unicode(300), nullable=False),
    Column("week_number", Integer, nullable=False),
    Column("questions_json", BIG_TEXT, nullable=False),
    Column("score", Integer),
    Column("total", Integer),
    Column("status", String(20), nullable=False, default="pending"),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)


@contextmanager
def get_db() -> Iterator[Connection]:
    """Yields a connection inside a transaction that commits on success,
    rolls back on error, and always closes — same contract as before."""
    with engine.begin() as conn:
        yield conn


def init_db() -> None:
    """Creates any missing tables. Portable across SQLite and Azure SQL —
    SQLAlchemy emits the right DDL (AUTOINCREMENT vs IDENTITY, etc.) per dialect."""
    metadata.create_all(engine)

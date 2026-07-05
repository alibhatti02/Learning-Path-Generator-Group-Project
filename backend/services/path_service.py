import json

from services.database import get_db


def save_path(user_id: int, topic: str, experience_level: str, hours_per_day: int, roadmap: dict) -> int:
    """Persists a generated roadmap as a session row and returns its id."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO learning_paths (user_id, title, topic, experience_level, hours_per_day, roadmap_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                roadmap.get("title") or topic,
                topic,
                experience_level,
                hours_per_day,
                json.dumps(roadmap),
            ),
        )
        return cursor.lastrowid


def list_paths(user_id: int) -> list[dict]:
    """Lightweight session list for the sidebar — no roadmap payloads, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, title, topic, experience_level, hours_per_day, created_at
            FROM learning_paths WHERE user_id = ? ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_path(user_id: int, path_id: int) -> dict | None:
    """Full saved session including the roadmap payload; None if not this user's."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM learning_paths WHERE id = ? AND user_id = ?",
            (path_id, user_id),
        ).fetchone()
    if row is None:
        return None
    record = dict(row)
    record["roadmap"] = json.loads(record.pop("roadmap_json"))
    return record


def delete_path(user_id: int, path_id: int) -> bool:
    """Deletes a session; returns False if it didn't exist or belongs to someone else."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM learning_paths WHERE id = ? AND user_id = ?",
            (path_id, user_id),
        )
        return cursor.rowcount > 0

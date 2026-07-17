import json

from sqlalchemy import text

from services.database import get_db, learning_paths


def save_path(user_id: int, topic: str, experience_level: str, hours_per_day: int, roadmap: dict) -> int:
    """Persists a generated roadmap as a session row and returns its id."""
    with get_db() as conn:
        result = conn.execute(
            learning_paths.insert().values(
                user_id=user_id,
                title=roadmap.get("title") or topic,
                topic=topic,
                experience_level=experience_level,
                hours_per_day=hours_per_day,
                roadmap_json=json.dumps(roadmap),
            )
        )
        return result.inserted_primary_key[0]


def list_paths(user_id: int) -> list[dict]:
    """Lightweight session list for the sidebar — no roadmap payloads, newest first."""
    with get_db() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, title, topic, experience_level, hours_per_day, created_at
                FROM learning_paths WHERE user_id = :user_id ORDER BY id DESC
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def get_path(user_id: int, path_id: int) -> dict | None:
    """Full saved session including the roadmap payload; None if not this user's."""
    with get_db() as conn:
        row = conn.execute(
            text("SELECT * FROM learning_paths WHERE id = :id AND user_id = :user_id"),
            {"id": path_id, "user_id": user_id},
        ).mappings().first()
    if row is None:
        return None
    record = dict(row)
    record["roadmap"] = json.loads(record.pop("roadmap_json"))
    return record


def delete_path(user_id: int, path_id: int) -> bool:
    """Deletes a session; returns False if it didn't exist or belongs to someone else."""
    with get_db() as conn:
        result = conn.execute(
            text("DELETE FROM learning_paths WHERE id = :id AND user_id = :user_id"),
            {"id": path_id, "user_id": user_id},
        )
        return result.rowcount > 0

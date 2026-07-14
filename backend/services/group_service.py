import json
import secrets
import sqlite3

from services.ai_service import generate_learning_roadmap
from services.database import get_db
from services.quiz_service import get_attempt

# Points awarded for finishing the whole course, by placement (1st through 6th).
# Placement is determined by whoever's total_points/status flips to "completed" first.
COMPLETION_POINTS = [100, 80, 65, 50, 35, 20]

# Weekly quiz points are scaled from the raw score, capped so quiz performance
# can't outweigh actually finishing the course.
MAX_QUIZ_POINTS_PER_WEEK = 10
STREAK_BONUS = 5  # awarded when a member completes a week without gaps in numbering


def _generate_invite_code() -> str:
    return secrets.token_hex(4)  # 8 hex chars, short enough to type/share


def create_group(user_id: int, name: str, skill_topic: str, experience_level: str) -> dict:
    """Creates a group and auto-enrolls the creator as its first member (hours still unset)."""
    with get_db() as conn:
        invite_code = _generate_invite_code()
        cursor = conn.execute(
            """
            INSERT INTO groups (name, skill_topic, experience_level, invite_code, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), skill_topic.strip(), experience_level, invite_code, user_id),
        )
        group_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
            (group_id, user_id),
        )
    return get_group_summary(group_id)


def join_group(user_id: int, invite_code: str) -> dict:
    """Adds the user to a group by invite code. Raises ValueError on any failure condition."""
    with get_db() as conn:
        group = conn.execute(
            "SELECT * FROM groups WHERE invite_code = ?", (invite_code.strip(),)
        ).fetchone()
        if group is None:
            raise ValueError("Invalid invite code.")
        if group["status"] != "active":
            raise ValueError("This group is no longer active.")

        member_count = conn.execute(
            "SELECT COUNT(*) AS c FROM group_members WHERE group_id = ?", (group["id"],)
        ).fetchone()["c"]
        if member_count >= group["max_members"]:
            raise ValueError("This group is already full.")

        try:
            conn.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
                (group["id"], user_id),
            )
        except sqlite3.IntegrityError:
            raise ValueError("You're already a member of this group.")

        return dict(group)


def leave_group(user_id: int, group_id: int) -> None:
    """
    Removes a non-creator member from a group. The creator can't leave — they must
    delete_group() instead, since there's no ownership-transfer flow yet.
    """
    with get_db() as conn:
        member = _member_row(conn, group_id, user_id)
        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group is None:
            raise ValueError("Group not found.")
        if group["created_by"] == user_id:
            raise ValueError("As the creator, you can't leave — delete the group instead.")

        conn.execute("DELETE FROM group_members WHERE id = ?", (member["id"],))
        # group_progress has no FK back to group_members, so it isn't covered by the
        # groups-table cascade — clear this member's history in the group explicitly.
        conn.execute(
            "DELETE FROM group_progress WHERE group_id = ? AND user_id = ?", (group_id, user_id)
        )


def delete_group(user_id: int, group_id: int) -> None:
    """
    Deletes a group entirely. Only the creator can do this. Requires PRAGMA foreign_keys
    to be ON (set in database.get_db) for group_members/group_progress rows to cascade —
    without it this would leave orphaned rows behind.
    """
    with get_db() as conn:
        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group is None:
            raise ValueError("Group not found.")
        if group["created_by"] != user_id:
            raise ValueError("Only the group's creator can delete it.")

        conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))


def _member_row(conn, group_id: int, user_id: int):
    row = conn.execute(
        "SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, user_id),
    ).fetchone()
    if row is None:
        raise ValueError("You are not a member of this group.")
    return row


def set_hours(user_id: int, group_id: int, hourly_commitment: float) -> dict:
    """
    Sets a member's private daily-hours commitment and generates their individual
    roadmap sized to it. This value, and the roadmap it produces, must never be
    exposed to any other member of the group — see get_leaderboard() for the enforced boundary.
    """
    with get_db() as conn:
        member = _member_row(conn, group_id, user_id)
        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()

        roadmap = generate_learning_roadmap(
            topic=group["skill_topic"],
            hours_per_day=int(round(hourly_commitment)) or 1,
            level=group["experience_level"],
        )
        if "error" in roadmap:
            raise ValueError(roadmap["error"])

        conn.execute(
            """
            UPDATE group_members
            SET hourly_commitment = ?, calculated_weeks = ?, roadmap_json = ?, status = 'active'
            WHERE id = ?
            """,
            (hourly_commitment, roadmap.get("calculated_total_weeks", 1), json.dumps(roadmap), member["id"]),
        )

    return get_my_membership(user_id, group_id)


def get_my_membership(user_id: int, group_id: int) -> dict:
    """Private view of a single member's own progress — safe to return only to that user."""
    with get_db() as conn:
        member = _member_row(conn, group_id, user_id)
        group = conn.execute("SELECT created_by FROM groups WHERE id = ?", (group_id,)).fetchone()

    return {
        "group_id": group_id,
        "hourly_commitment": member["hourly_commitment"],
        "calculated_weeks": member["calculated_weeks"],
        "current_week": member["current_week"],
        "total_points": member["total_points"],
        "status": member["status"],
        "roadmap": json.loads(member["roadmap_json"]) if member["roadmap_json"] else None,
        "is_creator": group is not None and group["created_by"] == user_id,
    }


def complete_week(user_id: int, group_id: int, quiz_id: int) -> dict:
    """
    Logs a week's progress from a SERVER-GRADED quiz attempt. The score is read
    from the stored attempt — never from the client — and the attempt must belong
    to this user and this group, which is what keeps the leaderboard honest.
    """
    with get_db() as conn:
        member = _member_row(conn, group_id, user_id)
        if member["calculated_weeks"] is None:
            raise ValueError("Set your hourly commitment before logging progress.")

        attempt = get_attempt(user_id, quiz_id)
        if attempt is None or attempt["status"] != "graded":
            raise ValueError("Submit the quiz before logging this week.")
        if attempt["group_id"] != group_id:
            raise ValueError("This quiz doesn't belong to this group.")

        # Trust only the server's stored grade and the attempt's own week number
        week_number = attempt["week_number"]
        quiz_score = attempt["score"]
        quiz_total = attempt["total"]
        if week_number != member["current_week"] + 1:
            raise ValueError(f"Expected week {member['current_week'] + 1} next, got week {week_number}.")

        quiz_points = round((quiz_score / quiz_total) * MAX_QUIZ_POINTS_PER_WEEK) if quiz_total else 0
        points = quiz_points + STREAK_BONUS

        try:
            conn.execute(
                """
                INSERT INTO group_progress (group_id, user_id, week_number, quiz_score, quiz_total, points_earned)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, user_id, week_number, quiz_score, quiz_total, points),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Week {week_number} was already logged.")

        new_week = member["current_week"] + 1
        new_status = member["status"]
        completed_at = None

        if new_week >= member["calculated_weeks"]:
            # Course finished — award placement points based on how many members
            # already finished this group's course before this one.
            already_finished = conn.execute(
                "SELECT COUNT(*) AS c FROM group_members WHERE group_id = ? AND status = 'completed'",
                (group_id,),
            ).fetchone()["c"]
            placement_points = COMPLETION_POINTS[min(already_finished, len(COMPLETION_POINTS) - 1)]
            points += placement_points
            new_status = "completed"
            completed_at = "datetime('now')"

        if completed_at:
            conn.execute(
                """
                UPDATE group_members
                SET current_week = ?, total_points = total_points + ?, status = ?, completed_at = datetime('now')
                WHERE id = ?
                """,
                (new_week, points, new_status, member["id"]),
            )
        else:
            conn.execute(
                """
                UPDATE group_members
                SET current_week = ?, total_points = total_points + ?, status = ?
                WHERE id = ?
                """,
                (new_week, points, new_status, member["id"]),
            )

    return get_my_membership(user_id, group_id)


def get_group_summary(group_id: int) -> dict:
    with get_db() as conn:
        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
        if group is None:
            raise ValueError("Group not found.")
        member_count = conn.execute(
            "SELECT COUNT(*) AS c FROM group_members WHERE group_id = ?", (group_id,)
        ).fetchone()["c"]

    result = dict(group)
    result["member_count"] = member_count
    return result


def get_leaderboard(requesting_user_id: int, group_id: int) -> dict:
    """
    Returns the public leaderboard: rank, points, current_week, status per member.

    PRIVACY BOUNDARY: this function is the single source of truth for what other
    members can see about each other. hourly_commitment, calculated_weeks, and
    roadmap_json are intentionally never selected into the row dict below — not
    just omitted from the response model. Do not add them here; fetch them only
    through get_my_membership(), which is scoped to the caller's own user_id.
    """
    with get_db() as conn:
        _member_row(conn, group_id, requesting_user_id)  # 403-style guard: must be a member to view
        group = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()

        rows = conn.execute(
            """
            SELECT gm.user_id, u.email, gm.current_week, gm.total_points, gm.status
            FROM group_members gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = ?
            ORDER BY gm.total_points DESC, gm.current_week DESC, gm.joined_at ASC
            """,
            (group_id,),
        ).fetchall()

    entries = []
    weeks = []
    for i, row in enumerate(rows, start=1):
        weeks.append(row["current_week"])
        entries.append({
            "user_id": row["user_id"],
            # Email prefix as a display name placeholder — swap for a real display_name
            # column once your teammate's user-profile work lands.
            "display_name": row["email"].split("@")[0],
            "rank": i,
            "total_points": row["total_points"],
            "current_week": row["current_week"],
            "status": row["status"],
            "is_me": row["user_id"] == requesting_user_id,
        })

    avg_week = round(sum(weeks) / len(weeks), 1) if weeks else 0.0

    summary = dict(group)
    summary["member_count"] = len(rows)

    return {
        "group": summary,
        "leaderboard": entries,
        "average_current_week": avg_week,
    }


def list_my_groups(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT g.* FROM groups g
            JOIN group_members gm ON gm.group_id = g.id
            WHERE gm.user_id = ?
            ORDER BY g.created_at DESC
            """,
            (user_id,),
        ).fetchall()
        result = []
        for row in rows:
            member_count = conn.execute(
                "SELECT COUNT(*) AS c FROM group_members WHERE group_id = ?", (row["id"],)
            ).fetchone()["c"]
            entry = dict(row)
            entry["member_count"] = member_count
            result.append(entry)
    return result
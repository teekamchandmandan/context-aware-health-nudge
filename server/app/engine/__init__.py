"""Decision engine: deterministic nudge selection with evaluators, fatigue, and escalation."""

import sqlite3

from .common import NudgeCandidate, _id, _now, _ts
from .evaluators import (
    check_meal_goal_mismatch,
    check_missing_weight_log,
    check_repeated_low_mood,
    check_support_risk,
)
from .persistence import create_nudge_from_candidate
from .policy import get_active_nudge, get_escalated_nudge, has_newer_signal, select_nudge, supersede_active_nudge


def evaluate_member(conn: sqlite3.Connection, member_id: str) -> dict:
    existing = get_active_nudge(conn, member_id)
    if existing:
        if not has_newer_signal(conn, member_id, existing["created_at"]):
            return {"state": "active", "nudge": dict(existing)}

        supersede_active_nudge(conn, existing["id"])

    escalated = get_escalated_nudge(conn, member_id)
    if escalated:
        if not has_newer_signal(conn, member_id, escalated["created_at"]):
            esc_row = conn.execute(
                "SELECT id FROM escalations WHERE nudge_id = ? AND status = 'open' LIMIT 1",
                (escalated["id"],),
            ).fetchone()
            if esc_row:
                return {
                    "state": "escalated",
                    "nudge_id": escalated["id"],
                    "escalation_id": esc_row["id"],
                }

            supersede_active_nudge(conn, escalated["id"])

        else:
            supersede_active_nudge(conn, escalated["id"])

    candidate = select_nudge(conn, member_id)
    if not candidate:
        conn.commit()
        return {"state": "no_nudge"}

    try:
        result = create_nudge_from_candidate(conn, member_id, candidate)
        conn.commit()
        return result
    except sqlite3.IntegrityError as exc:
        # A concurrent request may already have created an active nudge for
        # this member (unique partial index on status='active' fired). Roll
        # back and only recover if an active nudge now exists; otherwise the
        # integrity error was unrelated and should not be hidden.
        conn.rollback()
        surviving = get_active_nudge(conn, member_id)
        conn.commit()
        if surviving:
            return {"state": "active", "nudge": dict(surviving)}
        raise


__all__ = [
    "NudgeCandidate",
    "evaluate_member",
    "select_nudge",
    "check_meal_goal_mismatch",
    "check_missing_weight_log",
    "check_repeated_low_mood",
    "check_support_risk",
    "_ts",
    "_now",
    "_id",
]
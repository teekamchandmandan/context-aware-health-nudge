"""Decision engine: deterministic nudge selection with evaluators, fatigue, and escalation."""

import sqlite3

from .common import NudgeCandidate, _id, _now, _ts
from .evaluators import (
    check_meal_goal_mismatch,
    check_missing_weight_log,
    check_support_risk,
)
from .persistence import create_nudge_from_candidate
from .policy import get_active_nudge, has_newer_signal, select_nudge, supersede_active_nudge


def evaluate_member(conn: sqlite3.Connection, member_id: str) -> dict:
    existing = get_active_nudge(conn, member_id)
    if existing:
        if not has_newer_signal(conn, member_id, existing["created_at"]):
            return {"state": "active", "nudge": dict(existing)}

        supersede_active_nudge(conn, existing["id"])

    candidate = select_nudge(conn, member_id)
    if not candidate:
        conn.commit()
        return {"state": "no_nudge"}

    result = create_nudge_from_candidate(conn, member_id, candidate)
    conn.commit()
    return result


__all__ = [
    "NudgeCandidate",
    "evaluate_member",
    "select_nudge",
    "check_meal_goal_mismatch",
    "check_missing_weight_log",
    "check_support_risk",
    "_ts",
    "_now",
    "_id",
]
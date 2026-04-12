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


def _get_open_escalation_id(conn: sqlite3.Connection, nudge_id: str) -> str | None:
    row = conn.execute(
        "SELECT id FROM escalations WHERE nudge_id = ? AND status = 'open' LIMIT 1",
        (nudge_id,),
    ).fetchone()
    return row["id"] if row else None


def evaluate_member(conn: sqlite3.Connection, member_id: str) -> dict:
    existing = get_active_nudge(conn, member_id)
    if existing:
        if not has_newer_signal(conn, member_id, existing["created_at"]):
            return {"state": "active", "nudge": dict(existing)}

        supersede_active_nudge(conn, existing["id"])

    escalated = get_escalated_nudge(conn, member_id)
    if escalated:
        if not has_newer_signal(conn, member_id, escalated["created_at"]):
            escalation_id = _get_open_escalation_id(conn, escalated["id"])
            if escalation_id:
                return {
                    "state": "escalated",
                    "nudge_id": escalated["id"],
                    "escalation_id": escalation_id,
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
    except sqlite3.IntegrityError:
        # A concurrent request may already have created the active or escalated
        # result for this member. Roll back and reuse the surviving state if it
        # now exists; otherwise the integrity error was unrelated and should
        # not be hidden.
        conn.rollback()
        surviving_active = get_active_nudge(conn, member_id)
        if surviving_active:
            conn.commit()
            return {"state": "active", "nudge": dict(surviving_active)}

        surviving_escalated = get_escalated_nudge(conn, member_id)
        if surviving_escalated:
            escalation_id = _get_open_escalation_id(conn, surviving_escalated["id"])
            conn.commit()
            if escalation_id:
                return {
                    "state": "escalated",
                    "nudge_id": surviving_escalated["id"],
                    "escalation_id": escalation_id,
                }

        conn.commit()
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
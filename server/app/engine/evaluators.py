import json
import sqlite3
from datetime import datetime, timezone

from .common import (
    DISMISS_LOOKBACK_DAYS,
    MEAL_LOOKBACK_HOURS,
    MISSING_WEIGHT_DAYS,
    MOOD_LOOKBACK_DAYS,
    NudgeCandidate,
    PRIORITY,
    _now,
    _ts,
    timedelta,
)


def _parse_ts(ts: str) -> datetime:
    """Parse a UTC ISO timestamp string produced by _ts() into an aware datetime."""
    return datetime.fromisoformat(ts.rstrip("Z")).replace(tzinfo=timezone.utc)


def check_meal_goal_mismatch(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    row = conn.execute(
        "SELECT goal_type FROM members WHERE id = ?", (member_id,)
    ).fetchone()
    if not row or row["goal_type"] != "low_carb":
        return None

    cutoff = _ts(_now() - timedelta(hours=MEAL_LOOKBACK_HOURS))
    signal = conn.execute(
        """SELECT id, payload_json, created_at FROM signals
           WHERE member_id = ? AND signal_type = 'meal_logged' AND created_at >= ?
           ORDER BY created_at DESC LIMIT 1""",
        (member_id, cutoff),
    ).fetchone()
    if not signal:
        return None

    payload = json.loads(signal["payload_json"])
    if not meal_fields_confirmed(payload):
        return None

    if payload.get("meal_profile") != "higher_carb":
        return None

    hours_since = (_now() - _parse_ts(signal["created_at"])).total_seconds() / 3600
    freshness = max(0.0, 1.0 - hours_since / MEAL_LOOKBACK_HOURS)
    confidence = round(0.65 + 0.28 * freshness, 2)

    return NudgeCandidate(
        nudge_type="meal_guidance",
        matched_reason="meal_goal_mismatch",
        explanation_basis="Recent meal looked higher carb for a low-carb goal",
        confidence=confidence,
        escalation_recommended=False,
        source_signal_ids=[signal["id"]],
        priority=PRIORITY["meal_guidance"],
        latest_signal_ts=signal["created_at"],
    )


def meal_fields_confirmed(payload: dict) -> bool:
    meal_profile = payload.get("meal_profile")
    return isinstance(meal_profile, str) and bool(meal_profile.strip())


def check_missing_weight_log(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    now = _now()
    cutoff_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=MISSING_WEIGHT_DAYS)
    cutoff = _ts(cutoff_dt)

    signal = conn.execute(
        """SELECT id FROM signals
           WHERE member_id = ? AND signal_type = 'weight_logged' AND created_at >= ?
           LIMIT 1""",
        (member_id, cutoff),
    ).fetchone()
    if signal:
        return None

    last_weight = conn.execute(
        """SELECT created_at FROM signals
           WHERE member_id = ? AND signal_type = 'weight_logged'
           ORDER BY created_at DESC LIMIT 1""",
        (member_id,),
    ).fetchone()

    if last_weight:
        days_since = (now - _parse_ts(last_weight["created_at"])).total_seconds() / 86400
    else:
        # Never logged: treat as twice the threshold to saturate overdue_factor at 1.0.
        days_since = float(MISSING_WEIGHT_DAYS * 2)

    overdue_factor = min(1.0, max(0.0, (days_since - MISSING_WEIGHT_DAYS) / MISSING_WEIGHT_DAYS))
    confidence = round(0.56 + 0.16 * overdue_factor, 2)

    return NudgeCandidate(
        nudge_type="weight_check_in",
        matched_reason="missing_weight_log",
        explanation_basis=f"No weight logged in the last {MISSING_WEIGHT_DAYS} days",
        confidence=confidence,
        escalation_recommended=False,
        source_signal_ids=[],
        priority=PRIORITY["weight_check_in"],
    )


def check_support_risk(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    now = _now()
    mood_cutoff = _ts(now - timedelta(days=MOOD_LOOKBACK_DAYS))
    dismiss_cutoff = _ts(now - timedelta(days=DISMISS_LOOKBACK_DAYS))

    mood_signal = conn.execute(
        """SELECT id, payload_json, created_at FROM signals
           WHERE member_id = ? AND signal_type = 'mood_logged' AND created_at >= ?
           ORDER BY created_at DESC LIMIT 1""",
        (member_id, mood_cutoff),
    ).fetchone()
    if not mood_signal:
        return None

    payload = json.loads(mood_signal["payload_json"])
    if payload.get("mood") != "low":
        return None

    dismiss_count = conn.execute(
        """SELECT COUNT(*) as cnt FROM nudge_actions na
           JOIN nudges n ON na.nudge_id = n.id
           WHERE n.member_id = ? AND na.action_type = 'dismiss' AND na.created_at >= ?""",
        (member_id, dismiss_cutoff),
    ).fetchone()["cnt"]
    if dismiss_count < 2:
        return None

    confidence = round(0.42 + (dismiss_count - 2) * 0.06, 2)

    return NudgeCandidate(
        nudge_type="support_risk",
        matched_reason="support_risk",
        explanation_basis=f"Low mood reported; {dismiss_count} nudges dismissed in last {DISMISS_LOOKBACK_DAYS} days",
        confidence=confidence,
        escalation_recommended=True,
        source_signal_ids=[mood_signal["id"]],
        priority=PRIORITY["support_risk"],
        latest_signal_ts=mood_signal["created_at"],
    )


ALL_EVALUATORS = [
    check_meal_goal_mismatch,
    check_missing_weight_log,
    check_support_risk,
]
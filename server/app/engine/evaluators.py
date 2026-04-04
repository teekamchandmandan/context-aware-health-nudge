import json
import sqlite3

from .common import (
    DISMISS_LOOKBACK_DAYS,
    MEAL_CARB_THRESHOLD,
    MEAL_LOOKBACK_HOURS,
    MISSING_WEIGHT_DAYS,
    MOOD_LOOKBACK_DAYS,
    NudgeCandidate,
    PRIORITY,
    _now,
    _ts,
    timedelta,
)


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

    carbs = payload.get("carbs_g")
    if carbs is None or carbs < MEAL_CARB_THRESHOLD:
        return None

    meal_name = payload.get("meal_name") or payload.get("meal") or "Recent meal"
    return NudgeCandidate(
        nudge_type="meal_guidance",
        matched_reason="meal_goal_mismatch",
        explanation_basis=f"{meal_name} logged {carbs}g carbs; goal is low_carb (<{MEAL_CARB_THRESHOLD}g)",
        confidence=0.86,
        escalation_recommended=False,
        source_signal_ids=[signal["id"]],
        priority=PRIORITY["meal_guidance"],
        latest_signal_ts=signal["created_at"],
    )


def meal_fields_confirmed(payload: dict) -> bool:
    if payload.get("analysis_confirmed") is True:
        return True

    meal_input_method = payload.get("meal_input_method")
    if meal_input_method in {"manual", "structured"}:
        return True

    if isinstance(meal_input_method, str) and meal_input_method.startswith("one_step"):
        return True

    if "analysis_confirmed" not in payload and "analysis_source" not in payload:
        return True

    return False


def check_missing_weight_log(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    cutoff_dt = _now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=MISSING_WEIGHT_DAYS)
    cutoff = _ts(cutoff_dt)

    signal = conn.execute(
        """SELECT id FROM signals
           WHERE member_id = ? AND signal_type = 'weight_logged' AND created_at >= ?
           LIMIT 1""",
        (member_id, cutoff),
    ).fetchone()
    if signal:
        return None

    return NudgeCandidate(
        nudge_type="weight_check_in",
        matched_reason="missing_weight_log",
        explanation_basis=f"No weight logged in the last {MISSING_WEIGHT_DAYS} days",
        confidence=0.68,
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

    return NudgeCandidate(
        nudge_type="support_risk",
        matched_reason="support_risk",
        explanation_basis=f"Low mood reported; {dismiss_count} nudges dismissed in last {DISMISS_LOOKBACK_DAYS} days",
        confidence=0.42,
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
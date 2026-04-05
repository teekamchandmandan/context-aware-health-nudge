import json
import sqlite3
from datetime import datetime

from .common import (
    DISMISS_LOOKBACK_DAYS,
    MEAL_LOOKBACK_HOURS,
    MISSING_WEIGHT_DAYS,
    MOOD_LOOKBACK_DAYS,
    NudgeCandidate,
    PRIORITY,
    REPEATED_LOW_MOOD_COUNT,
    _now,
    _ts,
    timedelta,
)
from .confidence import score_meal_guidance, score_repeated_low_mood, score_support_risk, score_weight_check_in


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

    confidence, factors = score_meal_guidance(
        signal_ts=signal["created_at"],
        meal_profile=payload.get("meal_profile", "unclear"),
        lookback_hours=MEAL_LOOKBACK_HOURS,
    )

    return NudgeCandidate(
        nudge_type="meal_guidance",
        matched_reason="meal_goal_mismatch",
        explanation_basis="Recent meal looked higher carb for a low-carb goal",
        confidence=confidence,
        confidence_factors=factors,
        escalation_recommended=False,
        source_signal_ids=[signal["id"]],
        priority=PRIORITY["meal_guidance"],
        latest_signal_ts=signal["created_at"],
    )


def meal_fields_confirmed(payload: dict) -> bool:
    meal_profile = payload.get("meal_profile")
    return isinstance(meal_profile, str) and bool(meal_profile.strip())


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

    last_weight = conn.execute(
        "SELECT created_at FROM signals WHERE member_id = ? AND signal_type = 'weight_logged' ORDER BY created_at DESC LIMIT 1",
        (member_id,),
    ).fetchone()
    if last_weight:
        last_dt = datetime.fromisoformat(last_weight["created_at"].replace("Z", "+00:00"))
        days_since = (_now() - last_dt).total_seconds() / 86400
    else:
        days_since = float(MISSING_WEIGHT_DAYS * 2)

    activity_cutoff = _ts(_now() - timedelta(days=7))
    has_recent_activity = conn.execute(
        "SELECT 1 FROM signals WHERE member_id = ? AND signal_type != 'weight_logged' AND created_at >= ? LIMIT 1",
        (member_id, activity_cutoff),
    ).fetchone() is not None

    confidence, factors = score_weight_check_in(
        days_since_last_weight=days_since,
        threshold_days=MISSING_WEIGHT_DAYS,
        has_recent_activity=has_recent_activity,
    )

    return NudgeCandidate(
        nudge_type="weight_check_in",
        matched_reason="missing_weight_log",
        explanation_basis=f"No weight logged in the last {MISSING_WEIGHT_DAYS} days",
        confidence=confidence,
        confidence_factors=factors,
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

    confidence, factors = score_support_risk(
        mood_signal_ts=mood_signal["created_at"],
        dismiss_count=dismiss_count,
        mood_lookback_days=MOOD_LOOKBACK_DAYS,
        dismiss_lookback_days=DISMISS_LOOKBACK_DAYS,
    )

    return NudgeCandidate(
        nudge_type="support_risk",
        matched_reason="support_risk",
        explanation_basis=f"Low mood reported; {dismiss_count} nudges dismissed in last {DISMISS_LOOKBACK_DAYS} days",
        confidence=confidence,
        confidence_factors=factors,
        escalation_recommended=True,
        source_signal_ids=[mood_signal["id"]],
        priority=PRIORITY["support_risk"],
        latest_signal_ts=mood_signal["created_at"],
    )


def check_repeated_low_mood(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    now = _now()
    mood_cutoff = _ts(now - timedelta(days=MOOD_LOOKBACK_DAYS))

    row = conn.execute(
        """SELECT COUNT(*) AS cnt, MAX(created_at) AS latest_ts
           FROM signals
           WHERE member_id = ? AND signal_type = 'mood_logged' AND created_at >= ?
             AND json_extract(payload_json, '$.mood') = 'low'""",
        (member_id, mood_cutoff),
    ).fetchone()

    count = row["cnt"]
    if count < REPEATED_LOW_MOOD_COUNT:
        return None

    latest_ts = row["latest_ts"]

    signal_ids = [
        r["id"]
        for r in conn.execute(
            """SELECT id FROM signals
               WHERE member_id = ? AND signal_type = 'mood_logged' AND created_at >= ?
                 AND json_extract(payload_json, '$.mood') = 'low'
               ORDER BY created_at DESC""",
            (member_id, mood_cutoff),
        ).fetchall()
    ]

    confidence, factors = score_repeated_low_mood(
        low_mood_count=count,
        most_recent_mood_ts=latest_ts,
        mood_lookback_days=MOOD_LOOKBACK_DAYS,
        threshold=REPEATED_LOW_MOOD_COUNT,
    )

    return NudgeCandidate(
        nudge_type="support_risk",
        matched_reason="repeated_low_mood",
        explanation_basis=f"Low mood logged {count} times in the last {MOOD_LOOKBACK_DAYS} days",
        confidence=confidence,
        confidence_factors=factors,
        escalation_recommended=True,
        source_signal_ids=signal_ids,
        priority=PRIORITY["support_risk"],
        latest_signal_ts=latest_ts,
    )


ALL_EVALUATORS = [
    check_meal_goal_mismatch,
    check_missing_weight_log,
    check_support_risk,
    check_repeated_low_mood,
]
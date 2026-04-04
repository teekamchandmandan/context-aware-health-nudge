import json
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .database import _connect, init_db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _id() -> str:
    return uuid4().hex


def reset_and_seed() -> None:
    init_db()
    conn = _connect()
    try:
        _clear(conn)
        _seed(conn)
        conn.commit()
    finally:
        conn.close()


def _clear(conn: sqlite3.Connection) -> None:
    for table in [
        "audit_events",
        "escalations",
        "nudge_actions",
        "nudges",
        "signals",
        "members",
    ]:
        conn.execute(f"DELETE FROM {table}")


def _seed(conn: sqlite3.Connection) -> None:
    now = _now()

    members = [
        ("member_meal_01", "Alice Chen", "low_carb", None, _ts(now - timedelta(days=30))),
        ("member_weight_01", "Bob Martinez", "weight_loss", None, _ts(now - timedelta(days=30))),
        ("member_support_01", "Carol Davis", "balanced", None, _ts(now - timedelta(days=30))),
        ("member_catchup_01", "Diego Rivera", "balanced", None, _ts(now - timedelta(days=30))),
    ]
    conn.executemany(
        "INSERT INTO members (id, name, goal_type, profile_json, created_at) VALUES (?, ?, ?, ?, ?)",
        members,
    )

    signals = [
        (
            _id(),
            "member_meal_01",
            "meal_logged",
            json.dumps(
                {
                    "meal_type": "dinner",
                    "carbs_g": 72,
                    "protein_g": 28,
                    "photo_attached": True,
                    "analysis_summary": "Estimated from the uploaded meal photo. Saved values may be approximate.",
                    "analysis_confidence": 0.74,
                    "analysis_status": "estimated",
                    "analysis_source": "llm",
                }
            ),
            _ts(now - timedelta(hours=6)),
        ),
        (
            _id(),
            "member_weight_01",
            "weight_logged",
            json.dumps({"weight_lb": 182.4}),
            _ts(now - timedelta(days=7)),
        ),
        (
            _id(),
            "member_support_01",
            "mood_logged",
            json.dumps({"mood": "low"}),
            _ts(now - timedelta(days=1)),
        ),
        (
            _id(),
            "member_catchup_01",
            "weight_logged",
            json.dumps({"weight_lb": 168.2}),
            _ts(now - timedelta(days=1)),
        ),
    ]
    conn.executemany(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        signals,
    )

    nudge_acted_id = _id()
    nudge_dismissed_1_id = _id()
    nudge_dismissed_2_id = _id()

    nudges = [
        (
            nudge_acted_id,
            "member_support_01",
            "weight_check_in",
            "Time for a quick weight check-in.",
            "It has been a few days since your last weigh-in.",
            "missing_weight_log",
            0.68,
            0,
            "acted",
            "rule_engine",
            "template",
            _ts(now - timedelta(days=5)),
            _ts(now - timedelta(days=5)),
        ),
        (
            nudge_dismissed_1_id,
            "member_support_01",
            "weight_check_in",
            "A short check-in can help us keep your plan on track.",
            "It had been a few days since your last logged update.",
            "missing_weight_log",
            0.68,
            0,
            "dismissed",
            "rule_engine",
            "template",
            _ts(now - timedelta(days=3)),
            _ts(now - timedelta(days=3)),
        ),
        (
            nudge_dismissed_2_id,
            "member_support_01",
            "weight_check_in",
            "Share a quick update when you are ready.",
            "A recent check-in would help us keep your guidance current.",
            "missing_weight_log",
            0.68,
            0,
            "dismissed",
            "rule_engine",
            "template",
            _ts(now - timedelta(days=2)),
            _ts(now - timedelta(days=2)),
        ),
    ]
    conn.executemany(
        """INSERT INTO nudges
           (id, member_id, nudge_type, content, explanation, matched_reason,
            confidence, escalation_recommended, status, generated_by, phrasing_source,
            created_at, delivered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        nudges,
    )

    actions = [
        (_id(), nudge_acted_id, "act_now", None, _ts(now - timedelta(days=5, hours=-1))),
        (_id(), nudge_dismissed_1_id, "dismiss", None, _ts(now - timedelta(days=3, hours=-1))),
        (_id(), nudge_dismissed_2_id, "dismiss", None, _ts(now - timedelta(days=2, hours=-1))),
    ]
    conn.executemany(
        "INSERT INTO nudge_actions (id, nudge_id, action_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        actions,
    )
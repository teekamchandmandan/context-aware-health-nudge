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
        ("member_catchup_01", "Diego Rivera", "low_carb", None, _ts(now - timedelta(days=30))),
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
                    "meal_profile": "higher_carb",
                    "visible_food_summary": "The photo appears to show a pasta dish with bread.",
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
            _ts(now - timedelta(hours=48)),
        ),
        (
            _id(),
            "member_support_01",
            "mood_logged",
            json.dumps({"mood": "low"}),
            _ts(now - timedelta(hours=30)),
        ),
        (
            _id(),
            "member_support_01",
            "mood_logged",
            json.dumps({"mood": "low"}),
            _ts(now - timedelta(hours=6)),
        ),
        (
            _id(),
            "member_support_01",
            "weight_logged",
            json.dumps({"weight_lb": 145.0}),
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
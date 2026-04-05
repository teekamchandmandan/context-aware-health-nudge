import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.models.signals import SignalResponse


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


_LATEST_SIGNAL_TYPES = ("weight_logged", "sleep_logged", "mood_logged")


def get_latest_signals(
    conn: sqlite3.Connection,
    member_id: str,
) -> dict[str, dict]:
    """Return the most recent signal per type for a member."""
    placeholders = ",".join("?" for _ in _LATEST_SIGNAL_TYPES)
    rows = conn.execute(
        f"""
        SELECT s.signal_type, s.payload_json, s.created_at
        FROM signals s
        INNER JOIN (
            SELECT signal_type, MAX(created_at) AS max_ts
            FROM signals
            WHERE member_id = ? AND signal_type IN ({placeholders})
            GROUP BY signal_type
        ) latest ON s.signal_type = latest.signal_type
                  AND s.created_at = latest.max_ts
                  AND s.member_id = ?
        """,
        (member_id, *_LATEST_SIGNAL_TYPES, member_id),
    ).fetchall()

    result: dict[str, dict] = {}
    for row in rows:
        payload = json.loads(row["payload_json"]) if isinstance(row["payload_json"], str) else row["payload_json"]
        result[row["signal_type"]] = {
            "payload": payload,
            "logged_at": row["created_at"],
        }
    return result


def persist_signal(
    conn: sqlite3.Connection,
    *,
    member_id: str,
    signal_type: str,
    payload_dict: dict,
) -> SignalResponse:
    signal_id = uuid4().hex
    now = utc_timestamp()

    conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (signal_id, member_id, signal_type, json.dumps(payload_dict), now),
    )
    conn.commit()

    return SignalResponse(
        id=signal_id,
        member_id=member_id,
        signal_type=signal_type,
        payload=payload_dict,
        created_at=now,
    )
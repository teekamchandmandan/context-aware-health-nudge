import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.models.signals import SignalResponse


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


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
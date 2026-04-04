import json
import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


LOGGER = logging.getLogger("app.audit")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def record_audit_event(
    conn: sqlite3.Connection,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> None:
    conn.execute(
        """INSERT INTO audit_events (id, event_type, entity_type, entity_id, payload_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (uuid4().hex, event_type, entity_type, entity_id, json.dumps(payload), _ts()),
    )


def log_structured_event(level: int, event_type: str, payload: dict) -> None:
    LOGGER.log(level, json.dumps({"event_type": event_type, **payload}, sort_keys=True))
import json
import sqlite3

from app.core.config import OPENAI_MODEL



def latest_audit_payload(
    conn: sqlite3.Connection,
    event_type: str,
    *,
    entity_id: str | None = None,
) -> dict | None:
    query = "SELECT payload_json FROM audit_events WHERE event_type = ?"
    params: list[str] = [event_type]
    if entity_id is not None:
        query += " AND entity_id = ?"
        params.append(entity_id)
    query += " ORDER BY created_at DESC LIMIT 1"
    row = conn.execute(query, tuple(params)).fetchone()
    return json.loads(row["payload_json"]) if row else None

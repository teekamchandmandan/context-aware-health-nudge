import logging
import sqlite3

from app.observability.audit import log_structured_event, record_audit_event

PROVIDER_NAME = "openai"


def record_llm_call(
    conn: sqlite3.Connection,
    nudge_id: str,
    member_id: str,
    nudge_type: str,
    *,
    success: bool,
    latency_ms: int,
    phrasing_source: str | None = None,
) -> None:
    payload = {
        "member_id": member_id,
        "nudge_type": nudge_type,
        "provider": PROVIDER_NAME,
        "success": success,
        "latency_ms": latency_ms,
    }
    if phrasing_source is not None:
        payload["phrasing_source"] = phrasing_source
    record_audit_event(conn, "llm_call", "nudge", nudge_id, payload)
    log_structured_event(logging.INFO if success else logging.WARNING, "llm_call", {**payload, "nudge_id": nudge_id})


def record_fallback(
    conn: sqlite3.Connection,
    nudge_id: str,
    member_id: str,
    nudge_type: str,
    reason: str,
) -> None:
    payload = {
        "member_id": member_id,
        "nudge_type": nudge_type,
        "fallback_reason": reason,
    }
    record_audit_event(conn, "llm_fallback", "nudge", nudge_id, payload)
    log_structured_event(logging.WARNING, "llm_fallback", {**payload, "nudge_id": nudge_id})
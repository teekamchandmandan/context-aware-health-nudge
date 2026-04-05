import logging
import sqlite3

from app.observability.audit import log_structured_event, record_audit_event

PROMPT_AREA = "meal_analysis"


def record_llm_call(
    conn: sqlite3.Connection,
    member_id: str,
    *,
    success: bool,
    latency_ms: int,
    model_name: str,
    analysis_source: str | None = None,
) -> None:
    payload = {
        "member_id": member_id,
        "prompt_area": PROMPT_AREA,
        "model_name": model_name,
        "success": success,
        "latency_ms": latency_ms,
    }
    if analysis_source is not None:
        payload["analysis_source"] = analysis_source
    record_audit_event(conn, "llm_call", "member", member_id, payload)
    log_structured_event(logging.INFO if success else logging.WARNING, "llm_call", payload)


def record_fallback(
    conn: sqlite3.Connection,
    member_id: str,
    *,
    reason: str,
    model_name: str,
) -> None:
    payload = {
        "member_id": member_id,
        "prompt_area": PROMPT_AREA,
        "model_name": model_name,
        "fallback_reason": reason,
    }
    record_audit_event(conn, "llm_fallback", "member", member_id, payload)
    log_structured_event(logging.WARNING, "llm_fallback", payload)
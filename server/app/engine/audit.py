import logging
import sqlite3

from app.observability.audit import log_structured_event, record_audit_event

from .common import NudgeCandidate


def record_nudge_generated(
    conn: sqlite3.Connection,
    member_id: str,
    nudge_id: str,
    candidate: NudgeCandidate,
    *,
    phrasing_source: str,
    escalation_decision: bool,
) -> None:
    payload = {
        "member_id": member_id,
        "nudge_id": nudge_id,
        "nudge_type": candidate.nudge_type,
        "matched_reason": candidate.matched_reason,
        "confidence": candidate.confidence,
        "phrasing_source": phrasing_source,
    }
    record_audit_event(conn, "nudge_generated", "nudge", nudge_id, payload)
    log_structured_event(
        logging.INFO,
        "nudge_generated",
        {**payload, "escalation_decision": escalation_decision},
    )


def record_escalation_created(
    conn: sqlite3.Connection,
    escalation_id: str,
    *,
    member_id: str,
    nudge_id: str,
    reason: str,
    source: str,
    status: str,
) -> None:
    payload = {
        "member_id": member_id,
        "nudge_id": nudge_id,
        "reason": reason,
        "source": source,
        "status": status,
    }
    record_audit_event(conn, "escalation_created", "escalation", escalation_id, payload)
    log_structured_event(logging.INFO, "escalation_created", {**payload, "escalation_id": escalation_id})
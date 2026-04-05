import sqlite3

from app import phrasing

from .audit import record_escalation_created, record_nudge_generated
from .common import CONFIDENCE_LOW_THRESHOLD, NudgeCandidate, _id, _now, _ts


def create_nudge_row(
    conn: sqlite3.Connection, member_id: str, candidate: NudgeCandidate, status: str
) -> str:
    nudge_id = _id()
    now = _now()
    delivered_at = _ts(now) if status == "active" else None
    template = phrasing.get_template_phrasing(candidate.nudge_type)
    content = template["content"] if status == "active" else None
    explanation = template["explanation"] if status == "active" else candidate.explanation_basis
    conn.execute(
        """INSERT INTO nudges
           (id, member_id, nudge_type, content, explanation, matched_reason,
            confidence, escalation_recommended, status, generated_by, phrasing_source,
            created_at, delivered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            nudge_id,
            member_id,
            candidate.nudge_type,
            content,
            explanation,
            candidate.matched_reason,
            candidate.confidence,
            1 if candidate.escalation_recommended else 0,
            status,
            "rule_engine",
            "template",
            _ts(now),
            delivered_at,
        ),
    )
    return nudge_id


def create_escalation(
    conn: sqlite3.Connection, member_id: str, nudge_id: str, reason: str
) -> str:
    escalation_id = _id()
    conn.execute(
        """INSERT INTO escalations (id, nudge_id, member_id, reason, source, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (escalation_id, nudge_id, member_id, reason, "rule_engine", "open", _ts(_now())),
    )
    return escalation_id


def create_nudge_from_candidate(
    conn: sqlite3.Connection, member_id: str, candidate: NudgeCandidate
) -> dict:
    if candidate.confidence < CONFIDENCE_LOW_THRESHOLD or candidate.escalation_recommended:
        nudge_id = create_nudge_row(conn, member_id, candidate, "escalated")
        record_nudge_generated(
            conn,
            member_id,
            nudge_id,
            candidate,
            phrasing_source="template",
            escalation_decision=True,
        )
        escalation_id = create_escalation(conn, member_id, nudge_id, candidate.explanation_basis)
        record_escalation_created(
            conn,
            escalation_id,
            member_id=member_id,
            nudge_id=nudge_id,
            reason=candidate.explanation_basis,
            source="rule_engine",
            status="open",
        )
        return {"state": "escalated", "nudge_id": nudge_id, "escalation_id": escalation_id}

    nudge_id = create_nudge_row(conn, member_id, candidate, "active")
    member_goal = conn.execute(
        "SELECT goal_type FROM members WHERE id = ?",
        (member_id,),
    ).fetchone()["goal_type"]
    nudge, llm_metadata = phrasing.maybe_apply_llm_phrasing(
        conn,
        nudge_id,
        member_id=member_id,
        member_goal=member_goal,
        nudge_type=candidate.nudge_type,
        matched_reason=candidate.matched_reason,
        explanation_basis=candidate.explanation_basis,
        confidence=candidate.confidence,
    )
    record_nudge_generated(
        conn,
        member_id,
        nudge_id,
        candidate,
        phrasing_source=nudge["phrasing_source"],
        escalation_decision=False,
        llm_model_name=llm_metadata["model_name"] if llm_metadata is not None else None,
    )
    return {"state": "active", "nudge": dict(nudge)}
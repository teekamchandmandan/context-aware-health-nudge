import json
import logging
import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.api.deps import DbDep
from app.audit import record_audit_event, log_structured_event
from app.models.coach import (
    CoachEscalationItem,
    CoachEscalationListResponse,
    CoachNudgeItem,
    CoachNudgeListResponse,
)
from app.services.signals import utc_timestamp

router = APIRouter(prefix="/api/coach", tags=["coach"])


COACH_NUDGES_QUERY = """SELECT n.id, n.member_id, m.name AS member_name, n.nudge_type,
                              n.content, n.explanation, n.matched_reason, n.confidence,
                              n.confidence_factors_json,
                              n.escalation_recommended, n.status, n.phrasing_source,
                              n.created_at,
                              (
                                  SELECT s.payload_json
                                  FROM signals s
                                  WHERE s.member_id = n.member_id
                                      AND s.signal_type = 'meal_logged'
                                      AND s.created_at <= n.created_at
                                  ORDER BY s.created_at DESC
                                  LIMIT 1
                              ) AS meal_payload_json,
                              (
                                  SELECT na.action_type
                                  FROM nudge_actions na
                                  WHERE na.nudge_id = n.id
                                  ORDER BY na.created_at DESC, na.id DESC
                                  LIMIT 1
                              ) AS latest_action_type
                       FROM nudges n
                       JOIN members m ON n.member_id = m.id
                       ORDER BY n.created_at DESC
                       LIMIT ?"""

COACH_ESCALATIONS_QUERY = """SELECT e.id, e.member_id, m.name AS member_name, e.reason,
                                   e.source, e.status, e.created_at
                            FROM escalations e
                            JOIN members m ON e.member_id = m.id
                            WHERE e.status = 'open'
                            ORDER BY e.created_at DESC
                            LIMIT ?"""


def _extract_visible_food_summary(payload_json: str | None) -> str | None:
    if not payload_json:
        return None

    try:
        payload = json.loads(payload_json)
    except (TypeError, ValueError):
        return None

    summary = payload.get("visible_food_summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    return None


def _get_coach_nudge_visible_food_summary(row: sqlite3.Row) -> str | None:
    if row["nudge_type"] != "meal_guidance":
        return None
    return _extract_visible_food_summary(row["meal_payload_json"])


def _build_coach_nudge_item(row: sqlite3.Row) -> CoachNudgeItem:
    factors_raw = row["confidence_factors_json"]
    factors = json.loads(factors_raw) if factors_raw else None
    return CoachNudgeItem(
        nudge_id=row["id"],
        member_id=row["member_id"],
        member_name=row["member_name"],
        nudge_type=row["nudge_type"],
        visible_food_summary=_get_coach_nudge_visible_food_summary(row),
        content=row["content"],
        explanation=row["explanation"],
        matched_reason=row["matched_reason"],
        confidence=row["confidence"],
        confidence_factors=factors,
        escalation_recommended=bool(row["escalation_recommended"]),
        status=row["status"],
        latest_action=row["latest_action_type"],
        phrasing_source=row["phrasing_source"] or "template",
        created_at=row["created_at"],
    )


def _build_coach_escalation_item(row: sqlite3.Row) -> CoachEscalationItem:
    return CoachEscalationItem(
        escalation_id=row["id"],
        member_id=row["member_id"],
        member_name=row["member_name"],
        reason=row["reason"],
        source=row["source"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.get("/nudges")
def get_coach_nudges(
    conn: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoachNudgeListResponse:
    rows = conn.execute(COACH_NUDGES_QUERY, (limit,)).fetchall()
    items = [_build_coach_nudge_item(row) for row in rows]

    return CoachNudgeListResponse(items=items, limit=limit, count=len(items))


@router.get("/escalations")
def get_coach_escalations(
    conn: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoachEscalationListResponse:
    rows = conn.execute(COACH_ESCALATIONS_QUERY, (limit,)).fetchall()
    items = [_build_coach_escalation_item(row) for row in rows]

    return CoachEscalationListResponse(items=items, limit=limit, count=len(items))


@router.post("/escalations/{escalation_id}/resolve")
def resolve_escalation(
    escalation_id: Annotated[str, Path()],
    conn: DbDep,
) -> CoachEscalationItem:
    now = utc_timestamp()
    cursor = conn.execute(
        "UPDATE escalations SET status = 'resolved', resolved_at = ? WHERE id = ? AND status = 'open'",
        (now, escalation_id),
    )

    if cursor.rowcount == 0:
        row = conn.execute(
            "SELECT e.id, e.member_id, m.name AS member_name, e.reason, e.source, e.status, e.created_at FROM escalations e JOIN members m ON e.member_id = m.id WHERE e.id = ?",
            (escalation_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Escalation not found")
        raise HTTPException(status_code=409, detail="Escalation is already resolved")

    record_audit_event(
        conn,
        event_type="escalation_resolved",
        entity_type="escalation",
        entity_id=escalation_id,
        payload={"resolved_at": now},
    )
    conn.commit()

    log_structured_event(
        logging.INFO,
        "escalation_resolved",
        {"escalation_id": escalation_id, "resolved_at": now},
    )

    row = conn.execute(
        "SELECT e.id, e.member_id, m.name AS member_name, e.reason, e.source, e.status, e.created_at FROM escalations e JOIN members m ON e.member_id = m.id WHERE e.id = ?",
        (escalation_id,),
    ).fetchone()

    return CoachEscalationItem(
        escalation_id=row["id"],
        member_id=row["member_id"],
        member_name=row["member_name"],
        reason=row["reason"],
        source=row["source"],
        status=row["status"],
        created_at=row["created_at"],
    )
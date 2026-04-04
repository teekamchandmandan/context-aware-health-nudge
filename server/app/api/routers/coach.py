from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbDep
from app.models.coach import (
    CoachEscalationItem,
    CoachEscalationListResponse,
    CoachNudgeItem,
    CoachNudgeListResponse,
)

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.get("/nudges")
def get_coach_nudges(
    conn: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoachNudgeListResponse:
    rows = conn.execute(
        """SELECT n.id, n.member_id, m.name AS member_name, n.nudge_type,
                  n.content, n.explanation, n.matched_reason, n.confidence,
                  n.escalation_recommended, n.status, n.phrasing_source,
                  n.created_at,
                  la.action_type AS latest_action_type
           FROM nudges n
           JOIN members m ON n.member_id = m.id
           LEFT JOIN (
               SELECT nudge_id, action_type, MAX(created_at) AS max_created_at
               FROM nudge_actions
               GROUP BY nudge_id
           ) la ON la.nudge_id = n.id
           ORDER BY n.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    items = [
        CoachNudgeItem(
            nudge_id=row["id"],
            member_id=row["member_id"],
            member_name=row["member_name"],
            nudge_type=row["nudge_type"],
            content=row["content"],
            explanation=row["explanation"],
            matched_reason=row["matched_reason"],
            confidence=row["confidence"],
            escalation_recommended=bool(row["escalation_recommended"]),
            status=row["status"],
            latest_action=row["latest_action_type"],
            phrasing_source=row["phrasing_source"] or "template",
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return CoachNudgeListResponse(items=items, limit=limit, count=len(items))


@router.get("/escalations")
def get_coach_escalations(
    conn: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoachEscalationListResponse:
    rows = conn.execute(
        """SELECT e.id, e.member_id, m.name AS member_name, e.reason,
                  e.source, e.status, e.created_at
           FROM escalations e
           JOIN members m ON e.member_id = m.id
           WHERE e.status = 'open'
           ORDER BY e.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    items = [
        CoachEscalationItem(
            escalation_id=row["id"],
            member_id=row["member_id"],
            member_name=row["member_name"],
            reason=row["reason"],
            source=row["source"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return CoachEscalationListResponse(items=items, limit=limit, count=len(items))
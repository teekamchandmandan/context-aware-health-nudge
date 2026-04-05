import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Path, HTTPException

from app.api.deps import DbDep, get_nudge_or_404
from app.models.actions import ActionRequest, ActionResponse
from app.observability.audit import log_structured_event, record_audit_event
from app.services.signals import utc_timestamp

router = APIRouter(prefix="/api/nudges", tags=["nudges"])

TERMINAL_STATUSES = {"acted", "dismissed", "escalated", "superseded"}


@router.post("/{nudge_id}/action")
def post_nudge_action(
    nudge_id: Annotated[str, Path()],
    body: ActionRequest,
    conn: DbDep,
) -> ActionResponse:
    nudge = get_nudge_or_404(conn, nudge_id)
    previous_status = nudge["status"]

    if previous_status in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="Nudge is already in a terminal state")

    action_type = body.action_type.value
    new_status = {
        "act_now": "acted",
        "dismiss": "dismissed",
        "ask_for_help": "escalated",
    }[action_type]

    cursor = conn.execute(
        "UPDATE nudges SET status = ? WHERE id = ? AND status NOT IN ('acted', 'dismissed', 'escalated', 'superseded')",
        (new_status, nudge_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=409, detail="Nudge is already in a terminal state")

    action_id = uuid4().hex
    now = utc_timestamp()
    conn.execute(
        "INSERT INTO nudge_actions (id, nudge_id, action_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (action_id, nudge_id, action_type, None, now),
    )

    escalation_created = False
    user_action_payload = {
        "member_id": nudge["member_id"],
        "nudge_id": nudge_id,
        "action_type": action_type,
        "previous_status": previous_status,
        "new_status": new_status,
    }
    record_audit_event(conn, "user_action", "nudge", nudge_id, user_action_payload)

    if action_type == "ask_for_help":
        esc_id = uuid4().hex
        reason = "Member requested help"
        conn.execute(
            """INSERT INTO escalations (id, nudge_id, member_id, reason, source, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (esc_id, nudge_id, nudge["member_id"], reason, "member_action", "open", now),
        )
        escalation_payload = {
            "member_id": nudge["member_id"],
            "nudge_id": nudge_id,
            "reason": reason,
            "source": "member_action",
            "status": "open",
        }
        record_audit_event(conn, "escalation_created", "escalation", esc_id, escalation_payload)
        log_structured_event(logging.INFO, "escalation_created", {**escalation_payload, "escalation_id": esc_id})
        escalation_created = True

    log_structured_event(
        logging.INFO,
        "user_action",
        {**user_action_payload, "escalation_created": escalation_created},
    )

    conn.commit()

    return ActionResponse(
        nudge_id=nudge_id,
        action_type=action_type,
        nudge_status=new_status,
        recorded_at=now,
    )
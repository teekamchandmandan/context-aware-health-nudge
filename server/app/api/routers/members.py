from typing import Annotated
from functools import partial

import anyio
from fastapi import APIRouter, File, Path, Request, UploadFile

from app.api.deps import DbDep, get_member_or_404
from app.engine import evaluate_member
from app.models.member import MemberNudgeResponse
from app.models.shared import MemberRef, NudgeDetail, NudgeState
from app.models.signals import SignalRequest, SignalResponse
from app.services.meal_logging import (
    build_meal_log_payload,
    create_meal_draft_response,
    read_meal_photo,
    validate_meal_upload_form,
)
from app.services.signals import persist_signal

router = APIRouter(prefix="/api/members", tags=["members"])


def _build_member_nudge_response(member: MemberRef, result: dict) -> MemberNudgeResponse:
    if result["state"] == "active":
        nudge = result["nudge"]
        return MemberNudgeResponse(
            state=NudgeState.active,
            member=member,
            nudge=NudgeDetail(
                id=nudge["id"],
                nudge_type=nudge["nudge_type"],
                content=nudge["content"],
                explanation=nudge["explanation"],
                matched_reason=nudge["matched_reason"],
                confidence=nudge["confidence"],
                escalation_recommended=bool(nudge["escalation_recommended"]),
                status=nudge["status"],
                phrasing_source=nudge["phrasing_source"],
                created_at=nudge["created_at"],
            ),
        )

    if result["state"] == "escalated":
        return MemberNudgeResponse(
            state=NudgeState.escalated,
            member=member,
            nudge=None,
        )

    return MemberNudgeResponse(
        state=NudgeState.no_nudge,
        member=member,
        nudge=None,
    )


@router.get("/{member_id}/nudge", response_model_exclude_none=True)
def get_member_nudge(
    member_id: Annotated[str, Path()],
    conn: DbDep,
) -> MemberNudgeResponse:
    member_row = get_member_or_404(conn, member_id)
    member = MemberRef(id=member_row["id"], name=member_row["name"])

    existing_esc = conn.execute(
        "SELECT id FROM escalations WHERE member_id = ? AND status = 'open' LIMIT 1",
        (member_id,),
    ).fetchone()
    if existing_esc:
        return MemberNudgeResponse(state=NudgeState.escalated, member=member)

    result = evaluate_member(conn, member_id)
    return _build_member_nudge_response(member, result)


@router.post("/{member_id}/meal-logs", response_model_exclude_none=True)
async def post_member_meal_log(
    member_id: Annotated[str, Path()],
    conn: DbDep,
    request: Request,
    photo: Annotated[UploadFile | None, File()] = None,
) -> SignalResponse:
    get_member_or_404(conn, member_id)
    await validate_meal_upload_form(request)

    photo_bytes, photo_content_type = await read_meal_photo(photo, require_image=True)

    meal_analysis = await anyio.to_thread.run_sync(
        partial(
            create_meal_draft_response,
            conn=conn,
            member_id=member_id,
            photo_bytes=photo_bytes,
            photo_content_type=photo_content_type,
        )
    )

    return persist_signal(
        conn,
        member_id=member_id,
        signal_type="meal_logged",
        payload_dict=build_meal_log_payload(meal_analysis),
    )


@router.post("/{member_id}/signals")
def post_member_signal(
    member_id: Annotated[str, Path()],
    body: SignalRequest,
    conn: DbDep,
) -> SignalResponse:
    get_member_or_404(conn, member_id)
    return persist_signal(
        conn,
        member_id=member_id,
        signal_type=body.signal_type.value,
        payload_dict=body.payload.model_dump(exclude_none=True),
    )
from typing import Annotated
from functools import partial

import anyio
from fastapi import APIRouter, File, Form, Path, UploadFile

from app.api.deps import DbDep, get_member_or_404
from app.engine import evaluate_member
from app.models.meals import MealDraftResponse
from app.models.member import MemberNudgeResponse
from app.models.shared import MemberRef, NudgeDetail, NudgeState
from app.models.signals import SignalRequest, SignalResponse
from app.services.meal_logging import (
    build_meal_log_payload,
    create_meal_draft_response,
    read_meal_photo,
    validate_meal_log_input,
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
            escalation_created=True,
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


@router.post("/{member_id}/meal-drafts", response_model_exclude_none=True)
async def post_meal_draft(
    member_id: Annotated[str, Path()],
    description: Annotated[str, Form(min_length=2, max_length=500)],
    conn: DbDep,
    photo: Annotated[UploadFile | None, File()] = None,
) -> MealDraftResponse:
    get_member_or_404(conn, member_id)

    photo_bytes, photo_content_type = await read_meal_photo(photo, require_image=False)
    return await anyio.to_thread.run_sync(
        partial(
            create_meal_draft_response,
            description,
            photo_bytes=photo_bytes,
            photo_content_type=photo_content_type,
        )
    )


@router.post("/{member_id}/meal-logs", response_model_exclude_none=True)
async def post_member_meal_log(
    member_id: Annotated[str, Path()],
    conn: DbDep,
    description: Annotated[str | None, Form(max_length=500)] = None,
    photo: Annotated[UploadFile | None, File()] = None,
) -> SignalResponse:
    get_member_or_404(conn, member_id)

    meal_input = validate_meal_log_input(
        description=description,
        photo_attached=photo is not None,
    )
    photo_bytes, photo_content_type = await read_meal_photo(photo, require_image=True)

    analysis_input = meal_input.description or "Meal photo upload"
    meal_analysis = await anyio.to_thread.run_sync(
        partial(
            create_meal_draft_response,
            analysis_input,
            photo_bytes=photo_bytes,
            photo_content_type=photo_content_type,
        )
    )

    return persist_signal(
        conn,
        member_id=member_id,
        signal_type="meal_logged",
        payload_dict=build_meal_log_payload(meal_input, meal_analysis),
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
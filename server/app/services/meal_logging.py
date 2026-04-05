from __future__ import annotations

from importlib import import_module
import sqlite3

from fastapi import HTTPException, Request, UploadFile

from app.models.meals import MealDraftResponse

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MEAL_UPLOAD_FIELDS = frozenset({"photo"})


def _get_create_meal_draft():
    main_module = import_module("app.main")
    return getattr(main_module, "create_meal_draft")


async def validate_meal_upload_form(request: Request) -> None:
    form = await request.form()
    unexpected_fields = sorted({key for key in form.keys() if key not in ALLOWED_MEAL_UPLOAD_FIELDS})
    if unexpected_fields:
        field_list = ", ".join(unexpected_fields)
        raise HTTPException(status_code=422, detail=f"unexpected meal upload fields: {field_list}")


async def read_meal_photo(
    photo: UploadFile | None,
    *,
    require_image: bool,
) -> tuple[bytes | None, str | None]:
    if photo is None:
        if require_image:
            raise HTTPException(status_code=422, detail="meal logging requires a meal photo")
        return None, None

    photo_content_type = photo.content_type or ""
    if require_image and not photo_content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="meal photo must be an image")

    data = await photo.read()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="meal photo exceeds 10 MB limit")

    return data, photo_content_type or None


def create_meal_draft_response(
    *,
    conn: sqlite3.Connection,
    member_id: str,
    photo_bytes: bytes | None,
    photo_content_type: str | None,
) -> MealDraftResponse:
    return _get_create_meal_draft()(  # Preserve the historical patch target at app.main.create_meal_draft.
        conn=conn,
        member_id=member_id,
        photo_bytes=photo_bytes,
        photo_content_type=photo_content_type,
    )


def build_meal_log_payload(
    meal_analysis: MealDraftResponse,
) -> dict[str, object]:
    payload_dict: dict[str, object] = {
        "meal_profile": meal_analysis.meal_profile,
    }

    if meal_analysis.visible_food_summary:
        payload_dict["visible_food_summary"] = meal_analysis.visible_food_summary

    return payload_dict
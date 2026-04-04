from __future__ import annotations

from importlib import import_module

from fastapi import HTTPException, Request, UploadFile
from pydantic import ValidationError

from app.models.meals import MealDraftResponse, MealLogInput

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


def validate_meal_log_input(
    *,
    photo_attached: bool,
) -> MealLogInput:
    try:
        return MealLogInput(
            photo_attached=photo_attached,
        )
    except ValidationError as exc:
        detail = exc.errors()[0].get("msg", "Invalid meal log")
        raise HTTPException(status_code=422, detail=detail) from exc


def create_meal_draft_response(
    *,
    photo_bytes: bytes | None,
    photo_content_type: str | None,
) -> MealDraftResponse:
    return _get_create_meal_draft()(  # Preserve the historical patch target at app.main.create_meal_draft.
        photo_bytes=photo_bytes,
        photo_content_type=photo_content_type,
    )


def build_meal_log_payload(
    meal_input: MealLogInput,
    meal_analysis: MealDraftResponse,
) -> dict[str, object]:
    payload_dict: dict[str, object] = {
        "photo_attached": meal_input.photo_attached,
        "analysis_source": meal_analysis.analysis_source,
        "analysis_status": meal_analysis.analysis_status,
    }

    if meal_analysis.meal_type:
        payload_dict["meal_type"] = meal_analysis.meal_type
    if meal_analysis.carbs_g is not None:
        payload_dict["carbs_g"] = meal_analysis.carbs_g
    if meal_analysis.protein_g is not None:
        payload_dict["protein_g"] = meal_analysis.protein_g
    if meal_analysis.analysis_summary:
        payload_dict["analysis_summary"] = meal_analysis.analysis_summary
    if meal_analysis.analysis_confidence is not None:
        payload_dict["analysis_confidence"] = meal_analysis.analysis_confidence

    return payload_dict
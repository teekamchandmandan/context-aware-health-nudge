from __future__ import annotations

from importlib import import_module

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from app.models.meals import MealDraftResponse, MealLogInput

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB


def _get_create_meal_draft():
    main_module = import_module("app.main")
    return getattr(main_module, "create_meal_draft")


async def read_meal_photo(
    photo: UploadFile | None,
    *,
    require_image: bool,
) -> tuple[bytes | None, str | None]:
    if photo is None:
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
    meal_name: str | None,
    description: str | None,
    photo_attached: bool,
) -> MealLogInput:
    try:
        return MealLogInput(
            meal_name=meal_name,
            description=description,
            photo_attached=photo_attached,
        )
    except ValidationError as exc:
        detail = exc.errors()[0].get("msg", "Invalid meal log")
        raise HTTPException(status_code=422, detail=detail) from exc


def create_meal_draft_response(
    description: str,
    *,
    photo_bytes: bytes | None,
    photo_content_type: str | None,
) -> MealDraftResponse:
    return _get_create_meal_draft()(  # Preserve the historical patch target at app.main.create_meal_draft.
        description,
        photo_bytes=photo_bytes,
        photo_content_type=photo_content_type,
    )


def build_meal_log_payload(
    meal_input: MealLogInput,
    meal_analysis: MealDraftResponse,
) -> dict[str, object]:
    payload_dict: dict[str, object] = {
        "meal_input_method": "one_step_with_photo" if meal_input.photo_attached else "one_step",
        "photo_attached": meal_input.photo_attached,
        "analysis_source": meal_analysis.analysis_source,
        "analysis_status": meal_analysis.analysis_status,
    }

    if meal_input.meal_name or meal_analysis.meal_name:
        payload_dict["meal_name"] = meal_input.meal_name or meal_analysis.meal_name
    if meal_input.description:
        payload_dict["description"] = meal_input.description
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
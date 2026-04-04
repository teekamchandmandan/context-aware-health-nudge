"""Meal analysis for one-step meal logging and legacy draft flows."""

from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.core.config import get_openai_api_key
from app.models.meals import MealDraftResponse

from .fallback import fallback_meal_draft
from .provider import request_meal_draft_json as _request_meal_draft_json


def create_meal_draft(
    description: str,
    *,
    photo_bytes: bytes | None = None,
    photo_content_type: str | None = None,
) -> MealDraftResponse:
    cleaned_description = description.strip()
    photo_attached = photo_bytes is not None
    api_key = get_openai_api_key()
    if not api_key:
        return fallback_meal_draft(cleaned_description, photo_attached=photo_attached)

    try:
        raw_content = _request_meal_draft_json(
            cleaned_description,
            api_key,
            photo_bytes=photo_bytes,
            photo_content_type=photo_content_type,
        )
        parsed = json.loads(raw_content)
        draft = MealDraftResponse.model_validate(
            {
                "description": cleaned_description,
                "photo_attached": photo_attached,
                **parsed,
            }
        )
        return draft.model_copy(
            update={
                "analysis_source": "llm",
                "analysis_status": draft.analysis_status or "estimated",
            }
        )
    except (httpx.HTTPError, httpx.TimeoutException, json.JSONDecodeError, ValidationError, ValueError):
        return fallback_meal_draft(cleaned_description, photo_attached=photo_attached)


__all__ = ["create_meal_draft", "get_openai_api_key", "_request_meal_draft_json"]
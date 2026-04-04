"""Meal analysis for one-step meal logging."""

from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from app.core.config import get_openai_api_key
from app.models.meals import MealDraftResponse

from .fallback import fallback_meal_analysis
from .provider import request_meal_analysis_json as _request_meal_analysis_json


def create_meal_draft(
    *,
    photo_bytes: bytes | None = None,
    photo_content_type: str | None = None,
) -> MealDraftResponse:
    api_key = get_openai_api_key()
    if not api_key:
        return fallback_meal_analysis()

    try:
        raw_content = _request_meal_analysis_json(
            api_key,
            photo_bytes=photo_bytes,
            photo_content_type=photo_content_type,
        )
        parsed = json.loads(raw_content)
        analysis = MealDraftResponse.model_validate(parsed)
        return analysis.model_copy(
            update={
                "analysis_source": "llm",
                "analysis_status": analysis.analysis_status or "estimated",
            }
        )
    except (httpx.HTTPError, httpx.TimeoutException, json.JSONDecodeError, ValidationError, ValueError):
        return fallback_meal_analysis()


__all__ = ["create_meal_draft", "get_openai_api_key", "_request_meal_analysis_json"]
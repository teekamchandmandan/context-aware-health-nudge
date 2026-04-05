"""Meal analysis for one-step meal logging."""

from __future__ import annotations

import sqlite3
import time

import httpx
from pydantic import ValidationError

from app.core.config import OPENAI_MODEL, get_openai_api_key
from app.models.meals import MealDraftResponse

from .audit import record_fallback as _record_fallback
from .audit import record_llm_call as _record_llm_call
from .fallback import fallback_meal_analysis
from .provider import parse_json_output as _parse_json_output
from .provider import request_meal_analysis_json as _request_meal_analysis_json


def create_meal_draft(
    *,
    photo_bytes: bytes | None = None,
    photo_content_type: str | None = None,
    conn: sqlite3.Connection | None = None,
    member_id: str | None = None,
) -> MealDraftResponse:
    def record_fallback(reason: str, model_name: str) -> None:
        if conn is not None and member_id is not None:
            _record_fallback(conn, member_id, reason=reason, model_name=model_name)

    def record_llm_call(*, success: bool, latency_ms: int, model_name: str, analysis_source: str | None = None) -> None:
        if conn is not None and member_id is not None:
            _record_llm_call(
                conn,
                member_id,
                success=success,
                latency_ms=latency_ms,
                model_name=model_name,
                analysis_source=analysis_source,
            )

    model_name = OPENAI_MODEL
    api_key = get_openai_api_key()
    if not api_key:
        record_fallback("missing_key", model_name)
        return fallback_meal_analysis()

    started = time.perf_counter()
    try:
        raw_content, model_name = _request_meal_analysis_json(
            api_key,
            photo_bytes=photo_bytes,
            photo_content_type=photo_content_type,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = _parse_json_output(raw_content)
        parsed.pop("meal_type", None)
        parsed.pop("carbs_g", None)
        parsed.pop("protein_g", None)
        parsed.pop("analysis_summary", None)
        parsed.pop("analysis_status", None)
        parsed.pop("analysis_source", None)
        parsed.pop("analysis_confidence", None)
        final_analysis = MealDraftResponse.model_validate(parsed)
    except httpx.TimeoutException:
        latency_ms = int((time.perf_counter() - started) * 1000)
        record_llm_call(success=False, latency_ms=latency_ms, model_name=model_name)
        record_fallback("timeout", model_name)
        return fallback_meal_analysis()
    except httpx.HTTPError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        record_llm_call(success=False, latency_ms=latency_ms, model_name=model_name)
        record_fallback("provider_error", model_name)
        return fallback_meal_analysis()
    except ValidationError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        record_llm_call(success=False, latency_ms=latency_ms, model_name=model_name)
        record_fallback("validation_failure", model_name)
        return fallback_meal_analysis()
    except ValueError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        record_llm_call(success=False, latency_ms=latency_ms, model_name=model_name)
        record_fallback("invalid_json", model_name)
        return fallback_meal_analysis()

    record_llm_call(success=True, latency_ms=latency_ms, model_name=model_name, analysis_source="llm")
    return final_analysis


__all__ = ["create_meal_draft", "get_openai_api_key", "_request_meal_analysis_json"]
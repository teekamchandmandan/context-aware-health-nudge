"""Optional LLM phrasing with deterministic fallback and validation."""

from __future__ import annotations

import json
import logging
import sqlite3
import time

import httpx
from pydantic import ValidationError

from app.core.config import OPENAI_MODEL, get_openai_api_key

from .audit import record_fallback as _record_fallback
from .audit import record_llm_call as _record_llm_call
from .models import FallbackReason, PhrasingOutput, PhrasingRequest
from .provider import parse_json_output as _parse_json_output
from .provider import request_llm_json as _request_llm_json
from .templates import desired_tone_for_confidence, get_template_phrasing


LOGGER = logging.getLogger("app.phrasing")


def _record_failed_phrasing_attempt(
    conn: sqlite3.Connection,
    nudge_id: str,
    *,
    member_id: str,
    nudge_type: str,
    latency_ms: int,
    fallback_reason: str,
    model_name: str,
) -> tuple[sqlite3.Row, None]:
    _record_llm_call(
        conn,
        nudge_id,
        member_id,
        nudge_type,
        success=False,
        latency_ms=latency_ms,
        model_name=model_name,
    )
    _record_fallback(conn, nudge_id, member_id, nudge_type, fallback_reason, model_name)
    return _get_nudge(conn, nudge_id), None


def maybe_apply_llm_phrasing(
    conn: sqlite3.Connection,
    nudge_id: str,
    *,
    member_id: str,
    member_goal: str,
    nudge_type: str,
    matched_reason: str,
    explanation_basis: str,
    confidence: float,
) -> tuple[sqlite3.Row, dict[str, str] | None]:
    model_name = OPENAI_MODEL
    api_key = get_openai_api_key()
    if not api_key:
        _record_fallback(
            conn,
            nudge_id,
            member_id,
            nudge_type,
            FallbackReason.missing_key.value,
            model_name,
        )
        return _get_nudge(conn, nudge_id), None

    request_model = PhrasingRequest(
        nudge_type=nudge_type,
        member_goal=member_goal,
        matched_reason=matched_reason,
        explanation_basis=explanation_basis,
        tone=desired_tone_for_confidence(confidence),
    )

    started = time.perf_counter()
    try:
        raw_content, model_name = _request_llm_json(request_model, api_key)
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = _parse_json_output(raw_content)
        phrasing = PhrasingOutput.model_validate(parsed)
    except httpx.TimeoutException:
        return _record_failed_phrasing_attempt(
            conn,
            nudge_id,
            member_id=member_id,
            nudge_type=nudge_type,
            latency_ms=int((time.perf_counter() - started) * 1000),
            fallback_reason=FallbackReason.timeout.value,
            model_name=model_name,
        )
    except httpx.HTTPError:
        return _record_failed_phrasing_attempt(
            conn,
            nudge_id,
            member_id=member_id,
            nudge_type=nudge_type,
            latency_ms=int((time.perf_counter() - started) * 1000),
            fallback_reason=FallbackReason.provider_error.value,
            model_name=model_name,
        )
    except json.JSONDecodeError:
        return _record_failed_phrasing_attempt(
            conn,
            nudge_id,
            member_id=member_id,
            nudge_type=nudge_type,
            latency_ms=int((time.perf_counter() - started) * 1000),
            fallback_reason=FallbackReason.invalid_json.value,
            model_name=model_name,
        )
    except ValidationError:
        return _record_failed_phrasing_attempt(
            conn,
            nudge_id,
            member_id=member_id,
            nudge_type=nudge_type,
            latency_ms=int((time.perf_counter() - started) * 1000),
            fallback_reason=FallbackReason.validation_failure.value,
            model_name=model_name,
        )
    except ValueError:
        return _record_failed_phrasing_attempt(
            conn,
            nudge_id,
            member_id=member_id,
            nudge_type=nudge_type,
            latency_ms=int((time.perf_counter() - started) * 1000),
            fallback_reason=FallbackReason.invalid_json.value,
            model_name=model_name,
        )

    conn.execute(
        "UPDATE nudges SET content = ?, explanation = ?, phrasing_source = 'llm' WHERE id = ?",
        (phrasing.content, phrasing.explanation, nudge_id),
    )
    _record_llm_call(
        conn,
        nudge_id,
        member_id,
        nudge_type,
        success=True,
        latency_ms=latency_ms,
        model_name=model_name,
        phrasing_source="llm",
    )
    return _get_nudge(conn, nudge_id), {"model_name": model_name}


def _get_nudge(conn: sqlite3.Connection, nudge_id: str) -> sqlite3.Row:
    return conn.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()


__all__ = [
    "FallbackReason",
    "PhrasingOutput",
    "PhrasingRequest",
    "get_openai_api_key",
    "get_template_phrasing",
    "maybe_apply_llm_phrasing",
    "_request_llm_json",
]
"""Optional LLM phrasing with deterministic fallback and validation."""

from __future__ import annotations

import json
import logging
import sqlite3
import time

import httpx
from pydantic import ValidationError

from app.core.config import get_openai_api_key

from .audit import record_fallback as _record_fallback
from .audit import record_llm_call as _record_llm_call
from .models import FallbackReason, PhrasingOutput, PhrasingRequest
from .provider import parse_json_output as _parse_json_output
from .provider import request_llm_json as _request_llm_json
from .templates import desired_tone_for_confidence, get_template_phrasing


LOGGER = logging.getLogger("app.phrasing")


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
) -> sqlite3.Row:
    api_key = get_openai_api_key()
    if not api_key:
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.missing_key.value)
        return _get_nudge(conn, nudge_id)

    request_model = PhrasingRequest(
        nudge_type=nudge_type,
        member_goal=member_goal,
        matched_reason=matched_reason,
        explanation_basis=explanation_basis,
        tone=desired_tone_for_confidence(confidence),
    )

    started = time.perf_counter()
    try:
        raw_content = _request_llm_json(request_model, api_key)
        latency_ms = int((time.perf_counter() - started) * 1000)
        parsed = _parse_json_output(raw_content)
        phrasing = PhrasingOutput.model_validate(parsed)
    except httpx.TimeoutException:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.timeout.value)
        return _get_nudge(conn, nudge_id)
    except httpx.HTTPError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.provider_error.value)
        return _get_nudge(conn, nudge_id)
    except json.JSONDecodeError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.invalid_json.value)
        return _get_nudge(conn, nudge_id)
    except ValidationError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.validation_failure.value)
        return _get_nudge(conn, nudge_id)
    except ValueError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.invalid_json.value)
        return _get_nudge(conn, nudge_id)

    conn.execute(
        "UPDATE nudges SET content = ?, explanation = ?, phrasing_source = 'llm' WHERE id = ?",
        (phrasing.content, phrasing.explanation, nudge_id),
    )
    _record_llm_call(conn, nudge_id, member_id, nudge_type, success=True, latency_ms=latency_ms, phrasing_source="llm")
    return _get_nudge(conn, nudge_id)


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
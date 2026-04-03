"""Optional LLM phrasing with deterministic fallback and validation."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from enum import Enum

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.audit import log_structured_event, record_audit_event
from app.config import OPENAI_MODEL, PHRASING_TIMEOUT_SECONDS, get_openai_api_key


PROVIDER_NAME = "openai"
LOGGER = logging.getLogger("app.phrasing")
BLOCKED_TERMS = (
    "diagnose",
    "diagnosis",
    "medication",
    "prescription",
    "dose",
    "treatment plan",
)

SYSTEM_PROMPT = (
    "You are rewriting a short wellness nudge for clarity and empathy. "
    "Do not diagnose, prescribe, mention medication, or imply treatment. "
    "Keep the recommendation practical, non-judgmental, and comfortably under the requested length. "
    "The explanation must state why the member is seeing the nudge, not describe your writing choices. "
    "Use one short sentence for content and one short sentence for explanation. "
    "Return only JSON with content and explanation."
)

TEMPLATE_PHRASING: dict[str, dict[str, str]] = {
    "meal_guidance": {
        "content": "Try a lighter, lower-carb dinner to balance today's earlier meal.",
        "explanation": "You logged a higher-carb meal today and your goal is low carb.",
    },
    "weight_check_in": {
        "content": "Take a quick weight check-in when you have a minute.",
        "explanation": "You have not logged weight in the last few days.",
    },
    "support_risk": {
        "content": "A coach follow-up is a better next step than another automated nudge.",
        "explanation": "Recent signals suggest you may benefit from direct support.",
    },
}


class FallbackReason(str, Enum):
    missing_key = "missing_key"
    timeout = "timeout"
    provider_error = "provider_error"
    invalid_json = "invalid_json"
    validation_failure = "validation_failure"


class PhrasingRequest(BaseModel):
    nudge_type: str
    member_goal: str
    matched_reason: str
    explanation_basis: str
    tone: str = "clear and empathetic"
    max_content_chars: int = 120
    max_explanation_chars: int = 120


class PhrasingOutput(BaseModel):
    content: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_safe_copy(self) -> PhrasingOutput:
        self.content = self.content.strip()
        self.explanation = self.explanation.strip()
        if not self.content or not self.explanation:
            raise ValueError("content and explanation must be non-empty")

        lower_text = f"{self.content} {self.explanation}".lower()
        if any(term in lower_text for term in BLOCKED_TERMS):
            raise ValueError("blocked safety term present")
        return self


def get_template_phrasing(nudge_type: str) -> dict[str, str]:
    return TEMPLATE_PHRASING[nudge_type].copy()


def desired_tone_for_confidence(confidence: float) -> str:
    if confidence >= 0.75:
        return "clear, supportive, and practical"
    return "gentle, supportive, and practical"


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
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.missing_key)
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
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.timeout)
        return _get_nudge(conn, nudge_id)
    except httpx.HTTPError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.provider_error)
        return _get_nudge(conn, nudge_id)
    except json.JSONDecodeError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.invalid_json)
        return _get_nudge(conn, nudge_id)
    except ValidationError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.validation_failure)
        return _get_nudge(conn, nudge_id)
    except ValueError:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_llm_call(conn, nudge_id, member_id, nudge_type, success=False, latency_ms=latency_ms)
        _record_fallback(conn, nudge_id, member_id, nudge_type, FallbackReason.validation_failure)
        return _get_nudge(conn, nudge_id)

    conn.execute(
        "UPDATE nudges SET content = ?, explanation = ?, phrasing_source = 'llm' WHERE id = ?",
        (phrasing.content, phrasing.explanation, nudge_id),
    )
    _record_llm_call(conn, nudge_id, member_id, nudge_type, success=True, latency_ms=latency_ms, phrasing_source="llm")
    return _get_nudge(conn, nudge_id)


def _request_llm_json(request_model: PhrasingRequest, api_key: str) -> str:
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "nudge_type": request_model.nudge_type,
                        "member_goal": request_model.member_goal,
                        "matched_reason": request_model.matched_reason,
                        "explanation_basis": request_model.explanation_basis,
                        "tone": request_model.tone,
                        "max_content_chars": request_model.max_content_chars,
                        "max_explanation_chars": request_model.max_explanation_chars,
                        "instructions": [
                            "Content should be a direct member-facing recommendation.",
                            "Explanation should say why the member is seeing the nudge.",
                            "Do not mention tone, clarity, writing, or character limits.",
                            "Keep both fields concise and well below the validator maximum.",
                        ],
                    }
                ),
            },
        ],
    }

    with httpx.Client(timeout=PHRASING_TIMEOUT_SECONDS) as client:
        response = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    return _extract_message_content(body)


def _extract_message_content(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ValueError("provider returned no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return _strip_code_fences(content)

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text_value = item.get("text") or item.get("content") or ""
                if text_value:
                    text_parts.append(str(text_value))
        if text_parts:
            return _strip_code_fences("".join(text_parts))

    raise ValueError("provider returned unsupported content")


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _parse_json_output(raw_content: str) -> dict:
    parsed = json.loads(raw_content)
    if not isinstance(parsed, dict):
        raise ValueError("provider JSON must be an object")
    return parsed


def _record_llm_call(
    conn: sqlite3.Connection,
    nudge_id: str,
    member_id: str,
    nudge_type: str,
    *,
    success: bool,
    latency_ms: int,
    phrasing_source: str | None = None,
) -> None:
    payload = {
        "member_id": member_id,
        "nudge_type": nudge_type,
        "provider": PROVIDER_NAME,
        "success": success,
        "latency_ms": latency_ms,
    }
    if phrasing_source is not None:
        payload["phrasing_source"] = phrasing_source
    record_audit_event(conn, "llm_call", "nudge", nudge_id, payload)
    log_structured_event(logging.INFO if success else logging.WARNING, "llm_call", {**payload, "nudge_id": nudge_id})


def _record_fallback(
    conn: sqlite3.Connection,
    nudge_id: str,
    member_id: str,
    nudge_type: str,
    reason: FallbackReason,
) -> None:
    payload = {
        "member_id": member_id,
        "nudge_type": nudge_type,
        "fallback_reason": reason.value,
    }
    record_audit_event(conn, "llm_fallback", "nudge", nudge_id, payload)
    log_structured_event(logging.WARNING, "llm_fallback", {**payload, "nudge_id": nudge_id})


def _get_nudge(conn: sqlite3.Connection, nudge_id: str) -> sqlite3.Row:
    return conn.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()
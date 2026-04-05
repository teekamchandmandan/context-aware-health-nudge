import json

import httpx

from app.core.config import OPENAI_MODEL, PHRASING_TIMEOUT_SECONDS

from .models import PhrasingRequest

SYSTEM_PROMPT = (
    "You rewrite an already approved wellness nudge using only the structured facts you are given. "
    "Do not change the underlying decision, add new facts, add new risks, or add medical framing. "
    "Do not diagnose, prescribe, mention medication, recommend clinicians, or imply treatment. "
    "Return exactly one JSON object with only content and explanation. "
    "Content must be one short member-facing sentence with a practical next step. "
    "Explanation must be one short sentence explaining why the member is seeing the nudge using only the supplied reason. "
    "Keep both fields concrete, non-judgmental, and within the requested character limits. "
    "Do not mention tone, writing style, JSON, validation, or character counts."
)


def request_llm_json(request_model: PhrasingRequest, api_key: str) -> tuple[str, str]:
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.1,
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
                            "Use only the structured request fields. Do not invent extra facts, meal details, numbers, or time windows.",
                            "Content should be a direct member-facing recommendation with one practical next step.",
                            "Explanation should restate why the member is seeing the nudge and stay grounded in explanation_basis.",
                            "If the tone is gentle, soften the wording without becoming vague; if the tone is clear, be direct but still kind.",
                            "Avoid exclamation points, shame, warnings, absolutes, and any mention of tone, writing, or character limits.",
                            "Keep each field to one sentence and at or below the requested character limits.",
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

    return extract_message_content(body), extract_model_name(body)


def extract_message_content(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ValueError("provider returned no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return strip_code_fences(content)

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                text_value = item.get("text") or item.get("content") or ""
                if text_value:
                    text_parts.append(str(text_value))
        if text_parts:
            return strip_code_fences("".join(text_parts))

    raise ValueError("provider returned unsupported content")


def extract_model_name(body: dict) -> str:
    model_name = body.get("model")
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    return OPENAI_MODEL


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_json_output(raw_content: str) -> dict:
    parsed = json.loads(raw_content)
    if not isinstance(parsed, dict):
        raise ValueError("provider JSON must be an object")
    return parsed
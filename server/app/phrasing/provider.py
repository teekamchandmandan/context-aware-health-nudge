import json

import httpx

from app.core.config import OPENAI_MODEL, PHRASING_TIMEOUT_SECONDS

from .models import PhrasingRequest

SYSTEM_PROMPT = (
    "You are rewriting a short wellness nudge for clarity and empathy. "
    "Do not diagnose, prescribe, mention medication, or imply treatment. "
    "Keep the recommendation practical, non-judgmental, and comfortably under the requested length. "
    "The explanation must state why the member is seeing the nudge, not describe your writing choices. "
    "Use one short sentence for content and one short sentence for explanation. "
    "Return only JSON with content and explanation."
)


def request_llm_json(request_model: PhrasingRequest, api_key: str) -> str:
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

    return extract_message_content(body)


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
import base64
import json

import httpx

from app.core.config import MEAL_ANALYSIS_TIMEOUT_SECONDS, OPENAI_MODEL

SYSTEM_PROMPT = (
    "You extract structured meal details from a member's meal photo without any written description. "
    "Return only JSON with meal_type, carbs_g, protein_g, analysis_summary, analysis_confidence, analysis_status, and analysis_source. "
    "Use short, plain language. If you are uncertain, omit fields instead of inventing them. "
    "This output may be saved directly on the meal log, so keep estimates cautious and clearly marked as approximate."
)


def request_meal_analysis_json(
    api_key: str,
    *,
    photo_bytes: bytes | None,
    photo_content_type: str | None,
) -> str:
    payload = {
        "model": OPENAI_MODEL,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_content(
                    photo_bytes=photo_bytes,
                    photo_content_type=photo_content_type,
                ),
            },
        ],
    }

    with httpx.Client(timeout=MEAL_ANALYSIS_TIMEOUT_SECONDS) as client:
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


def build_user_content(
    *,
    photo_bytes: bytes | None,
    photo_content_type: str | None,
) -> list[dict[str, object]]:
    if photo_bytes is None or not photo_content_type or not photo_content_type.startswith("image/"):
        raise ValueError("meal analysis requires an image")

    content: list[dict[str, object]] = [
        {
            "type": "text",
            "text": json.dumps(
                {
                    "input": "meal_photo_only",
                    "instructions": [
                        "Use only details visible in the image.",
                        "Do not rely on any member-written description because none is provided.",
                        "Infer meal_type, carbs_g, and protein_g only when reasonably supported.",
                        "Use analysis_status='estimated' when you include nutrition estimates.",
                        "Use analysis_status='partial' when you are unsure or only have limited structure.",
                        "Set analysis_source='llm'.",
                        "Keep analysis_summary under 160 characters and mention that values may be approximate.",
                    ],
                }
            ),
        }
    ]
    encoded = base64.b64encode(photo_bytes).decode("ascii")
    content.append(
        {
            "type": "image_url",
            "image_url": {"url": f"data:{photo_content_type};base64,{encoded}"},
        }
    )
    return content


def extract_message_content(body: dict) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ValueError("provider returned no choices")

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        return strip_code_fences(content)

    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        if text_parts:
            return strip_code_fences("".join(text_parts))

    raise ValueError("provider returned no text content")


def strip_code_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped
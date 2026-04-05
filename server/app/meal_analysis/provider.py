import base64
import json

import httpx

from app.core.config import MEAL_ANALYSIS_TIMEOUT_SECONDS, OPENAI_MODEL

SYSTEM_PROMPT = (
    "You classify a meal photo using a cautious structured output. "
    "Use only visible evidence from the image and do not rely on hidden ingredients, outside member context, or any written description. "
    "Return exactly one JSON object with these keys: meal_profile and visible_food_summary. "
    "meal_profile must be one of higher_carb, higher_protein, balanced, or unclear. "
    "Use unclear when the image is blurry, cropped, occluded, mostly packaging, or does not support a confident classification. "
    "visible_food_summary must be either null or one short factual sentence under 160 characters describing only visible food items. "
    "Do not give advice, warnings, diagnoses, treatment suggestions, or coaching."
)


def request_meal_analysis_json(
    api_key: str,
    *,
    photo_bytes: bytes | None,
    photo_content_type: str | None,
) -> tuple[str, str]:
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

    return extract_message_content(body), extract_model_name(body)


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
                        "Return meal_profile='unclear' when the image does not support a confident classification.",
                        "Keep visible_food_summary factual and limited to visible food items only.",
                    ],
                }
            ),
        }
    ]
    encoded = base64.b64encode(photo_bytes).decode("ascii")
    content.append(
        {
            "type": "image_url",
            "image_url": {"url": f"data:{photo_content_type};base64,{encoded}", "detail": "auto"},
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


def extract_model_name(body: dict) -> str:
    model_name = body.get("model")
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    return OPENAI_MODEL


def parse_json_output(raw_content: str) -> dict:
    parsed = json.loads(raw_content)
    if not isinstance(parsed, dict):
        raise ValueError("provider JSON must be an object")
    return parsed
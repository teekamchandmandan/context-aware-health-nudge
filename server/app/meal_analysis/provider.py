import base64
import json

from app.core.openai_chat import extract_message_content as _extract_message_content
from app.core.openai_chat import extract_model_name as _extract_model_name
from app.core.openai_chat import parse_json_output as _parse_json_output
from app.core.openai_chat import request_chat_completion as _request_chat_completion
from app.core.openai_chat import strip_code_fences as _strip_code_fences
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

    body = _request_chat_completion(
        api_key=api_key,
        payload=payload,
        timeout_seconds=MEAL_ANALYSIS_TIMEOUT_SECONDS,
    )

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
    return _extract_message_content(
        body,
        text_item_types={"text"},
        text_value_keys=("text",),
        error_message="provider returned no text content",
    )


def strip_code_fences(content: str) -> str:
    return _strip_code_fences(content)


def extract_model_name(body: dict) -> str:
    return _extract_model_name(body, OPENAI_MODEL)


def parse_json_output(raw_content: str) -> dict:
    return _parse_json_output(raw_content)
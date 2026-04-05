from __future__ import annotations

import json
from collections.abc import Iterable

import httpx


CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def request_chat_completion(
    *,
    api_key: str,
    payload: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(
            CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    if not isinstance(body, dict):
        raise ValueError("provider response must be an object")

    return body


def extract_message_content(
    body: dict[str, object],
    *,
    text_item_types: set[str],
    text_value_keys: tuple[str, ...],
    error_message: str,
) -> str:
    choices = body.get("choices") or []
    if not isinstance(choices, list) or not choices:
        raise ValueError("provider returned no choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError(error_message)

    message = first_choice.get("message") or {}
    if not isinstance(message, dict):
        raise ValueError(error_message)

    content = message.get("content")

    if isinstance(content, str):
        return strip_code_fences(content)

    if isinstance(content, list):
        text_parts = _extract_text_parts(
            content,
            text_item_types=text_item_types,
            text_value_keys=text_value_keys,
        )
        if text_parts:
            return strip_code_fences("".join(text_parts))

    raise ValueError(error_message)


def extract_model_name(body: dict[str, object], default_model_name: str) -> str:
    model_name = body.get("model")
    if isinstance(model_name, str) and model_name.strip():
        return model_name.strip()
    return default_model_name


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def parse_json_output(raw_content: str) -> dict[str, object]:
    parsed = json.loads(raw_content)
    if not isinstance(parsed, dict):
        raise ValueError("provider JSON must be an object")
    return parsed


def _extract_text_parts(
    content: Iterable[object],
    *,
    text_item_types: set[str],
    text_value_keys: tuple[str, ...],
) -> list[str]:
    text_parts: list[str] = []

    for item in content:
        if not isinstance(item, dict) or item.get("type") not in text_item_types:
            continue

        for key in text_value_keys:
            text_value = item.get(key)
            if text_value:
                text_parts.append(str(text_value))
                break

    return text_parts
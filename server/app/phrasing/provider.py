import json

from app.core.openai_chat import extract_message_content as _extract_message_content
from app.core.openai_chat import extract_model_name as _extract_model_name
from app.core.openai_chat import parse_json_output as _parse_json_output
from app.core.openai_chat import request_chat_completion as _request_chat_completion
from app.core.openai_chat import strip_code_fences as _strip_code_fences
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

    body = _request_chat_completion(
        api_key=api_key,
        payload=payload,
        timeout_seconds=PHRASING_TIMEOUT_SECONDS,
    )

    return extract_message_content(body), extract_model_name(body)


def extract_message_content(body: dict) -> str:
    return _extract_message_content(
        body,
        text_item_types={"text", "output_text"},
        text_value_keys=("text", "content"),
        error_message="provider returned unsupported content",
    )


def extract_model_name(body: dict) -> str:
    return _extract_model_name(body, OPENAI_MODEL)


def strip_code_fences(text: str) -> str:
    return _strip_code_fences(text)


def parse_json_output(raw_content: str) -> dict:
    return _parse_json_output(raw_content)
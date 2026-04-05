import json
from unittest.mock import patch

import httpx
import pytest

from app.meal_analysis import create_meal_draft
from app.meal_analysis.provider import request_meal_analysis_json as request_meal_analysis_provider_json
from app.models.meals import MealDraftResponse
from app.phrasing.models import PhrasingRequest
from app.phrasing.provider import request_llm_json as request_phrasing_provider_json

from .api_support import (
    OPENAI_MODEL,
    assert_meal_analysis_audit,
    post_meal_log_response,
)


def test_meal_analysis_photo_only_fallback():
    analysis = create_meal_draft(
        photo_bytes=b"fake-image-bytes",
        photo_content_type="image/jpeg",
    )

    assert analysis.meal_profile == "unclear"
    assert analysis.visible_food_summary is None


def test_meal_analysis_provider_omits_temperature_for_gpt5_models():
    with patch(
        "app.meal_analysis.provider._request_chat_completion",
        return_value={
            "choices": [
                {
                    "message": {
                        "content": '{"meal_profile":"balanced","visible_food_summary":null}',
                    }
                }
            ],
            "model": "gpt-5-mini",
        },
    ) as mocked_request:
        raw_content, model_name = request_meal_analysis_provider_json(
            "test-key",
            photo_bytes=b"fake-image-bytes",
            photo_content_type="image/jpeg",
        )

    assert model_name == "gpt-5-mini"
    assert "balanced" in raw_content
    payload = mocked_request.call_args.kwargs["payload"]
    assert "temperature" not in payload


def test_phrasing_provider_omits_temperature_for_gpt5_models():
    with patch(
        "app.phrasing.provider._request_chat_completion",
        return_value={
            "choices": [
                {
                    "message": {
                        "content": '{"content":"Try a lighter dinner tonight.","explanation":"You logged a higher-carb meal today."}',
                    }
                }
            ],
            "model": "gpt-5-mini",
        },
    ) as mocked_request:
        raw_content, model_name = request_phrasing_provider_json(
            PhrasingRequest(
                nudge_type="meal_guidance",
                member_goal="low_carb",
                matched_reason="meal_goal_mismatch",
                explanation_basis="A recent meal exceeded the member's low-carb target.",
            ),
            "test-key",
        )

    assert model_name == "gpt-5-mini"
    assert "lighter dinner" in raw_content
    payload = mocked_request.call_args.kwargs["payload"]
    assert "temperature" not in payload


def test_meal_analysis_llm_audit_records_model_name(api_client):
    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        return_value=(
            '{"meal_profile":"higher_carb","visible_food_summary":"The photo appears to show a pasta dish with bread."}',
            "gpt-5-mini-test-meal-audit",
        ),
    ):
        response = post_meal_log_response(api_client)

    assert response.status_code == 200
    assert_meal_analysis_audit(
        "llm_call",
        expected_model_name="gpt-5-mini-test-meal-audit",
        expected_success=True,
    )


def test_meal_analysis_missing_key_audit_records_model_name(api_client):
    response = post_meal_log_response(api_client)
    assert response.status_code == 200
    assert_meal_analysis_audit(
        "llm_fallback",
        expected_model_name=OPENAI_MODEL,
        expected_reason="missing_key",
    )


@pytest.mark.parametrize(
    ("patch_kwargs", "expected_reason", "expected_model_name"),
    [
        ({"side_effect": httpx.TimeoutException("timed out")}, "timeout", OPENAI_MODEL),
        ({"side_effect": httpx.HTTPError("provider error")}, "provider_error", OPENAI_MODEL),
        ({"return_value": ("not-json", "gpt-5-mini-test-meal-invalid-json")}, "invalid_json", "gpt-5-mini-test-meal-invalid-json"),
        (
            {
                "return_value": (
                    '{"meal_profile":"breakfasty","visible_food_summary":"The photo appears to show a plated meal."}',
                    "gpt-5-mini-test-meal-validation",
                )
            },
            "validation_failure",
            "gpt-5-mini-test-meal-validation",
        ),
    ],
)
def test_meal_analysis_provider_failures_record_audit(api_client, patch_kwargs, expected_reason, expected_model_name):
    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"):
        with patch("app.meal_analysis._request_meal_analysis_json", **patch_kwargs):
            response = post_meal_log_response(api_client)

    assert response.status_code == 200
    assert_meal_analysis_audit(
        "llm_fallback",
        expected_model_name=expected_model_name,
        expected_reason=expected_reason,
    )


def test_meal_log_one_step_rejects_description_field(api_client):
    with patch(
        "app.main.create_meal_draft",
        return_value=MealDraftResponse(
            meal_profile="higher_carb",
            visible_food_summary="The photo appears to show a pasta dish with bread.",
        ),
    ) as mocked_create_meal_draft:
        response = api_client.post(
            "/api/members/member_meal_01/meal-logs",
            data={"description": "Pasta carbonara with garlic bread"},
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert response.status_code == 422
    assert "unexpected meal upload fields" in json.dumps(response.json())
    assert mocked_create_meal_draft.call_count == 0


def test_meal_log_one_step_photo_only(api_client):
    with patch(
        "app.main.create_meal_draft",
        return_value=MealDraftResponse(
            meal_profile="higher_protein",
            visible_food_summary="The photo appears to show grilled chicken and vegetables.",
        ),
    ):
        response = api_client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    assert response.status_code == 200
    data = response.json()
    assert "photo_attached" not in data["payload"]
    assert "meal_input_method" not in data["payload"]
    assert data["payload"]["meal_profile"] == "higher_protein"
    assert data["payload"]["visible_food_summary"] == "The photo appears to show grilled chicken and vegetables."


def test_meal_log_rejects_unsupported_image_format(api_client):
    with patch("app.main.create_meal_draft") as mocked_create_meal_draft:
        response = api_client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.avif", b"fake-image-bytes", "image/avif")},
        )

    assert response.status_code == 422
    assert "webp" in json.dumps(response.json()).lower()
    assert mocked_create_meal_draft.call_count == 0


def test_meal_log_requires_photo(api_client):
    response = api_client.post("/api/members/member_meal_01/meal-logs")
    assert response.status_code == 422
    assert "meal photo" in json.dumps(response.json())


def test_meal_log_rejects_non_image_upload(api_client):
    response = api_client.post(
        "/api/members/member_meal_01/meal-logs",
        files={"photo": ("meal.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 422
    assert "image" in json.dumps(response.json())

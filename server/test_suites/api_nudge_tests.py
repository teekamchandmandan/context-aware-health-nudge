from unittest.mock import patch

import httpx

def test_member_nudge_active(api_client):
    response = api_client.get("/api/members/member_meal_01/nudge")
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "active"
    assert data["member"]["id"] == "member_meal_01"
    assert data["member"]["name"] == "Alice Chen"
    assert data["nudge"] is not None

    nudge = data["nudge"]
    assert nudge["nudge_type"] == "meal_guidance"
    assert nudge["content"]
    assert nudge["confidence"] == 0.86
    assert nudge["status"] == "active"
    assert nudge["phrasing_source"] == "template"
    assert "created_at" in nudge


def test_member_nudge_idempotent(api_client):
    first_response = api_client.get("/api/members/member_meal_01/nudge")
    second_response = api_client.get("/api/members/member_meal_01/nudge")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["nudge"]["id"] == second_response.json()["nudge"]["id"]


def test_member_nudge_llm_success(api_client):
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=(
            '{"content":"Try a lighter dinner tonight to stay aligned with your goal.","explanation":"You logged a higher-carb meal today and your goal is low carb."}',
            "gpt-5-mini-test-api",
        ),
    ):
        response = api_client.get("/api/members/member_meal_01/nudge")

    assert response.status_code == 200
    data = response.json()
    assert data["nudge"]["phrasing_source"] == "llm"
    assert "tonight" in data["nudge"]["content"]


def test_member_nudge_llm_timeout_fallback(api_client):
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        response = api_client.get("/api/members/member_meal_01/nudge")

    assert response.status_code == 200
    data = response.json()
    assert data["nudge"]["phrasing_source"] == "template"
    assert data["nudge"]["content"] == "Try a lighter, lower-carb dinner to balance today's earlier meal."


def test_member_nudge_llm_idempotent_reads(api_client):
    calls = {"count": 0}

    def fake_request(*_args, **_kwargs):
        calls["count"] += 1
        return (
            '{"content":"Try a lighter dinner tonight to stay aligned.","explanation":"You logged a higher-carb meal today and your goal is low carb."}',
            "gpt-5-mini-test-idempotent-api",
        )

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=fake_request,
    ):
        first_response = api_client.get("/api/members/member_meal_01/nudge")
        second_response = api_client.get("/api/members/member_meal_01/nudge")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert calls["count"] == 1
    assert first_response.json()["nudge"]["id"] == second_response.json()["nudge"]["id"]


def test_member_nudge_weight(api_client):
    response = api_client.get("/api/members/member_weight_01/nudge")
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "active"
    assert data["nudge"]["nudge_type"] == "weight_check_in"
    assert data["nudge"]["content"]


def test_member_nudge_no_nudge(api_client):
    response = api_client.get("/api/members/member_catchup_01/nudge")
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "no_nudge"
    assert data["member"]["id"] == "member_catchup_01"
    assert data["member"]["name"] == "Diego Rivera"
    assert data.get("nudge") is None


def test_member_nudge_escalated(api_client):
    response = api_client.get("/api/members/member_support_01/nudge")
    assert response.status_code == 200

    data = response.json()
    assert data["state"] == "escalated"
    assert data.get("nudge") is None


def test_member_nudge_404(api_client):
    response = api_client.get("/api/members/nonexistent/nudge")
    assert response.status_code == 404

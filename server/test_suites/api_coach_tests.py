from unittest.mock import patch

def test_coach_nudges(api_client):
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=(
            '{"content":"Try a lighter dinner tonight to stay aligned with your goal.","explanation":"You logged a higher-carb meal today and your goal is low carb."}',
            "gpt-5-mini-test-coach",
        ),
    ):
        api_client.get("/api/members/member_meal_01/nudge")

    api_client.get("/api/members/member_weight_01/nudge")

    response = api_client.get("/api/coach/nudges")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["items"], list)
    assert data["limit"] == 20
    assert data["count"] == len(data["items"])
    assert data["count"] > 0

    if data["items"]:
        item = data["items"][0]
        for field in [
            "nudge_id",
            "member_id",
            "member_name",
            "nudge_type",
            "visible_food_summary",
            "explanation",
            "matched_reason",
            "confidence",
            "status",
            "phrasing_source",
            "created_at",
        ]:
            assert field in item
        assert isinstance(item["phrasing_source"], str)
        assert item["phrasing_source"]

    meal_item = next((item for item in data["items"] if item["member_id"] == "member_meal_01"), None)
    assert meal_item is not None
    assert meal_item["phrasing_source"] == "llm"
    assert meal_item["visible_food_summary"] == "The photo appears to show a pasta dish with bread."


def test_coach_nudges_limit(api_client):
    response = api_client.get("/api/coach/nudges?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 2
    assert data["count"] <= 2

    invalid_limit_response = api_client.get("/api/coach/nudges?limit=100")
    assert invalid_limit_response.status_code == 422


def test_coach_escalations(api_client):
    api_client.get("/api/members/member_support_01/nudge")

    response = api_client.get("/api/coach/escalations")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["items"], list)
    assert data["count"] >= 1

    if data["items"]:
        item = data["items"][0]
        for field in ["escalation_id", "member_id", "member_name", "reason", "source", "status", "created_at"]:
            assert field in item
        assert item["status"] == "open"


def test_coach_escalations_from_ask_for_help(api_client):
    nudge_response = api_client.get("/api/members/member_meal_01/nudge")
    nudge_id = nudge_response.json()["nudge"]["id"]
    api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "ask_for_help"})

    response = api_client.get("/api/coach/escalations")
    data = response.json()
    member_action_escalations = [item for item in data["items"] if item["source"] == "member_action"]
    assert member_action_escalations
    assert member_action_escalations[0]["member_id"] == "member_meal_01"

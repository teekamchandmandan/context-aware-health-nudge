import json

def test_signal_weight_logged(api_client):
    response = api_client.post(
        "/api/members/member_weight_01/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 180.5}},
    )
    assert response.status_code == 200
    assert response.json()["payload"]["weight_lb"] == 180.5


def test_signal_re_evaluates_existing_active_nudge(api_client):
    initial_response = api_client.get("/api/members/member_weight_01/nudge")
    assert initial_response.status_code == 200
    assert initial_response.json()["state"] == "active"

    signal_response = api_client.post(
        "/api/members/member_weight_01/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 180.5}},
    )
    assert signal_response.status_code == 200

    follow_up_response = api_client.get("/api/members/member_weight_01/nudge")
    assert follow_up_response.status_code == 200
    assert follow_up_response.json()["state"] == "no_nudge"


def test_signal_mood_logged(api_client):
    response = api_client.post(
        "/api/members/member_support_01/signals",
        json={"signal_type": "mood_logged", "payload": {"mood": "high"}},
    )
    assert response.status_code == 200
    assert response.json()["payload"]["mood"] == "high"


def test_signal_422_invalid_values(api_client):
    mood_response = api_client.post(
        "/api/members/member_support_01/signals",
        json={"signal_type": "mood_logged", "payload": {"mood": "good"}},
    )
    assert mood_response.status_code == 422
    assert "low, neutral, high" in json.dumps(mood_response.json())

    weight_response = api_client.post(
        "/api/members/member_weight_01/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 0}},
    )
    assert weight_response.status_code == 422

    sleep_response = api_client.post(
        "/api/members/member_meal_01/signals",
        json={"signal_type": "sleep_logged", "payload": {"sleep_hours": 25}},
    )
    assert sleep_response.status_code == 422


def test_signal_sleep_logged(api_client):
    response = api_client.post(
        "/api/members/member_meal_01/signals",
        json={"signal_type": "sleep_logged", "payload": {"sleep_hours": 7.5}},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["signal_type"] == "sleep_logged"
    assert data["payload"]["sleep_hours"] == 7.5


def test_signal_422_missing_required(api_client):
    weight_response = api_client.post(
        "/api/members/member_weight_01/signals",
        json={"signal_type": "weight_logged", "payload": {}},
    )
    assert weight_response.status_code == 422

    mood_response = api_client.post(
        "/api/members/member_support_01/signals",
        json={"signal_type": "mood_logged", "payload": {}},
    )
    assert mood_response.status_code == 422

    sleep_response = api_client.post(
        "/api/members/member_meal_01/signals",
        json={"signal_type": "sleep_logged", "payload": {}},
    )
    assert sleep_response.status_code == 422


def test_signal_422_unknown_type(api_client):
    response = api_client.post(
        "/api/members/member_meal_01/signals",
        json={"signal_type": "unknown_type", "payload": {"foo": "bar"}},
    )
    assert response.status_code == 422


def test_signal_422_cross_signal_extra_fields(api_client):
    """Sending fields belonging to other signal types should be rejected with 422."""
    # weight_logged with mood
    r1 = api_client.post(
        "/api/members/member_weight_01/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 180.0, "mood": "high"}},
    )
    assert r1.status_code == 422

    # weight_logged with sleep_hours
    r2 = api_client.post(
        "/api/members/member_weight_01/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 180.0, "sleep_hours": 7}},
    )
    assert r2.status_code == 422

    # mood_logged with weight_lb
    r3 = api_client.post(
        "/api/members/member_support_01/signals",
        json={"signal_type": "mood_logged", "payload": {"mood": "high", "weight_lb": 180.0}},
    )
    assert r3.status_code == 422

    # mood_logged with sleep_hours
    r4 = api_client.post(
        "/api/members/member_support_01/signals",
        json={"signal_type": "mood_logged", "payload": {"mood": "high", "sleep_hours": 7}},
    )
    assert r4.status_code == 422

    # sleep_logged with weight_lb
    r5 = api_client.post(
        "/api/members/member_meal_01/signals",
        json={"signal_type": "sleep_logged", "payload": {"sleep_hours": 7.5, "weight_lb": 180.0}},
    )
    assert r5.status_code == 422

    # sleep_logged with mood
    r6 = api_client.post(
        "/api/members/member_meal_01/signals",
        json={"signal_type": "sleep_logged", "payload": {"sleep_hours": 7.5, "mood": "low"}},
    )
    assert r6.status_code == 422


def test_signal_404_unknown_member(api_client):
    response = api_client.post(
        "/api/members/nonexistent/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 175.0}},
    )
    assert response.status_code == 404


def test_signals_latest(api_client):
    member_id = "member_meal_01"

    initial_response = api_client.get(f"/api/members/{member_id}/signals/latest")
    assert initial_response.status_code == 200
    assert initial_response.json() == {}

    api_client.post(
        f"/api/members/{member_id}/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 180.5}},
    )
    first_weight_response = api_client.get(f"/api/members/{member_id}/signals/latest")
    data = first_weight_response.json()
    assert first_weight_response.status_code == 200
    assert "weight_logged" in data
    assert "sleep_logged" not in data
    assert "mood_logged" not in data
    assert data["weight_logged"]["payload"]["weight_lb"] == 180.5
    assert "logged_at" in data["weight_logged"]

    api_client.post(
        f"/api/members/{member_id}/signals",
        json={"signal_type": "weight_logged", "payload": {"weight_lb": 185.0}},
    )
    latest_weight_response = api_client.get(f"/api/members/{member_id}/signals/latest")
    assert latest_weight_response.json()["weight_logged"]["payload"]["weight_lb"] == 185.0

    api_client.post(
        f"/api/members/{member_id}/signals",
        json={"signal_type": "sleep_logged", "payload": {"sleep_hours": 7.5}},
    )
    api_client.post(
        f"/api/members/{member_id}/signals",
        json={"signal_type": "mood_logged", "payload": {"mood": "high"}},
    )
    summary_response = api_client.get(f"/api/members/{member_id}/signals/latest")
    summary = summary_response.json()
    assert all(key in summary for key in ("weight_logged", "sleep_logged", "mood_logged"))
    assert summary["sleep_logged"]["payload"]["sleep_hours"] == 7.5
    assert summary["mood_logged"]["payload"]["mood"] == "high"

    missing_member_response = api_client.get("/api/members/nonexistent/signals/latest")
    assert missing_member_response.status_code == 404

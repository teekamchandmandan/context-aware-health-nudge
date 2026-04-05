from .api_support import latest_audit_payload


def test_action_act_now(api_client):
    nudge_response = api_client.get("/api/members/member_meal_01/nudge")
    nudge_id = nudge_response.json()["nudge"]["id"]

    response = api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "act_now"})
    assert response.status_code == 200

    data = response.json()
    assert data["nudge_id"] == nudge_id
    assert data["action_type"] == "act_now"
    assert data["nudge_status"] == "acted"
    assert "recorded_at" in data

    audit_payload = latest_audit_payload("user_action", entity_id=nudge_id)
    assert audit_payload is not None
    assert audit_payload["action_type"] == "act_now"
    assert audit_payload["previous_status"] == "active"
    assert audit_payload["new_status"] == "acted"


def test_action_dismiss(api_client):
    nudge_response = api_client.get("/api/members/member_meal_01/nudge")
    nudge_id = nudge_response.json()["nudge"]["id"]

    response = api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "dismiss"})
    assert response.status_code == 200
    assert response.json()["nudge_status"] == "dismissed"

    audit_payload = latest_audit_payload("user_action", entity_id=nudge_id)
    assert audit_payload is not None
    assert audit_payload["action_type"] == "dismiss"
    assert audit_payload["new_status"] == "dismissed"


def test_action_ask_for_help(api_client):
    nudge_response = api_client.get("/api/members/member_meal_01/nudge")
    nudge_id = nudge_response.json()["nudge"]["id"]

    response = api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "ask_for_help"})
    assert response.status_code == 200
    data = response.json()
    assert data["nudge_status"] == "escalated"

    coach_response = api_client.get("/api/coach/escalations")
    esc_items = coach_response.json()["items"]
    member_esc = [item for item in esc_items if item["source"] == "member_action"]
    assert member_esc

    action_audit = latest_audit_payload("user_action", entity_id=nudge_id)
    assert action_audit is not None
    assert action_audit["action_type"] == "ask_for_help"
    assert action_audit["new_status"] == "escalated"

    escalation_audit = latest_audit_payload("escalation_created")
    assert escalation_audit is not None
    assert escalation_audit["source"] == "member_action"
    assert escalation_audit["nudge_id"] == nudge_id


def test_action_409_terminal(api_client):
    nudge_response = api_client.get("/api/members/member_meal_01/nudge")
    nudge_id = nudge_response.json()["nudge"]["id"]

    api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "dismiss"})
    response = api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "act_now"})
    assert response.status_code == 409


def test_action_404_unknown(api_client):
    response = api_client.post("/api/nudges/nonexistent/action", json={"action_type": "act_now"})
    assert response.status_code == 404


def test_action_422_invalid_type(api_client):
    nudge_response = api_client.get("/api/members/member_meal_01/nudge")
    nudge_id = nudge_response.json()["nudge"]["id"]

    response = api_client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "invalid"})
    assert response.status_code == 422

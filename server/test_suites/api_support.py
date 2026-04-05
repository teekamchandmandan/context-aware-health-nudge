import json

from app.core.config import OPENAI_MODEL
from app.database import _connect



def latest_audit_payload(event_type: str, *, entity_id: str | None = None) -> dict | None:
    conn = _connect()
    try:
        query = "SELECT payload_json FROM audit_events WHERE event_type = ?"
        params: list[str] = [event_type]
        if entity_id is not None:
            query += " AND entity_id = ?"
            params.append(entity_id)
        query += " ORDER BY created_at DESC LIMIT 1"
        row = conn.execute(query, tuple(params)).fetchone()
        return json.loads(row["payload_json"]) if row else None
    finally:
        conn.close()


def post_meal_log_response(api_client):
    return api_client.post(
        "/api/members/member_meal_01/meal-logs",
        files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
    )



def assert_meal_analysis_audit(
    event_type: str,
    *,
    expected_model_name: str,
    expected_reason: str | None = None,
    expected_success: bool | None = None,
):
    payload = latest_audit_payload(event_type, entity_id="member_meal_01")
    assert payload is not None
    assert payload["prompt_area"] == "meal_analysis"
    assert payload["model_name"] == expected_model_name

    if expected_reason is not None:
        assert payload["fallback_reason"] == expected_reason

    if expected_success is not None:
        assert payload["success"] is expected_success

    return payload

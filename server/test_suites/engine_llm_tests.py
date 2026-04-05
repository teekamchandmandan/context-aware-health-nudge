import json
from unittest.mock import patch

import httpx

from app.engine import evaluate_member

from .engine_support import OPENAI_MODEL, latest_audit_payload


def test_llm_success_upgrade(db_conn):
    model_name = "gpt-5.4-test-phrasing"

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=(
            json.dumps(
                {
                    "content": "Try a lighter, lower-carb dinner tonight to balance your earlier meal.",
                    "explanation": "You logged a higher-carb meal today and your goal is low carb.",
                }
            ),
            model_name,
        ),
    ):
        result = evaluate_member(db_conn, "member_meal_01")

    assert result["state"] == "active"
    nudge = result["nudge"]
    assert nudge["phrasing_source"] == "llm"
    assert "tonight" in (nudge["content"] or "")

    events = db_conn.execute(
        "SELECT event_type, payload_json FROM audit_events ORDER BY created_at ASC"
    ).fetchall()
    assert len([event for event in events if event["event_type"] == "llm_call"]) == 1
    assert len([event for event in events if event["event_type"] == "llm_fallback"]) == 0

    llm_call_audit = latest_audit_payload(db_conn, "llm_call", entity_id=nudge["id"])
    assert llm_call_audit is not None
    assert llm_call_audit["prompt_area"] == "phrasing"
    assert llm_call_audit["model_name"] == model_name

    nudge_audit = latest_audit_payload(db_conn, "nudge_generated", entity_id=nudge["id"])
    assert nudge_audit is not None
    assert nudge_audit["phrasing_source"] == "llm"
    assert nudge_audit["llm_model_name"] == model_name


def test_missing_key_fallback_audit(db_conn):
    result = evaluate_member(db_conn, "member_meal_01")
    assert result["state"] == "active"
    assert result["nudge"]["phrasing_source"] == "template"

    fallback = db_conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert fallback is not None

    payload = json.loads(fallback["payload_json"])
    assert payload["fallback_reason"] == "missing_key"
    assert payload["prompt_area"] == "phrasing"
    assert payload["model_name"] == OPENAI_MODEL


def test_llm_invalid_json_fallback(db_conn):
    model_name = "gpt-5.4-test-invalid-json"

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=("not-json", model_name),
    ):
        result = evaluate_member(db_conn, "member_meal_01")

    assert result["nudge"]["phrasing_source"] == "template"
    fallback = db_conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert fallback is not None

    payload = json.loads(fallback["payload_json"])
    assert payload["fallback_reason"] == "invalid_json"
    assert payload["model_name"] == model_name


def test_llm_timeout_fallback(db_conn):
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        result = evaluate_member(db_conn, "member_meal_01")

    assert result["nudge"]["phrasing_source"] == "template"
    fallback = db_conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert fallback is not None

    payload = json.loads(fallback["payload_json"])
    assert payload["fallback_reason"] == "timeout"
    assert payload["model_name"] == OPENAI_MODEL


def test_validation_failure_fallback(db_conn):
    model_name = "gpt-5.4-test-validation"

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=(
            json.dumps(
                {
                    "content": "This may diagnose the issue for you.",
                    "explanation": "Medication is not needed right now.",
                }
            ),
            model_name,
        ),
    ):
        result = evaluate_member(db_conn, "member_meal_01")

    assert result["nudge"]["phrasing_source"] == "template"
    assert result["nudge"]["content"] == "Try a lighter, lower-carb dinner to balance today's earlier meal."

    fallback = db_conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    assert fallback is not None

    payload = json.loads(fallback["payload_json"])
    assert payload["fallback_reason"] == "validation_failure"
    assert payload["model_name"] == model_name


def test_existing_active_nudge_skips_rephrase(db_conn):
    calls = {"count": 0}

    def fake_request(*_args, **_kwargs):
        calls["count"] += 1
        return (
            json.dumps(
                {
                    "content": "Try a lighter dinner tonight to keep things aligned.",
                    "explanation": "You logged a higher-carb meal today and your goal is low carb.",
                }
            ),
            "gpt-5.4-test-idempotent",
        )

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=fake_request,
    ):
        first = evaluate_member(db_conn, "member_meal_01")
        second = evaluate_member(db_conn, "member_meal_01")

    assert calls["count"] == 1
    assert first["nudge"]["id"] == second["nudge"]["id"]
    assert second["nudge"]["phrasing_source"] == "llm"


def test_support_risk_skips_llm(db_conn):
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=AssertionError("LLM should not run for escalations"),
    ):
        result = evaluate_member(db_conn, "member_support_01")

    assert result["state"] == "escalated"
    llm_events = db_conn.execute(
        "SELECT COUNT(*) AS cnt FROM audit_events WHERE event_type IN ('llm_call', 'llm_fallback')"
    ).fetchone()["cnt"]
    assert llm_events == 0

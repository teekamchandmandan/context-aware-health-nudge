"""Phase 03 API contract tests using FastAPI TestClient."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure server package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Use a test-specific database
os.environ["DATABASE_PATH"] = str(Path(__file__).resolve().parent / "test_api.db")
os.environ["DEBUG"] = "true"
os.environ["OPENAI_API_KEY"] = ""

import httpx
from fastapi.testclient import TestClient

from app.core.config import OPENAI_MODEL
from app.database import _connect
from app.main import app
from app.meal_analysis import create_meal_draft
from app.models.meals import MealDraftResponse
from app.seed import reset_and_seed

client = TestClient(app)

PASS = 0
FAIL = 0


def ok(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  — {detail}")


def section(title: str):
    print(f"\n{'─' * 60}\n{title}\n{'─' * 60}")


def seed():
    reset_and_seed()


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


# ── GET /api/members/{member_id}/nudge ───────────────────────────────────────

def test_member_nudge_active():
    section("GET /nudge — member_meal_01 returns active nudge")
    seed()
    r = client.get("/api/members/member_meal_01/nudge")
    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    ok("state is 'active'", data["state"] == "active", f"got {data['state']}")
    ok("member.id matches", data["member"]["id"] == "member_meal_01")
    ok("member.name is Alice Chen", data["member"]["name"] == "Alice Chen")
    ok("nudge is not null", data["nudge"] is not None)
    nudge = data["nudge"]
    ok("nudge_type is meal_guidance", nudge["nudge_type"] == "meal_guidance")
    ok("content is populated", nudge["content"] is not None and len(nudge["content"]) > 0,
       f"got content={nudge['content']!r}")
    ok("confidence is 0.86", nudge["confidence"] == 0.86)
    ok("status is active", nudge["status"] == "active")
    ok("phrasing_source is template", nudge["phrasing_source"] == "template")
    ok("created_at present", "created_at" in nudge)
    return data


def test_member_nudge_idempotent():
    section("GET /nudge — repeated calls return same nudge")
    seed()
    r1 = client.get("/api/members/member_meal_01/nudge")
    r2 = client.get("/api/members/member_meal_01/nudge")
    ok("both 200", r1.status_code == 200 and r2.status_code == 200)
    d1, d2 = r1.json(), r2.json()
    ok("same nudge ID", d1["nudge"]["id"] == d2["nudge"]["id"],
       f"{d1['nudge']['id']} vs {d2['nudge']['id']}")


def test_member_nudge_llm_success():
    section("GET /nudge — successful mocked LLM phrasing")
    seed()
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=(
            '{"content":"Try a lighter dinner tonight to stay aligned with your goal.","explanation":"You logged a higher-carb meal today and your goal is low carb."}',
            "gpt-5-mini-test-api",
        ),
    ):
        r = client.get("/api/members/member_meal_01/nudge")

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    ok("phrasing_source is llm", data["nudge"]["phrasing_source"] == "llm", f"got {data['nudge']['phrasing_source']}")
    ok("llm content returned", "tonight" in data["nudge"]["content"], f"got {data['nudge']['content']!r}")


def test_member_nudge_llm_timeout_fallback():
    section("GET /nudge — timeout falls back to template")
    seed()
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        r = client.get("/api/members/member_meal_01/nudge")

    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("phrasing_source is template", data["nudge"]["phrasing_source"] == "template")
    ok(
        "template content preserved",
        data["nudge"]["content"] == "Try a lighter, lower-carb dinner to balance today's earlier meal.",
        f"got {data['nudge']['content']!r}",
    )


def test_member_nudge_llm_idempotent_reads():
    section("GET /nudge — existing active nudge is not rephrased twice")
    seed()
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
        r1 = client.get("/api/members/member_meal_01/nudge")
        r2 = client.get("/api/members/member_meal_01/nudge")

    ok("both 200", r1.status_code == 200 and r2.status_code == 200)
    ok("only one provider call", calls["count"] == 1, f"got {calls['count']}")
    ok("same nudge id", r1.json()["nudge"]["id"] == r2.json()["nudge"]["id"])


def test_coach_nudges_show_llm_source():
    section("GET /coach/nudges — coach list reflects llm phrasing source")
    seed()
    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=(
            '{"content":"Try a lighter dinner tonight to stay aligned with your goal.","explanation":"You logged a higher-carb meal today and your goal is low carb."}',
            "gpt-5-mini-test-coach",
        ),
    ):
        client.get("/api/members/member_meal_01/nudge")

    r = client.get("/api/coach/nudges")
    ok("status 200", r.status_code == 200)
    items = r.json()["items"]
    meal_item = next((item for item in items if item["member_id"] == "member_meal_01"), None)
    ok("meal member nudge present", meal_item is not None)
    if meal_item:
        ok("phrasing_source is llm", meal_item["phrasing_source"] == "llm", f"got {meal_item['phrasing_source']}")
        ok(
            "visible food summary included",
            meal_item["visible_food_summary"] == "The photo appears to show a pasta dish with bread.",
            f"got {meal_item['visible_food_summary']!r}",
        )


def test_member_nudge_weight():
    section("GET /nudge — member_weight_01 returns weight check-in")
    seed()
    r = client.get("/api/members/member_weight_01/nudge")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("state is 'active'", data["state"] == "active")
    ok("nudge_type is weight_check_in", data["nudge"]["nudge_type"] == "weight_check_in")
    ok("content is populated", data["nudge"]["content"] is not None)


def test_member_nudge_no_nudge():
    section("GET /nudge — member_catchup_01 returns no_nudge")
    seed()
    r = client.get("/api/members/member_catchup_01/nudge")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("state is 'no_nudge'", data["state"] == "no_nudge", f"got {data['state']}")
    ok("member.id matches", data["member"]["id"] == "member_catchup_01")
    ok("member.name is Diego Rivera", data["member"]["name"] == "Diego Rivera")
    ok("nudge is null", data.get("nudge") is None)


def test_member_nudge_escalated():
    section("GET /nudge — member_support_01 returns escalated")
    seed()
    r = client.get("/api/members/member_support_01/nudge")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("state is 'escalated'", data["state"] == "escalated", f"got {data['state']}")
    ok("nudge is null", data.get("nudge") is None)


def test_member_nudge_404():
    section("GET /nudge — unknown member returns 404")
    seed()
    r = client.get("/api/members/nonexistent/nudge")
    ok("status 404", r.status_code == 404, f"got {r.status_code}")


# ── POST /api/nudges/{nudge_id}/action ───────────────────────────────────────

def test_action_act_now():
    section("POST /action — act_now transitions to acted")
    seed()
    # Get a nudge first
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "act_now"})
    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    ok("nudge_id matches", data["nudge_id"] == nudge_id)
    ok("action_type is act_now", data["action_type"] == "act_now")
    ok("nudge_status is acted", data["nudge_status"] == "acted")
    ok("recorded_at present", "recorded_at" in data)

    audit_payload = latest_audit_payload("user_action", entity_id=nudge_id)
    ok("user_action audit recorded", audit_payload is not None)
    if audit_payload:
        ok("audit action_type is act_now", audit_payload["action_type"] == "act_now")
        ok("audit previous_status is active", audit_payload["previous_status"] == "active")
        ok("audit new_status is acted", audit_payload["new_status"] == "acted")


def test_action_dismiss():
    section("POST /action — dismiss transitions to dismissed")
    seed()
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "dismiss"})
    ok("status 200", r.status_code == 200)
    ok("nudge_status is dismissed", r.json()["nudge_status"] == "dismissed")

    audit_payload = latest_audit_payload("user_action", entity_id=nudge_id)
    ok("dismiss audit recorded", audit_payload is not None)
    if audit_payload:
        ok("audit action_type is dismiss", audit_payload["action_type"] == "dismiss")
        ok("audit new_status is dismissed", audit_payload["new_status"] == "dismissed")


def test_action_ask_for_help():
    section("POST /action — ask_for_help creates escalation")
    seed()
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "ask_for_help"})
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("nudge_status is escalated", data["nudge_status"] == "escalated")

    # Verify escalation visible to coach
    er = client.get("/api/coach/escalations")
    esc_items = er.json()["items"]
    member_esc = [e for e in esc_items if e["source"] == "member_action"]
    ok("escalation visible in coach list", len(member_esc) > 0,
       f"got {len(member_esc)} member_action escalations")

    action_audit = latest_audit_payload("user_action", entity_id=nudge_id)
    ok("ask_for_help audit recorded", action_audit is not None)
    if action_audit:
        ok("audit action_type is ask_for_help", action_audit["action_type"] == "ask_for_help")
        ok("audit new_status is escalated", action_audit["new_status"] == "escalated")

    escalation_audit = latest_audit_payload("escalation_created")
    ok("member_action escalation audit recorded", escalation_audit is not None)
    if escalation_audit:
        ok("escalation audit source is member_action", escalation_audit["source"] == "member_action")
        ok("escalation audit nudge_id matches", escalation_audit["nudge_id"] == nudge_id)


def test_action_409_terminal():
    section("POST /action — 409 on terminal nudge")
    seed()
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    # First action succeeds
    client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "dismiss"})
    # Second action should fail
    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "act_now"})
    ok("status 409", r.status_code == 409, f"got {r.status_code}")


def test_action_404_unknown():
    section("POST /action — 404 for unknown nudge")
    seed()
    r = client.post("/api/nudges/nonexistent/action", json={"action_type": "act_now"})
    ok("status 404", r.status_code == 404, f"got {r.status_code}")


def test_action_422_invalid_type():
    section("POST /action — 422 for invalid action_type")
    seed()
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "invalid"})
    ok("status 422", r.status_code == 422, f"got {r.status_code}")


def test_meal_analysis_photo_only_fallback():
    section("Meal analysis — fallback supports photo-only input")
    seed()

    analysis = create_meal_draft(
        photo_bytes=b"fake-image-bytes",
        photo_content_type="image/jpeg",
    )

    ok("fallback profile is unclear", analysis.meal_profile == "unclear", f"got {analysis.meal_profile!r}")
    ok("fallback omits visible summary", analysis.visible_food_summary is None, f"got {analysis.visible_food_summary!r}")


def test_meal_analysis_provider_uses_photo_only_payload():
    section("Meal analysis — provider call is photo only")
    seed()

    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        return_value=(
            '{"meal_profile":"higher_carb",'
            '"visible_food_summary":"The photo appears to show a pasta dish with bread."}',
            "gpt-5-mini-test-meal",
        ),
    ) as mocked_request:
        analysis = create_meal_draft(
            photo_bytes=b"fake-image-bytes",
            photo_content_type="image/jpeg",
        )

    ok("provider result profile saved", analysis.meal_profile == "higher_carb", f"got {analysis.meal_profile!r}")
    ok(
        "provider result visible summary saved",
        analysis.visible_food_summary == "The photo appears to show a pasta dish with bread.",
        f"got {analysis.visible_food_summary!r}",
    )
    ok(
        "provider called with photo only",
        mocked_request.call_args == (("test-key",), {"photo_bytes": b"fake-image-bytes", "photo_content_type": "image/jpeg"}),
        f"got {mocked_request.call_args!r}",
    )


def test_meal_analysis_llm_audit_records_model_name():
    section("Meal analysis — llm_call audit records prompt area and model")
    seed()

    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        return_value=(
            '{"meal_profile":"higher_carb",'
            '"visible_food_summary":"The photo appears to show a pasta dish with bread."}',
            "gpt-5-mini-test-meal-audit",
        ),
    ):
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    payload = latest_audit_payload("llm_call", entity_id="member_meal_01")
    ok("llm_call audit recorded", payload is not None)
    if payload:
        ok("prompt_area is meal_analysis", payload["prompt_area"] == "meal_analysis", f"got {payload['prompt_area']}")
        ok("model_name recorded", payload["model_name"] == "gpt-5-mini-test-meal-audit", f"got {payload['model_name']}")
        ok("llm_call marked successful", payload["success"] is True, f"got {payload['success']}")


def test_meal_analysis_missing_key_audit_records_model_name():
    section("Meal analysis — missing API key records fallback audit")
    seed()

    r = client.post(
        "/api/members/member_meal_01/meal-logs",
        files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    payload = latest_audit_payload("llm_fallback", entity_id="member_meal_01")
    ok("llm_fallback audit recorded", payload is not None)
    if payload:
        ok("fallback reason is missing_key", payload["fallback_reason"] == "missing_key", f"got {payload['fallback_reason']}")
        ok("prompt_area is meal_analysis", payload["prompt_area"] == "meal_analysis", f"got {payload['prompt_area']}")
        ok("model_name recorded", payload["model_name"] == OPENAI_MODEL, f"got {payload['model_name']}")


def test_meal_analysis_timeout_records_audit():
    section("Meal analysis — timeout records llm_call failure and fallback")
    seed()

    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    fallback_payload = latest_audit_payload("llm_fallback", entity_id="member_meal_01")
    ok("llm_fallback audit recorded", fallback_payload is not None)
    if fallback_payload:
        ok("fallback reason is timeout", fallback_payload["fallback_reason"] == "timeout", f"got {fallback_payload['fallback_reason']}")
        ok("timeout model_name recorded", fallback_payload["model_name"] == OPENAI_MODEL, f"got {fallback_payload['model_name']}")


def test_meal_analysis_provider_error_records_audit():
    section("Meal analysis — provider error records fallback audit")
    seed()

    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        side_effect=httpx.HTTPError("provider error"),
    ):
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    fallback_payload = latest_audit_payload("llm_fallback", entity_id="member_meal_01")
    ok("llm_fallback audit recorded", fallback_payload is not None)
    if fallback_payload:
        ok("fallback reason is provider_error", fallback_payload["fallback_reason"] == "provider_error", f"got {fallback_payload['fallback_reason']}")
        ok("provider error model_name recorded", fallback_payload["model_name"] == OPENAI_MODEL, f"got {fallback_payload['model_name']}")


def test_meal_analysis_invalid_json_records_audit():
    section("Meal analysis — invalid JSON records fallback audit")
    seed()

    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        return_value=("not-json", "gpt-5-mini-test-meal-invalid-json"),
    ):
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    fallback_payload = latest_audit_payload("llm_fallback", entity_id="member_meal_01")
    ok("llm_fallback audit recorded", fallback_payload is not None)
    if fallback_payload:
        ok("fallback reason is invalid_json", fallback_payload["fallback_reason"] == "invalid_json", f"got {fallback_payload['fallback_reason']}")
        ok("invalid json model_name recorded", fallback_payload["model_name"] == "gpt-5-mini-test-meal-invalid-json", f"got {fallback_payload['model_name']}")


def test_meal_analysis_validation_failure_records_audit():
    section("Meal analysis — validation failure records fallback audit")
    seed()

    with patch("app.meal_analysis.get_openai_api_key", return_value="test-key"), patch(
        "app.meal_analysis._request_meal_analysis_json",
        return_value=(
            '{"meal_profile":"breakfasty",'
            '"visible_food_summary":"The photo appears to show a plated meal."}',
            "gpt-5-mini-test-meal-validation",
        ),
    ):
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    fallback_payload = latest_audit_payload("llm_fallback", entity_id="member_meal_01")
    ok("llm_fallback audit recorded", fallback_payload is not None)
    if fallback_payload:
        ok(
            "fallback reason is validation_failure",
            fallback_payload["fallback_reason"] == "validation_failure",
            f"got {fallback_payload['fallback_reason']}",
        )
        ok(
            "validation failure model_name recorded",
            fallback_payload["model_name"] == "gpt-5-mini-test-meal-validation",
            f"got {fallback_payload['model_name']}",
        )


def test_meal_log_one_step_rejects_description_field():
    section("POST /meal-logs — rejects extra description field")
    seed()

    with patch(
        "app.main.create_meal_draft",
        return_value=MealDraftResponse(
            meal_profile="higher_carb",
            visible_food_summary="The photo appears to show a pasta dish with bread.",
        ),
    ) as mocked_create_meal_draft:
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            data={"description": "Pasta carbonara with garlic bread"},
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 422", r.status_code == 422, f"got {r.status_code}")
    ok("validation mentions unexpected fields", "unexpected meal upload fields" in json.dumps(r.json()), f"got {r.text}")
    ok("analysis not called", mocked_create_meal_draft.call_count == 0, f"got {mocked_create_meal_draft.call_count}")


def test_meal_log_one_step_photo_only():
    section("POST /meal-logs — photo-only save allowed")
    seed()

    with patch(
        "app.main.create_meal_draft",
        return_value=MealDraftResponse(
            meal_profile="higher_protein",
            visible_food_summary="The photo appears to show grilled chicken and vegetables.",
        ),
    ):
        r = client.post(
            "/api/members/member_meal_01/meal-logs",
            files={"photo": ("meal.jpg", b"fake-image-bytes", "image/jpeg")},
        )

    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    ok("photo attached not persisted", "photo_attached" not in data["payload"], f"got {data['payload']!r}")
    ok("meal_input_method not persisted", "meal_input_method" not in data["payload"], f"got {data['payload']!r}")
    ok("meal profile saved", data["payload"]["meal_profile"] == "higher_protein")
    ok(
        "visible summary saved",
        data["payload"]["visible_food_summary"] == "The photo appears to show grilled chicken and vegetables.",
        f"got {data['payload']!r}",
    )


def test_meal_log_requires_photo():
    section("POST /meal-logs — requires a meal photo")
    seed()

    r = client.post("/api/members/member_meal_01/meal-logs")
    ok("status 422", r.status_code == 422, f"got {r.status_code}")
    ok(
        "validation mentions meal photo",
        "meal photo" in json.dumps(r.json()),
        f"got {r.text}",
    )


def test_meal_log_rejects_non_image_upload():
    section("POST /meal-logs — rejects non-image uploads")
    seed()

    r = client.post(
        "/api/members/member_meal_01/meal-logs",
        files={"photo": ("meal.txt", b"not-an-image", "text/plain")},
    )
    ok("status 422", r.status_code == 422, f"got {r.status_code}")
    ok("validation mentions image", "image" in json.dumps(r.json()), f"got {r.text}")


def test_signal_weight_logged():
    section("POST /signals — weight_logged")
    seed()
    r = client.post("/api/members/member_weight_01/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 180.5}
    })
    ok("status 200", r.status_code == 200)
    ok("weight_lb in payload", r.json()["payload"]["weight_lb"] == 180.5)


def test_signal_re_evaluates_existing_active_nudge():
    section("POST /signals — fresh signal re-evaluates existing active nudge")
    seed()

    initial = client.get("/api/members/member_weight_01/nudge")
    ok("initial nudge is active", initial.status_code == 200 and initial.json()["state"] == "active")

    signal = client.post("/api/members/member_weight_01/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 180.5}
    })
    ok("signal accepted", signal.status_code == 200, f"got {signal.status_code}")

    follow_up = client.get("/api/members/member_weight_01/nudge")
    ok("follow-up state is no_nudge", follow_up.status_code == 200 and follow_up.json()["state"] == "no_nudge",
       f"got {follow_up.status_code}, {follow_up.json() if follow_up.status_code == 200 else follow_up.text}")


def test_signal_mood_logged():
    section("POST /signals — mood_logged")
    seed()
    r = client.post("/api/members/member_support_01/signals", json={
        "signal_type": "mood_logged",
        "payload": {"mood": "high"}
    })
    ok("status 200", r.status_code == 200)
    ok("mood in payload", r.json()["payload"]["mood"] == "high")


def test_signal_422_invalid_values():
    section("POST /signals — 422 for invalid payload values")
    seed()

    mood = client.post("/api/members/member_support_01/signals", json={
        "signal_type": "mood_logged",
        "payload": {"mood": "good"}
    })
    ok("422 for invalid mood value", mood.status_code == 422, f"got {mood.status_code}")
    ok(
        "mood error mentions allowed values",
        "low, neutral, high" in json.dumps(mood.json()),
        f"got {mood.text}",
    )

    weight = client.post("/api/members/member_weight_01/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 0}
    })
    ok("422 for non-positive weight", weight.status_code == 422, f"got {weight.status_code}")

    sleep = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "sleep_logged",
        "payload": {"sleep_hours": 25}
    })
    ok("422 for sleep above 24h", sleep.status_code == 422, f"got {sleep.status_code}")


def test_signal_sleep_logged():
    section("POST /signals — sleep_logged")
    seed()
    r = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "sleep_logged",
        "payload": {"sleep_hours": 7.5}
    })
    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    ok("signal_type is sleep_logged", data["signal_type"] == "sleep_logged")
    ok("sleep_hours in payload", data["payload"]["sleep_hours"] == 7.5)


def test_signal_422_missing_required():
    section("POST /signals — 422 for missing required fields")
    seed()
    # weight_logged without weight_lb
    r3 = client.post("/api/members/member_weight_01/signals", json={
        "signal_type": "weight_logged",
        "payload": {}
    })
    ok("422 without weight_lb", r3.status_code == 422, f"got {r3.status_code}")

    # mood_logged without mood
    r4 = client.post("/api/members/member_support_01/signals", json={
        "signal_type": "mood_logged",
        "payload": {}
    })
    ok("422 without mood", r4.status_code == 422, f"got {r4.status_code}")

    # sleep_logged without sleep_hours
    r5 = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "sleep_logged",
        "payload": {}
    })
    ok("422 without sleep_hours", r5.status_code == 422, f"got {r5.status_code}")


def test_signal_422_unknown_type():
    section("POST /signals — 422 for unknown signal_type")
    seed()
    r = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "unknown_type",
        "payload": {"foo": "bar"}
    })
    ok("422 for unknown signal_type", r.status_code == 422, f"got {r.status_code}")


def test_signal_404_unknown_member():
    section("POST /signals — 404 for unknown member")
    seed()
    r = client.post("/api/members/nonexistent/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 175.0}
    })
    ok("404 for unknown member", r.status_code == 404, f"got {r.status_code}")


# ── GET /api/members/{member_id}/signals/latest ──────────────────────────────

def test_signals_latest():
    section("GET /signals/latest — returns latest per-type entries")
    seed()
    member_id = "member_meal_01"

    # member_meal_01 has only a meal_logged signal seeded → no tracked types present
    r0 = client.get(f"/api/members/{member_id}/signals/latest")
    ok("status 200 on empty tracked types", r0.status_code == 200, f"got {r0.status_code}")
    ok("no weight/sleep/mood entries initially", r0.json() == {}, f"got {r0.json()}")

    # Post a weight signal
    client.post(f"/api/members/{member_id}/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 180.5}
    })
    r1 = client.get(f"/api/members/{member_id}/signals/latest")
    ok("status 200 after weight post", r1.status_code == 200)
    data1 = r1.json()
    ok("weight_logged present", "weight_logged" in data1, f"keys: {list(data1.keys())}")
    ok("sleep_logged absent", "sleep_logged" not in data1)
    ok("mood_logged absent", "mood_logged" not in data1)
    ok("weight_lb is 180.5", data1["weight_logged"]["payload"]["weight_lb"] == 180.5,
       f"got {data1['weight_logged']['payload']}")
    ok("logged_at present", "logged_at" in data1["weight_logged"])

    # Post a newer weight — only the latest should be returned
    client.post(f"/api/members/{member_id}/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 185.0}
    })
    r2 = client.get(f"/api/members/{member_id}/signals/latest")
    ok("only latest weight returned", r2.json()["weight_logged"]["payload"]["weight_lb"] == 185.0,
       f"got {r2.json()['weight_logged']['payload']}")

    # Post sleep and mood signals
    client.post(f"/api/members/{member_id}/signals", json={
        "signal_type": "sleep_logged",
        "payload": {"sleep_hours": 7.5}
    })
    client.post(f"/api/members/{member_id}/signals", json={
        "signal_type": "mood_logged",
        "payload": {"mood": "high"}
    })
    r3 = client.get(f"/api/members/{member_id}/signals/latest")
    data3 = r3.json()
    ok("all three types present", all(k in data3 for k in ("weight_logged", "sleep_logged", "mood_logged")),
       f"keys: {list(data3.keys())}")
    ok("sleep_hours correct", data3["sleep_logged"]["payload"]["sleep_hours"] == 7.5)
    ok("mood correct", data3["mood_logged"]["payload"]["mood"] == "high")

    # 404 for unknown member
    r404 = client.get("/api/members/nonexistent/signals/latest")
    ok("404 for unknown member", r404.status_code == 404, f"got {r404.status_code}")


# ── GET /api/coach/nudges ───────────────────────────────────────────────────

def test_coach_nudges():
    section("GET /coach/nudges — returns seeded nudges")
    seed()
    # Trigger some nudges first
    client.get("/api/members/member_meal_01/nudge")
    client.get("/api/members/member_weight_01/nudge")

    r = client.get("/api/coach/nudges")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("items is a list", isinstance(data["items"], list))
    ok("limit is 20", data["limit"] == 20)
    ok("count matches items length", data["count"] == len(data["items"]))
    # Should have at least the seeded + triggered nudges
    ok("has items", data["count"] > 0, f"got {data['count']}")

    # Check item shape
    if data["items"]:
        item = data["items"][0]
        for field in ["nudge_id", "member_id", "member_name", "nudge_type",
                       "visible_food_summary", "explanation", "matched_reason", "confidence", "status",
                       "phrasing_source", "created_at"]:
            ok(f"item has '{field}'", field in item, f"missing {field}")
        ok("phrasing_source is a string",
           isinstance(item["phrasing_source"], str) and len(item["phrasing_source"]) > 0,
           f"got {item.get('phrasing_source')!r}")


def test_coach_nudges_limit():
    section("GET /coach/nudges — limit parameter")
    seed()
    r = client.get("/api/coach/nudges?limit=2")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("limit is 2", data["limit"] == 2)
    ok("count <= 2", data["count"] <= 2)

    # Over-limit rejected
    r2 = client.get("/api/coach/nudges?limit=100")
    ok("422 for limit > 50", r2.status_code == 422, f"got {r2.status_code}")


# ── GET /api/coach/escalations ───────────────────────────────────────────────

def test_coach_escalations():
    section("GET /coach/escalations — returns open escalations")
    seed()
    # Trigger escalation for member_support_01
    client.get("/api/members/member_support_01/nudge")

    r = client.get("/api/coach/escalations")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("items is a list", isinstance(data["items"], list))
    ok("has at least 1 escalation", data["count"] >= 1, f"got {data['count']}")

    if data["items"]:
        item = data["items"][0]
        for field in ["escalation_id", "member_id", "member_name", "reason",
                       "source", "status", "created_at"]:
            ok(f"item has '{field}'", field in item, f"missing {field}")
        ok("status is 'open'", item["status"] == "open")


def test_coach_escalations_from_ask_for_help():
    section("GET /coach/escalations — ask_for_help escalation visible")
    seed()
    # Get a nudge and ask for help
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]
    client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "ask_for_help"})

    r = client.get("/api/coach/escalations")
    data = r.json()
    member_action_escs = [e for e in data["items"] if e["source"] == "member_action"]
    ok("member_action escalation found", len(member_action_escs) >= 1,
       f"got {len(member_action_escs)}")
    if member_action_escs:
        ok("member_id is member_meal_01",
           member_action_escs[0]["member_id"] == "member_meal_01")


# ── Run All ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_member_nudge_active,
        test_member_nudge_idempotent,
        test_member_nudge_llm_success,
        test_member_nudge_llm_timeout_fallback,
        test_member_nudge_llm_idempotent_reads,
        test_member_nudge_weight,
        test_member_nudge_no_nudge,
        test_member_nudge_escalated,
        test_member_nudge_404,
        test_action_act_now,
        test_action_dismiss,
        test_action_ask_for_help,
        test_action_409_terminal,
        test_action_404_unknown,
        test_action_422_invalid_type,
        test_meal_analysis_photo_only_fallback,
        test_meal_analysis_provider_uses_photo_only_payload,
        test_meal_analysis_llm_audit_records_model_name,
        test_meal_analysis_missing_key_audit_records_model_name,
        test_meal_analysis_timeout_records_audit,
        test_meal_analysis_provider_error_records_audit,
        test_meal_analysis_invalid_json_records_audit,
        test_meal_analysis_validation_failure_records_audit,
        test_meal_log_one_step_rejects_description_field,
        test_meal_log_one_step_photo_only,
        test_meal_log_requires_photo,
        test_meal_log_rejects_non_image_upload,
        test_signal_weight_logged,
        test_signal_re_evaluates_existing_active_nudge,
        test_signal_mood_logged,
        test_signal_422_invalid_values,
        test_signal_sleep_logged,
        test_signal_422_missing_required,
        test_signal_422_unknown_type,
        test_signal_404_unknown_member,
        test_signals_latest,
        test_coach_nudges,
        test_coach_nudges_show_llm_source,
        test_coach_nudges_limit,
        test_coach_escalations,
        test_coach_escalations_from_ask_for_help,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  ✗ {t.__name__} EXCEPTION: {e}")

    print(f"\n{'═' * 60}")
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print(f"{'═' * 60}")
    sys.exit(1 if FAIL else 0)

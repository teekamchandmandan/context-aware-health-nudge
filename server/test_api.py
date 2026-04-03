"""Phase 03 API contract tests using FastAPI TestClient."""

import json
import os
import sys
from pathlib import Path

# Ensure server package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Use a test-specific database
os.environ["DATABASE_PATH"] = str(Path(__file__).resolve().parent / "test_api.db")
os.environ["DEBUG"] = "true"

from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
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


def test_member_nudge_weight():
    section("GET /nudge — member_weight_01 returns weight check-in")
    seed()
    r = client.get("/api/members/member_weight_01/nudge")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("state is 'active'", data["state"] == "active")
    ok("nudge_type is weight_check_in", data["nudge"]["nudge_type"] == "weight_check_in")
    ok("content is populated", data["nudge"]["content"] is not None)


def test_member_nudge_escalated():
    section("GET /nudge — member_support_01 returns escalated")
    seed()
    r = client.get("/api/members/member_support_01/nudge")
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("state is 'escalated'", data["state"] == "escalated", f"got {data['state']}")
    ok("nudge is null", data["nudge"] is None)
    ok("escalation_created is true", data.get("escalation_created") is True)


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
    ok("escalation_created is false", data["escalation_created"] is False)
    ok("recorded_at present", "recorded_at" in data)


def test_action_dismiss():
    section("POST /action — dismiss transitions to dismissed")
    seed()
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "dismiss"})
    ok("status 200", r.status_code == 200)
    ok("nudge_status is dismissed", r.json()["nudge_status"] == "dismissed")


def test_action_ask_for_help():
    section("POST /action — ask_for_help creates escalation")
    seed()
    nr = client.get("/api/members/member_meal_01/nudge")
    nudge_id = nr.json()["nudge"]["id"]

    r = client.post(f"/api/nudges/{nudge_id}/action", json={"action_type": "ask_for_help"})
    ok("status 200", r.status_code == 200)
    data = r.json()
    ok("nudge_status is escalated", data["nudge_status"] == "escalated")
    ok("escalation_created is true", data["escalation_created"] is True)

    # Verify escalation visible to coach
    er = client.get("/api/coach/escalations")
    esc_items = er.json()["items"]
    member_esc = [e for e in esc_items if e["source"] == "member_action"]
    ok("escalation visible in coach list", len(member_esc) > 0,
       f"got {len(member_esc)} member_action escalations")


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


# ── POST /api/members/{member_id}/signals ────────────────────────────────────

def test_signal_meal_logged():
    section("POST /signals — meal_logged")
    seed()
    r = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "meal_logged",
        "payload": {"meal_type": "dinner", "carbs_g": 45, "protein_g": 22}
    })
    ok("status 200", r.status_code == 200, f"got {r.status_code}")
    data = r.json()
    ok("id present", "id" in data)
    ok("signal_type is meal_logged", data["signal_type"] == "meal_logged")
    ok("payload has meal_type", data["payload"]["meal_type"] == "dinner")
    ok("created_at present", "created_at" in data)


def test_signal_weight_logged():
    section("POST /signals — weight_logged")
    seed()
    r = client.post("/api/members/member_weight_01/signals", json={
        "signal_type": "weight_logged",
        "payload": {"weight_lb": 180.5}
    })
    ok("status 200", r.status_code == 200)
    ok("weight_lb in payload", r.json()["payload"]["weight_lb"] == 180.5)


def test_signal_mood_logged():
    section("POST /signals — mood_logged")
    seed()
    r = client.post("/api/members/member_support_01/signals", json={
        "signal_type": "mood_logged",
        "payload": {"mood": "good", "note": "Feeling better today"}
    })
    ok("status 200", r.status_code == 200)
    ok("mood in payload", r.json()["payload"]["mood"] == "good")


def test_signal_422_missing_required():
    section("POST /signals — 422 for missing required fields")
    seed()
    # meal_logged without meal_type
    r = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "meal_logged",
        "payload": {"carbs_g": 30}
    })
    ok("422 without meal_type", r.status_code == 422, f"got {r.status_code}")

    # meal_logged with meal_type but no carbs_g or meal_tag
    r2 = client.post("/api/members/member_meal_01/signals", json={
        "signal_type": "meal_logged",
        "payload": {"meal_type": "lunch"}
    })
    ok("422 without carbs_g or meal_tag", r2.status_code == 422, f"got {r2.status_code}")

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
                       "explanation", "matched_reason", "confidence", "status", "created_at"]:
            ok(f"item has '{field}'", field in item, f"missing {field}")


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
        test_member_nudge_weight,
        test_member_nudge_escalated,
        test_member_nudge_404,
        test_action_act_now,
        test_action_dismiss,
        test_action_ask_for_help,
        test_action_409_terminal,
        test_action_404_unknown,
        test_action_422_invalid_type,
        test_signal_meal_logged,
        test_signal_weight_logged,
        test_signal_mood_logged,
        test_signal_422_missing_required,
        test_signal_422_unknown_type,
        test_signal_404_unknown_member,
        test_coach_nudges,
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

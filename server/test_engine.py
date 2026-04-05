"""Verification tests for the Phase 2 decision engine."""

import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure the server package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["OPENAI_API_KEY"] = ""

import httpx
from pydantic import ValidationError

from app.core.config import OPENAI_MODEL
from app.database import _connect
from app.seed import reset_and_seed
from app.engine import (
    evaluate_member,
    select_nudge,
    check_meal_goal_mismatch,
    check_missing_weight_log,
    check_support_risk,
    _ts,
    _now,
    _id,
)
from app.phrasing import PhrasingOutput

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


# ── Setup ────────────────────────────────────────────────────────────────────

def fresh_db() -> sqlite3.Connection:
    """Reset seed data and return a connection."""
    reset_and_seed()
    conn = _connect()
    return conn


def latest_audit_payload(
    conn: sqlite3.Connection,
    event_type: str,
    *,
    entity_id: str | None = None,
) -> dict | None:
    query = "SELECT payload_json FROM audit_events WHERE event_type = ?"
    params: list[str] = [event_type]
    if entity_id is not None:
        query += " AND entity_id = ?"
        params.append(entity_id)
    query += " ORDER BY created_at DESC LIMIT 1"
    row = conn.execute(query, tuple(params)).fetchone()
    return json.loads(row["payload_json"]) if row else None


# ── Test 1: Scenario — member_meal_01 (meal goal mismatch) ──────────────────

def test_meal_mismatch():
    section("Scenario 1: member_meal_01 — meal goal mismatch")
    conn = fresh_db()

    result = evaluate_member(conn, "member_meal_01")
    ok("state is 'active'", result["state"] == "active", f"got {result['state']}")
    nudge = result.get("nudge", {})
    ok("nudge_type is 'meal_guidance'", nudge.get("nudge_type") == "meal_guidance", f"got {nudge.get('nudge_type')}")
    ok("confidence is 0.86", nudge.get("confidence") == 0.86, f"got {nudge.get('confidence')}")
    ok("matched_reason is 'meal_goal_mismatch'", nudge.get("matched_reason") == "meal_goal_mismatch")
    ok("delivered_at is set", nudge.get("delivered_at") is not None)
    ok("status is 'active'", nudge.get("status") == "active")

    audit_payload = latest_audit_payload(conn, "nudge_generated", entity_id=nudge.get("id"))
    ok("nudge_generated audit recorded", audit_payload is not None)
    if audit_payload:
        ok("audit stores member_id", audit_payload["member_id"] == "member_meal_01")
        ok("audit stores nudge_id", audit_payload["nudge_id"] == nudge.get("id"))
        ok("audit stores confidence", audit_payload["confidence"] == 0.86)
        ok("audit stores phrasing_source", audit_payload["phrasing_source"] == "template")

    conn.close()


# ── Test 2: Idempotency — second call returns same nudge ────────────────────

def test_idempotency():
    section("Idempotency: second call returns same active nudge")
    conn = fresh_db()

    r1 = evaluate_member(conn, "member_meal_01")
    r2 = evaluate_member(conn, "member_meal_01")
    ok("both return state 'active'", r1["state"] == "active" and r2["state"] == "active")
    ok("same nudge ID", r1["nudge"]["id"] == r2["nudge"]["id"],
       f"{r1['nudge']['id']} vs {r2['nudge']['id']}")

    # Count active nudges — should be exactly 1
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM nudges WHERE member_id = 'member_meal_01' AND status = 'active'"
    ).fetchone()["cnt"]
    ok("exactly 1 active nudge in DB", count == 1, f"got {count}")

    conn.close()


# ── Test 3: Scenario — member_weight_01 (missing weight log) ────────────────

def test_missing_weight():
    section("Scenario 2: member_weight_01 — missing weight log")
    conn = fresh_db()

    result = evaluate_member(conn, "member_weight_01")
    ok("state is 'active'", result["state"] == "active", f"got {result['state']}")
    nudge = result.get("nudge", {})
    ok("nudge_type is 'weight_check_in'", nudge.get("nudge_type") == "weight_check_in")
    ok("confidence is 0.68", nudge.get("confidence") == 0.68, f"got {nudge.get('confidence')}")
    ok("matched_reason is 'missing_weight_log'", nudge.get("matched_reason") == "missing_weight_log")

    conn.close()


def test_catch_up_member():
    section("Scenario 2b: member_catchup_01 — no nudge needed")
    conn = fresh_db()

    result = evaluate_member(conn, "member_catchup_01")
    ok("state is 'no_nudge'", result["state"] == "no_nudge", f"got {result['state']}")
    ok("nudge is absent", result.get("nudge") is None)

    nudges = conn.execute(
        "SELECT COUNT(*) AS cnt FROM nudges WHERE member_id = ?",
        ("member_catchup_01",),
    ).fetchone()["cnt"]
    ok("no nudges persisted", nudges == 0, f"got {nudges}")

    conn.close()


def test_new_signal_supersedes_active_nudge():
    section("Fresh signal supersedes active nudge and re-evaluates state")
    conn = fresh_db()

    first_result = evaluate_member(conn, "member_weight_01")
    ok("first result is active", first_result["state"] == "active")
    active_nudge_id = first_result["nudge"]["id"]

    conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (_id(), "member_weight_01", "weight_logged", json.dumps({"weight_lb": 180.5}), _ts(_now())),
    )
    conn.commit()

    second_result = evaluate_member(conn, "member_weight_01")
    ok("fresh input clears the old recommendation", second_result["state"] == "no_nudge", f"got {second_result['state']}")

    stale_nudge = conn.execute("SELECT status FROM nudges WHERE id = ?", (active_nudge_id,)).fetchone()
    ok("stale active nudge marked superseded", stale_nudge and stale_nudge["status"] == "superseded")

    conn.close()


# ── Test 4: Scenario — member_support_01 (support risk → escalation) ────────

def test_support_risk():
    section("Scenario 3: member_support_01 — support risk escalation")
    conn = fresh_db()

    result = evaluate_member(conn, "member_support_01")
    ok("state is 'escalated'", result["state"] == "escalated", f"got {result['state']}")
    ok("nudge_id present", "nudge_id" in result)
    ok("escalation_id present", "escalation_id" in result)

    # Verify escalation row
    esc = conn.execute(
        "SELECT * FROM escalations WHERE id = ?", (result.get("escalation_id", ""),)
    ).fetchone()
    ok("escalation row exists", esc is not None)
    if esc:
        ok("escalation status is 'open'", esc["status"] == "open")
        ok("escalation source is 'rule_engine'", esc["source"] == "rule_engine")
        ok("escalation reason contains 'mood'", "mood" in (esc["reason"] or "").lower())

    # Verify nudge row is 'escalated'
    nudge = conn.execute(
        "SELECT * FROM nudges WHERE id = ?", (result.get("nudge_id", ""),)
    ).fetchone()
    ok("nudge status is 'escalated'", nudge and nudge["status"] == "escalated")
    ok("nudge confidence is 0.42", nudge and nudge["confidence"] == 0.42)

    nudge_audit = latest_audit_payload(conn, "nudge_generated", entity_id=result.get("nudge_id"))
    ok("nudge_generated audit exists for escalated nudge", nudge_audit is not None)
    if nudge_audit:
        ok("escalated audit stores support_risk type", nudge_audit["nudge_type"] == "support_risk")
        ok("escalated audit stores template phrasing", nudge_audit["phrasing_source"] == "template")

    escalation_audit = latest_audit_payload(conn, "escalation_created", entity_id=result.get("escalation_id"))
    ok("escalation_created audit recorded", escalation_audit is not None)
    if escalation_audit:
        ok("audit stores escalation source", escalation_audit["source"] == "rule_engine")
        ok("audit stores escalation status", escalation_audit["status"] == "open")
        ok("audit stores nudge_id", escalation_audit["nudge_id"] == result.get("nudge_id"))

    conn.close()


# ── Test 5: Priority — support_risk beats meal_guidance ──────────────────────

def test_priority_order():
    section("Priority: support_risk wins over meal_guidance")
    conn = fresh_db()

    # Make member_support_01 also qualify for meal_guidance by setting goal to low_carb
    # and adding a high-carb meal signal
    conn.execute("UPDATE members SET goal_type = 'low_carb' WHERE id = 'member_support_01'")
    from datetime import timedelta
    conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            _id(),
            "member_support_01",
            "meal_logged",
            json.dumps(
                {
                    "meal_profile": "higher_carb",
                }
            ),
            _ts(_now() - timedelta(hours=2)),
        ),
    )
    conn.commit()

    # Both support_risk and meal_guidance should match, but support_risk has priority 1
    candidate = select_nudge(conn, "member_support_01")
    ok("candidate is support_risk", candidate is not None and candidate.nudge_type == "support_risk",
       f"got {candidate.nudge_type if candidate else 'None'}")

    conn.close()


# ── Test 6: Cooldown — same nudge_type blocked for 24h after dismiss ────────

def test_cooldown():
    section("Cooldown: same nudge_type blocked after dismiss")
    conn = fresh_db()

    # Create and immediately dismiss a meal_guidance nudge for member_meal_01
    r1 = evaluate_member(conn, "member_meal_01")
    ok("first nudge is active", r1["state"] == "active")
    ok("first nudge is meal_guidance", r1["nudge"]["nudge_type"] == "meal_guidance")
    nudge_id = r1["nudge"]["id"]

    # Dismiss it
    conn.execute("UPDATE nudges SET status = 'dismissed' WHERE id = ?", (nudge_id,))
    conn.execute(
        "INSERT INTO nudge_actions (id, nudge_id, action_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (_id(), nudge_id, "dismiss", None, _ts(_now())),
    )
    conn.commit()

    # Re-evaluate: meal_guidance is on cooldown, so the next candidate wins (weight_check_in)
    r2 = evaluate_member(conn, "member_meal_01")
    ok("second nudge is NOT meal_guidance (cooldown blocks it)",
       r2["state"] == "active" and r2["nudge"]["nudge_type"] == "weight_check_in",
       f"got state={r2['state']}, type={r2.get('nudge', {}).get('nudge_type')}")

    conn.close()


# ── Test 7: Daily cap — 3rd nudge blocked (unless support_risk) ─────────────

def test_daily_cap():
    section("Daily cap: 3rd auto-delivered nudge blocked")
    conn = fresh_db()

    member = "member_meal_01"
    now = _now()

    # Insert 2 fake nudges created today to fill the cap
    for i in range(2):
        conn.execute(
            """INSERT INTO nudges
               (id, member_id, nudge_type, content, explanation, matched_reason,
                confidence, escalation_recommended, status, generated_by, phrasing_source,
                created_at, delivered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_id(), member, "weight_check_in", None, "test", "test",
             0.68, 0, "acted", "rule_engine", "template",
             _ts(now), _ts(now)),
        )
    conn.commit()

    # meal_guidance candidate should be blocked by daily cap
    candidate = select_nudge(conn, member)
    ok("no candidate due to daily cap", candidate is None, f"got {candidate}")

    conn.close()


# ── Test 8: Support-risk bypasses cap and cooldown ──────────────────────────

def test_support_risk_bypass():
    section("Support-risk bypasses cooldown and daily cap")
    conn = fresh_db()

    member = "member_support_01"
    now = _now()

    # Fill daily cap with 2 nudges
    for i in range(2):
        conn.execute(
            """INSERT INTO nudges
               (id, member_id, nudge_type, content, explanation, matched_reason,
                confidence, escalation_recommended, status, generated_by, phrasing_source,
                created_at, delivered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_id(), member, "weight_check_in", None, "test", "test",
             0.68, 0, "acted", "rule_engine", "template",
             _ts(now), _ts(now)),
        )
    conn.commit()

    # support_risk should still match despite daily cap
    candidate = select_nudge(conn, member)
    ok("support_risk bypasses daily cap", candidate is not None and candidate.nudge_type == "support_risk",
       f"got {candidate.nudge_type if candidate else 'None'}")

    conn.close()


# ── Test 9: Evaluator unit checks ───────────────────────────────────────────

def test_evaluator_units():
    section("Evaluator unit checks")
    conn = fresh_db()

    # check_meal_goal_mismatch should return candidate for member_meal_01
    c1 = check_meal_goal_mismatch(conn, "member_meal_01")
    ok("meal mismatch fires for member_meal_01", c1 is not None)
    ok("meal mismatch: has source_signal_ids", c1 is not None and len(c1.source_signal_ids) > 0)

    # check_meal_goal_mismatch should NOT fire for non-low_carb member
    c2 = check_meal_goal_mismatch(conn, "member_weight_01")
    ok("meal mismatch does NOT fire for weight_loss goal", c2 is None)

    # check_missing_weight_log should fire for member_weight_01
    c3 = check_missing_weight_log(conn, "member_weight_01")
    ok("missing weight fires for member_weight_01", c3 is not None)

    # check_missing_weight_log should NOT fire for member with no weight signals but also no expectation
    # member_meal_01 has no weight signal — but that means they haven't logged at all in 4 days, so it SHOULD fire
    c4 = check_missing_weight_log(conn, "member_meal_01")
    ok("missing weight fires for member_meal_01 (never logged)", c4 is not None)

    c4b = check_missing_weight_log(conn, "member_catchup_01")
    ok("missing weight does NOT fire for member_catchup_01", c4b is None)

    # check_support_risk should fire for member_support_01
    c5 = check_support_risk(conn, "member_support_01")
    ok("support risk fires for member_support_01", c5 is not None)
    ok("support risk: escalation_recommended", c5 is not None and c5.escalation_recommended)

    # check_support_risk should NOT fire for member without mood/dismissals
    c6 = check_support_risk(conn, "member_meal_01")
    ok("support risk does NOT fire for member_meal_01", c6 is None)

    conn.close()


def test_meal_log_without_meal_profile_is_ignored():
    section("Meal payload without meal profile does not trigger guidance")
    conn = fresh_db()

    conn.execute("UPDATE members SET goal_type = 'low_carb' WHERE id = 'member_weight_01'")
    conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            _id(),
            "member_weight_01",
            "meal_logged",
            json.dumps({"visible_food_summary": "The photo appears to show a plated meal."}),
            _ts(_now()),
        ),
    )
    conn.commit()

    candidate = check_meal_goal_mismatch(conn, "member_weight_01")
    ok("meal without meal profile does not trigger guidance", candidate is None)

    conn.close()


def test_one_step_meal_input_is_trusted():
    section("One-step meal log is trusted for guidance")
    conn = fresh_db()

    conn.execute("UPDATE members SET goal_type = 'low_carb' WHERE id = 'member_weight_01'")
    conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            _id(),
            "member_weight_01",
            "meal_logged",
            json.dumps(
                {
                    "meal_profile": "higher_carb",
                    "visible_food_summary": "The photo appears to show a pasta dish with bread.",
                }
            ),
            _ts(_now()),
        ),
    )
    conn.commit()

    candidate = check_meal_goal_mismatch(conn, "member_weight_01")
    ok("one-step meal triggers guidance", candidate is not None)
    ok(
        "one-step explanation uses meal profile",
        candidate is not None and "higher carb" in candidate.explanation_basis,
        f"got {candidate.explanation_basis if candidate else 'None'}",
    )

    conn.close()


def test_llm_success_upgrade():
    section("Phase 6: successful LLM phrasing upgrades active nudge")
    conn = fresh_db()
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
        result = evaluate_member(conn, "member_meal_01")

    ok("state is active", result["state"] == "active")
    nudge = result["nudge"]
    ok("phrasing source is llm", nudge["phrasing_source"] == "llm", f"got {nudge['phrasing_source']}")
    ok("content updated from llm", "tonight" in (nudge["content"] or ""), f"got {nudge['content']!r}")

    events = conn.execute(
        "SELECT event_type, payload_json FROM audit_events ORDER BY created_at ASC"
    ).fetchall()
    ok("one llm_call event recorded", len([e for e in events if e["event_type"] == "llm_call"]) == 1)
    ok("no llm_fallback event recorded", len([e for e in events if e["event_type"] == "llm_fallback"]) == 0)

    llm_call_audit = latest_audit_payload(conn, "llm_call", entity_id=nudge["id"])
    ok("llm_call audit recorded", llm_call_audit is not None)
    if llm_call_audit:
        ok("llm_call prompt_area is phrasing", llm_call_audit["prompt_area"] == "phrasing", f"got {llm_call_audit['prompt_area']}")
        ok("llm_call model_name recorded", llm_call_audit["model_name"] == model_name, f"got {llm_call_audit['model_name']}")

    nudge_audit = latest_audit_payload(conn, "nudge_generated", entity_id=nudge["id"])
    ok("nudge_generated audit reflects llm phrasing", nudge_audit is not None)
    if nudge_audit:
        ok("audit phrasing_source upgraded to llm", nudge_audit["phrasing_source"] == "llm")
        ok("nudge_generated llm_model_name recorded", nudge_audit["llm_model_name"] == model_name, f"got {nudge_audit.get('llm_model_name')}")

    conn.close()


def test_missing_key_fallback_audit():
    section("Phase 6: missing API key falls back to template")
    conn = fresh_db()

    result = evaluate_member(conn, "member_meal_01")
    ok("state is active", result["state"] == "active")
    ok("phrasing source remains template", result["nudge"]["phrasing_source"] == "template")

    fallback = conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    ok("llm_fallback event recorded", fallback is not None)
    if fallback:
        payload = json.loads(fallback["payload_json"])
        ok("fallback reason is missing_key", payload["fallback_reason"] == "missing_key", f"got {payload['fallback_reason']}")
        ok("fallback prompt_area is phrasing", payload["prompt_area"] == "phrasing", f"got {payload['prompt_area']}")
        ok("fallback model_name recorded", payload["model_name"] == OPENAI_MODEL, f"got {payload['model_name']}")

    conn.close()


def test_llm_invalid_json_fallback():
    section("Phase 6: invalid JSON falls back to templates")
    conn = fresh_db()
    model_name = "gpt-5.4-test-invalid-json"

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        return_value=("not-json", model_name),
    ):
        result = evaluate_member(conn, "member_meal_01")

    ok("phrasing source remains template", result["nudge"]["phrasing_source"] == "template")
    fallback = conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    ok("llm_fallback event recorded", fallback is not None)
    if fallback:
        payload = json.loads(fallback["payload_json"])
        ok("fallback reason is invalid_json", payload["fallback_reason"] == "invalid_json", f"got {payload['fallback_reason']}")
        ok("fallback model_name recorded", payload["model_name"] == model_name, f"got {payload['model_name']}")

    conn.close()


def test_llm_timeout_fallback():
    section("Phase 6: timeout falls back to templates")
    conn = fresh_db()

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=httpx.TimeoutException("timed out"),
    ):
        result = evaluate_member(conn, "member_meal_01")

    ok("phrasing source remains template", result["nudge"]["phrasing_source"] == "template")
    fallback = conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    ok("llm_fallback event recorded", fallback is not None)
    if fallback:
        payload = json.loads(fallback["payload_json"])
        ok("fallback reason is timeout", payload["fallback_reason"] == "timeout", f"got {payload['fallback_reason']}")
        ok("fallback model_name recorded", payload["model_name"] == OPENAI_MODEL, f"got {payload['model_name']}")

    conn.close()


def test_validation_failure_fallback():
    section("Phase 6: blocked terms are rejected before persistence")
    conn = fresh_db()
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
        result = evaluate_member(conn, "member_meal_01")

    ok("phrasing source remains template", result["nudge"]["phrasing_source"] == "template")
    ok(
        "template content preserved",
        result["nudge"]["content"] == "Try a lighter, lower-carb dinner to balance today's earlier meal.",
        f"got {result['nudge']['content']!r}",
    )

    fallback = conn.execute(
        "SELECT payload_json FROM audit_events WHERE event_type = 'llm_fallback' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    ok("llm_fallback event recorded", fallback is not None)
    if fallback:
        payload = json.loads(fallback["payload_json"])
        ok(
            "fallback reason is validation_failure",
            payload["fallback_reason"] == "validation_failure",
            f"got {payload['fallback_reason']}",
        )
        ok("fallback model_name recorded", payload["model_name"] == model_name, f"got {payload['model_name']}")

    conn.close()


def test_existing_active_nudge_skips_rephrase():
    section("Phase 6: repeated reads do not re-trigger LLM phrasing")
    conn = fresh_db()
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
        first = evaluate_member(conn, "member_meal_01")
        second = evaluate_member(conn, "member_meal_01")

    ok("only one LLM call made", calls["count"] == 1, f"got {calls['count']}")
    ok("same nudge returned on second read", first["nudge"]["id"] == second["nudge"]["id"])
    ok("second read preserves llm phrasing source", second["nudge"]["phrasing_source"] == "llm")

    conn.close()


def test_support_risk_skips_llm():
    section("Phase 6: escalated support-risk path skips LLM phrasing")
    conn = fresh_db()

    with patch("app.phrasing.get_openai_api_key", return_value="test-key"), patch(
        "app.phrasing._request_llm_json",
        side_effect=AssertionError("LLM should not run for escalations"),
    ):
        result = evaluate_member(conn, "member_support_01")

    ok("state is escalated", result["state"] == "escalated")
    llm_events = conn.execute(
        "SELECT COUNT(*) AS cnt FROM audit_events WHERE event_type IN ('llm_call', 'llm_fallback')"
    ).fetchone()["cnt"]
    ok("no llm audit events recorded", llm_events == 0, f"got {llm_events}")

    conn.close()


def test_phrasing_output_validation():
    section("Phase 6: phrasing output validation enforces limits and blocked terms")

    ok(
        "valid phrasing output accepted",
        PhrasingOutput.model_validate(
            {
                "content": "Take a quick weight check-in when you have a minute.",
                "explanation": "You have not logged weight in the last few days.",
            }
        ).content.startswith("Take a quick weight check-in"),
    )

    try:
        PhrasingOutput.model_validate(
            {
                "content": "x" * 161,
                "explanation": "short explanation",
            }
        )
        ok("overlong content rejected", False, "validation unexpectedly passed")
    except ValidationError:
        ok("overlong content rejected", True)

    try:
        PhrasingOutput.model_validate(
            {
                "content": "This might diagnose a problem.",
                "explanation": "Please follow a treatment plan.",
            }
        )
        ok("blocked terms rejected", False, "validation unexpectedly passed")
    except ValidationError:
        ok("blocked terms rejected", True)


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_evaluator_units()
    test_meal_log_without_meal_profile_is_ignored()
    test_one_step_meal_input_is_trusted()
    test_meal_mismatch()
    test_idempotency()
    test_missing_weight()
    test_catch_up_member()
    test_new_signal_supersedes_active_nudge()
    test_support_risk()
    test_priority_order()
    test_cooldown()
    test_daily_cap()
    test_support_risk_bypass()
    test_llm_success_upgrade()
    test_missing_key_fallback_audit()
    test_llm_invalid_json_fallback()
    test_llm_timeout_fallback()
    test_validation_failure_fallback()
    test_existing_active_nudge_skips_rephrase()
    test_support_risk_skips_llm()
    test_phrasing_output_validation()

    print(f"\n{'═' * 60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print(f"{'═' * 60}")
    sys.exit(1 if FAIL else 0)

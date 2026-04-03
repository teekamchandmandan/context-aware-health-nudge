"""Verification tests for the Phase 2 decision engine."""

import json
import sqlite3
import sys
from pathlib import Path

# Ensure the server package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
        (_id(), "member_support_01", "meal_logged",
         json.dumps({"meal": "Pizza", "carbs_g": 95}),
         _ts(_now() - timedelta(hours=2))),
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

    # check_support_risk should fire for member_support_01
    c5 = check_support_risk(conn, "member_support_01")
    ok("support risk fires for member_support_01", c5 is not None)
    ok("support risk: escalation_recommended", c5 is not None and c5.escalation_recommended)

    # check_support_risk should NOT fire for member without mood/dismissals
    c6 = check_support_risk(conn, "member_meal_01")
    ok("support risk does NOT fire for member_meal_01", c6 is None)

    conn.close()


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_evaluator_units()
    test_meal_mismatch()
    test_idempotency()
    test_missing_weight()
    test_support_risk()
    test_priority_order()
    test_cooldown()
    test_daily_cap()
    test_support_risk_bypass()

    print(f"\n{'═' * 60}")
    print(f"Results: {PASS} passed, {FAIL} failed")
    print(f"{'═' * 60}")
    sys.exit(1 if FAIL else 0)

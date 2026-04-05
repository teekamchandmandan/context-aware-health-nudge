import json
from datetime import timedelta

from app.engine import _id, _now, _ts, evaluate_member, select_nudge

from .engine_support import latest_audit_payload


def test_meal_mismatch(db_conn):
    result = evaluate_member(db_conn, "member_meal_01")
    assert result["state"] == "active"

    nudge = result["nudge"]
    assert nudge["nudge_type"] == "meal_guidance"
    assert 0.70 <= nudge["confidence"] <= 0.95, f"meal confidence {nudge['confidence']} out of expected range"
    assert nudge["matched_reason"] == "meal_goal_mismatch"
    assert nudge["delivered_at"] is not None
    assert nudge["status"] == "active"

    audit_payload = latest_audit_payload(db_conn, "nudge_generated", entity_id=nudge["id"])
    assert audit_payload is not None
    assert audit_payload["member_id"] == "member_meal_01"
    assert audit_payload["nudge_id"] == nudge["id"]
    assert 0.70 <= audit_payload["confidence"] <= 0.95
    assert audit_payload["phrasing_source"] == "template"


def test_idempotency(db_conn):
    first_result = evaluate_member(db_conn, "member_meal_01")
    second_result = evaluate_member(db_conn, "member_meal_01")

    assert first_result["state"] == "active"
    assert second_result["state"] == "active"
    assert first_result["nudge"]["id"] == second_result["nudge"]["id"]

    count = db_conn.execute(
        "SELECT COUNT(*) as cnt FROM nudges WHERE member_id = 'member_meal_01' AND status = 'active'"
    ).fetchone()["cnt"]
    assert count == 1


def test_missing_weight(db_conn):
    result = evaluate_member(db_conn, "member_weight_01")
    assert result["state"] == "active"
    assert result["nudge"]["nudge_type"] == "weight_check_in"
    assert 0.50 <= result["nudge"]["confidence"] <= 0.80, f"weight confidence {result['nudge']['confidence']} out of expected range"
    assert result["nudge"]["matched_reason"] == "missing_weight_log"


def test_catch_up_member(db_conn):
    result = evaluate_member(db_conn, "member_catchup_01")
    assert result["state"] == "no_nudge"
    assert result.get("nudge") is None

    nudges = db_conn.execute(
        "SELECT COUNT(*) AS cnt FROM nudges WHERE member_id = ?",
        ("member_catchup_01",),
    ).fetchone()["cnt"]
    assert nudges == 0


def test_new_signal_supersedes_active_nudge(db_conn):
    first_result = evaluate_member(db_conn, "member_weight_01")
    assert first_result["state"] == "active"
    active_nudge_id = first_result["nudge"]["id"]

    db_conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (_id(), "member_weight_01", "weight_logged", json.dumps({"weight_lb": 180.5}), _ts(_now())),
    )
    db_conn.commit()

    second_result = evaluate_member(db_conn, "member_weight_01")
    assert second_result["state"] == "no_nudge"

    stale_nudge = db_conn.execute("SELECT status FROM nudges WHERE id = ?", (active_nudge_id,)).fetchone()
    assert stale_nudge is not None
    assert stale_nudge["status"] == "superseded"


def test_support_risk(db_conn):
    result = evaluate_member(db_conn, "member_support_01")
    assert result["state"] == "escalated"
    assert "nudge_id" in result
    assert "escalation_id" in result

    esc = db_conn.execute(
        "SELECT * FROM escalations WHERE id = ?", (result.get("escalation_id", ""),)
    ).fetchone()
    assert esc is not None
    assert esc["status"] == "open"
    assert esc["source"] == "rule_engine"
    assert "mood" in (esc["reason"] or "").lower()

    nudge = db_conn.execute(
        "SELECT * FROM nudges WHERE id = ?", (result.get("nudge_id", ""),)
    ).fetchone()
    assert nudge is not None
    assert nudge["status"] == "escalated"
    assert nudge["confidence"] < 0.50, f"support_risk confidence {nudge['confidence']} should be below automation threshold"

    assert nudge["matched_reason"] == "support_risk", (
        f"expected dismiss-based path but got {nudge['matched_reason']}"
    )

    nudge_audit = latest_audit_payload(db_conn, "nudge_generated", entity_id=result.get("nudge_id"))
    assert nudge_audit is not None
    assert nudge_audit["nudge_type"] == "support_risk"
    assert nudge_audit["phrasing_source"] == "template"

    escalation_audit = latest_audit_payload(db_conn, "escalation_created", entity_id=result.get("escalation_id"))
    assert escalation_audit is not None
    assert escalation_audit["source"] == "rule_engine"
    assert escalation_audit["status"] == "open"
    assert escalation_audit["nudge_id"] == result.get("nudge_id")


def test_priority_order(db_conn):
    db_conn.execute("UPDATE members SET goal_type = 'low_carb' WHERE id = 'member_support_01'")
    db_conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            _id(),
            "member_support_01",
            "meal_logged",
            json.dumps({"meal_profile": "higher_carb"}),
            _ts(_now() - timedelta(hours=2)),
        ),
    )
    db_conn.commit()

    candidate = select_nudge(db_conn, "member_support_01")
    assert candidate is not None
    assert candidate.nudge_type == "support_risk"


def test_cooldown(db_conn):
    first_result = evaluate_member(db_conn, "member_meal_01")
    assert first_result["state"] == "active"
    assert first_result["nudge"]["nudge_type"] == "meal_guidance"
    nudge_id = first_result["nudge"]["id"]

    db_conn.execute("UPDATE nudges SET status = 'dismissed' WHERE id = ?", (nudge_id,))
    db_conn.execute(
        "INSERT INTO nudge_actions (id, nudge_id, action_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (_id(), nudge_id, "dismiss", None, _ts(_now())),
    )
    db_conn.commit()

    second_result = evaluate_member(db_conn, "member_meal_01")
    assert second_result["state"] == "active"
    assert second_result["nudge"]["nudge_type"] == "weight_check_in"


def test_repeated_low_mood_triggers_escalation(db_conn):
    """3+ low mood signals in the lookback window trigger an escalation
    even without any dismiss history."""
    member = "member_catchup_01"
    for hours_ago in (40, 20, 2):
        db_conn.execute(
            "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (_id(), member, "mood_logged", json.dumps({"mood": "low"}), _ts(_now() - timedelta(hours=hours_ago))),
        )
    db_conn.commit()

    result = evaluate_member(db_conn, member)
    assert result["state"] == "escalated"
    assert "nudge_id" in result
    assert "escalation_id" in result

    nudge = db_conn.execute("SELECT * FROM nudges WHERE id = ?", (result["nudge_id"],)).fetchone()
    assert nudge["nudge_type"] == "support_risk"
    assert nudge["matched_reason"] == "repeated_low_mood"
    assert nudge["status"] == "escalated"
    assert nudge["confidence"] < 0.50

    esc = db_conn.execute("SELECT * FROM escalations WHERE id = ?", (result["escalation_id"],)).fetchone()
    assert esc["status"] == "open"
    assert "mood" in esc["reason"].lower()


def test_repeated_low_mood_below_threshold(db_conn):
    """Fewer than 3 low mood signals should NOT trigger a repeated_low_mood nudge."""
    member = "member_catchup_01"
    for hours_ago in (20, 2):
        db_conn.execute(
            "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (_id(), member, "mood_logged", json.dumps({"mood": "low"}), _ts(_now() - timedelta(hours=hours_ago))),
        )
    db_conn.commit()

    result = evaluate_member(db_conn, member)
    assert result["state"] == "no_nudge"


def test_repeated_low_mood_ignores_non_low(db_conn):
    """Only 'low' moods count toward the threshold; high/neutral are excluded."""
    member = "member_catchup_01"
    moods = [("low", 40), ("high", 30), ("low", 20), ("neutral", 10), ("low", 1)]
    for mood, hours_ago in moods:
        db_conn.execute(
            "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (_id(), member, "mood_logged", json.dumps({"mood": mood}), _ts(_now() - timedelta(hours=hours_ago))),
        )
    db_conn.commit()

    result = evaluate_member(db_conn, member)
    assert result["state"] == "escalated"
    nudge = db_conn.execute("SELECT * FROM nudges WHERE id = ?", (result["nudge_id"],)).fetchone()
    assert nudge["matched_reason"] == "repeated_low_mood"


def test_repeated_low_mood_bypasses_fatigue(db_conn):
    """Repeated low mood escalation should ignore daily cap."""
    member = "member_catchup_01"
    # Create 2 nudges today to hit the daily cap
    for i in range(2):
        db_conn.execute(
            """INSERT INTO nudges (id, member_id, nudge_type, content, explanation, matched_reason,
               confidence, escalation_recommended, status, generated_by, phrasing_source,
               created_at, delivered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_id(), member, "weight_check_in", "content", "explanation", "missing_weight_log",
             0.55, 0, "active", "rule_engine", "template", _ts(_now() - timedelta(hours=i + 1)),
             _ts(_now() - timedelta(hours=i + 1))),
        )
    # Add 3 low moods
    for hours_ago in (40, 20, 1):
        db_conn.execute(
            "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (_id(), member, "mood_logged", json.dumps({"mood": "low"}), _ts(_now() - timedelta(hours=hours_ago))),
        )
    db_conn.commit()

    result = evaluate_member(db_conn, member)
    assert result["state"] == "escalated"
    nudge = db_conn.execute("SELECT * FROM nudges WHERE id = ?", (result["nudge_id"],)).fetchone()
    assert nudge["matched_reason"] == "repeated_low_mood"


def test_escalation_idempotency(db_conn):
    """Calling evaluate_member multiple times for an escalated member must not create duplicates."""
    member = "member_catchup_01"
    for hours_ago in (40, 20, 2):
        db_conn.execute(
            "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (_id(), member, "mood_logged", json.dumps({"mood": "low"}), _ts(_now() - timedelta(hours=hours_ago))),
        )
    db_conn.commit()

    first = evaluate_member(db_conn, member)
    assert first["state"] == "escalated"

    second = evaluate_member(db_conn, member)
    assert second["state"] == "escalated"
    assert second["nudge_id"] == first["nudge_id"]
    assert second["escalation_id"] == first["escalation_id"]

    esc_count = db_conn.execute(
        "SELECT COUNT(*) as cnt FROM escalations WHERE member_id = ?", (member,)
    ).fetchone()["cnt"]
    assert esc_count == 1


def test_daily_cap(db_conn):
    member = "member_meal_01"
    now = _now()

    for _ in range(2):
        db_conn.execute(
            """INSERT INTO nudges
               (id, member_id, nudge_type, content, explanation, matched_reason,
                confidence, escalation_recommended, status, generated_by, phrasing_source,
                created_at, delivered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_id(), member, "weight_check_in", None, "test", "test", 0.68, 0, "acted", "rule_engine", "template", _ts(now), _ts(now)),
        )
    db_conn.commit()

    candidate = select_nudge(db_conn, member)
    assert candidate is None


def test_support_risk_bypass(db_conn):
    member = "member_support_01"
    now = _now()

    for _ in range(2):
        db_conn.execute(
            """INSERT INTO nudges
               (id, member_id, nudge_type, content, explanation, matched_reason,
                confidence, escalation_recommended, status, generated_by, phrasing_source,
                created_at, delivered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_id(), member, "weight_check_in", None, "test", "test", 0.68, 0, "acted", "rule_engine", "template", _ts(now), _ts(now)),
        )
    db_conn.commit()

    candidate = select_nudge(db_conn, member)
    assert candidate is not None
    assert candidate.nudge_type == "support_risk"

"""Decision engine: deterministic nudge selection with evaluators, fatigue, and escalation."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import BaseModel


# ── Constants ────────────────────────────────────────────────────────────────

CONFIDENCE_LOW_THRESHOLD = 0.50
COOLDOWN_HOURS = 24
DAILY_CAP = 2
MISSING_WEIGHT_DAYS = 4
MEAL_CARB_THRESHOLD = 60
MEAL_LOOKBACK_HOURS = 24
MOOD_LOOKBACK_DAYS = 3
DISMISS_LOOKBACK_DAYS = 7

PRIORITY = {
    "support_risk": 1,
    "meal_guidance": 2,
    "weight_check_in": 3,
}

TEMPLATE_CONTENT: dict[str, str | None] = {
    "meal_guidance": "Consider a lighter, lower-carb option for your next meal.",
    "weight_check_in": "It's been a few days since your last weigh-in — a quick check-in helps track your progress.",
    "support_risk": None,  # not member-facing; escalated
}


# ── Candidate Model ─────────────────────────────────────────────────────────


class NudgeCandidate(BaseModel):
    nudge_type: str
    matched_reason: str
    explanation_basis: str
    confidence: float
    escalation_recommended: bool
    source_signal_ids: list[str]
    priority: int
    latest_signal_ts: str = ""  # ISO 8601 UTC; used for tie-break on recency


# ── Helpers ──────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _id() -> str:
    return uuid4().hex


# ── Evaluator Functions ──────────────────────────────────────────────────────


def check_meal_goal_mismatch(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    """Trigger: member goal is low_carb and most recent meal in last 24h has carbs_g >= 60."""
    row = conn.execute(
        "SELECT goal_type FROM members WHERE id = ?", (member_id,)
    ).fetchone()
    if not row or row["goal_type"] != "low_carb":
        return None

    cutoff = _ts(_now() - timedelta(hours=MEAL_LOOKBACK_HOURS))
    signal = conn.execute(
        """SELECT id, payload_json, created_at FROM signals
           WHERE member_id = ? AND signal_type = 'meal_logged' AND created_at >= ?
           ORDER BY created_at DESC LIMIT 1""",
        (member_id, cutoff),
    ).fetchone()
    if not signal:
        return None

    payload = json.loads(signal["payload_json"])
    carbs = payload.get("carbs_g", 0)
    if carbs < MEAL_CARB_THRESHOLD:
        return None

    meal_name = payload.get("meal", "Recent meal")
    return NudgeCandidate(
        nudge_type="meal_guidance",
        matched_reason="meal_goal_mismatch",
        explanation_basis=f"{meal_name} logged {carbs}g carbs; goal is low_carb (<{MEAL_CARB_THRESHOLD}g)",
        confidence=0.86,
        escalation_recommended=False,
        source_signal_ids=[signal["id"]],
        priority=PRIORITY["meal_guidance"],
        latest_signal_ts=signal["created_at"],
    )


def check_missing_weight_log(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    """Trigger: no weight_logged signal in the last 4 full UTC days."""
    now = _now()
    # Start of today minus 4 days gives the cutoff
    cutoff_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=MISSING_WEIGHT_DAYS)
    cutoff = _ts(cutoff_dt)

    signal = conn.execute(
        """SELECT id FROM signals
           WHERE member_id = ? AND signal_type = 'weight_logged' AND created_at >= ?
           LIMIT 1""",
        (member_id, cutoff),
    ).fetchone()
    if signal:
        return None  # Weight was logged recently enough

    return NudgeCandidate(
        nudge_type="weight_check_in",
        matched_reason="missing_weight_log",
        explanation_basis=f"No weight logged in the last {MISSING_WEIGHT_DAYS} days",
        confidence=0.68,
        escalation_recommended=False,
        source_signal_ids=[],
        priority=PRIORITY["weight_check_in"],
    )


def check_support_risk(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    """Trigger: mood_logged with mood=='low' in last 3 days AND >= 2 dismiss actions in last 7 days."""
    now = _now()
    mood_cutoff = _ts(now - timedelta(days=MOOD_LOOKBACK_DAYS))
    dismiss_cutoff = _ts(now - timedelta(days=DISMISS_LOOKBACK_DAYS))

    mood_signal = conn.execute(
        """SELECT id, payload_json, created_at FROM signals
           WHERE member_id = ? AND signal_type = 'mood_logged' AND created_at >= ?
           ORDER BY created_at DESC LIMIT 1""",
        (member_id, mood_cutoff),
    ).fetchone()
    if not mood_signal:
        return None

    payload = json.loads(mood_signal["payload_json"])
    if payload.get("mood") != "low":
        return None

    dismiss_count = conn.execute(
        """SELECT COUNT(*) as cnt FROM nudge_actions na
           JOIN nudges n ON na.nudge_id = n.id
           WHERE n.member_id = ? AND na.action_type = 'dismiss' AND na.created_at >= ?""",
        (member_id, dismiss_cutoff),
    ).fetchone()["cnt"]

    if dismiss_count < 2:
        return None

    return NudgeCandidate(
        nudge_type="support_risk",
        matched_reason="support_risk",
        explanation_basis=f"Low mood reported; {dismiss_count} nudges dismissed in last {DISMISS_LOOKBACK_DAYS} days",
        confidence=0.42,
        escalation_recommended=True,
        source_signal_ids=[mood_signal["id"]],
        priority=PRIORITY["support_risk"],
        latest_signal_ts=mood_signal["created_at"],
    )


# ── Fatigue and Deduplication ────────────────────────────────────────────────


def get_active_nudge(conn: sqlite3.Connection, member_id: str) -> sqlite3.Row | None:
    """Return the existing active nudge for a member, or None."""
    return conn.execute(
        "SELECT * FROM nudges WHERE member_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
        (member_id,),
    ).fetchone()


def _has_newer_signal(conn: sqlite3.Connection, member_id: str, created_at: str) -> bool:
    """Return True when a newer member signal exists after the active nudge was created."""
    row = conn.execute(
        "SELECT 1 FROM signals WHERE member_id = ? AND created_at > ? LIMIT 1",
        (member_id, created_at),
    ).fetchone()
    return row is not None


def _supersede_active_nudge(conn: sqlite3.Connection, nudge_id: str) -> None:
    """Mark an outdated active nudge as superseded so fresh context can be re-evaluated."""
    conn.execute(
        "UPDATE nudges SET status = 'superseded' WHERE id = ?",
        (nudge_id,),
    )


def _check_cooldown(conn: sqlite3.Connection, member_id: str, nudge_type: str) -> bool:
    """Return True if same nudge_type had act_now/dismiss within the cooldown window."""
    cutoff = _ts(_now() - timedelta(hours=COOLDOWN_HOURS))
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM nudge_actions na
           JOIN nudges n ON na.nudge_id = n.id
           WHERE n.member_id = ? AND n.nudge_type = ?
             AND na.action_type IN ('act_now', 'dismiss')
             AND na.created_at >= ?""",
        (member_id, nudge_type, cutoff),
    ).fetchone()
    return row["cnt"] > 0


def _count_today_nudges(conn: sqlite3.Connection, member_id: str) -> int:
    """Count nudges auto-delivered (status active, acted, or dismissed) today UTC."""
    today_start = _ts(_now().replace(hour=0, minute=0, second=0, microsecond=0))
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM nudges
           WHERE member_id = ? AND created_at >= ?
             AND status IN ('active', 'acted', 'dismissed')""",
        (member_id, today_start),
    ).fetchone()
    return row["cnt"]


def _apply_fatigue(
    conn: sqlite3.Connection, member_id: str, candidates: list[NudgeCandidate]
) -> list[NudgeCandidate]:
    """Filter out candidates blocked by cooldown or daily cap. Support-risk bypasses both."""
    today_count = _count_today_nudges(conn, member_id)
    result = []
    for c in candidates:
        if c.nudge_type == "support_risk":
            result.append(c)
            continue
        if _check_cooldown(conn, member_id, c.nudge_type):
            continue
        if today_count >= DAILY_CAP:
            continue
        result.append(c)
    return result


# ── Selection ────────────────────────────────────────────────────────────────

ALL_EVALUATORS = [
    check_meal_goal_mismatch,
    check_missing_weight_log,
    check_support_risk,
]


def select_nudge(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    """Run evaluators, apply fatigue, return the best candidate or None."""
    candidates = []
    for evaluator in ALL_EVALUATORS:
        candidate = evaluator(conn, member_id)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return None

    candidates = _apply_fatigue(conn, member_id, candidates)
    if not candidates:
        return None

    # Sort: priority ASC, confidence DESC, most recent signal DESC (spec tie-break).
    # Two-pass stable sort: first by recency DESC, then by (priority, confidence).
    # Python's stable sort preserves recency ordering within equal primary keys.
    candidates.sort(key=lambda c: c.latest_signal_ts, reverse=True)
    candidates.sort(key=lambda c: (c.priority, -c.confidence))
    return candidates[0]


# ── Persistence & Escalation ─────────────────────────────────────────────────


def _create_nudge_row(
    conn: sqlite3.Connection, member_id: str, candidate: NudgeCandidate, status: str
) -> str:
    """Insert a nudge row and return its ID."""
    nudge_id = _id()
    now = _now()
    delivered_at = _ts(now) if status == "active" else None
    content = TEMPLATE_CONTENT.get(candidate.nudge_type) if status == "active" else None
    conn.execute(
        """INSERT INTO nudges
           (id, member_id, nudge_type, content, explanation, matched_reason,
            confidence, escalation_recommended, status, generated_by, phrasing_source,
            created_at, delivered_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            nudge_id,
            member_id,
            candidate.nudge_type,
            content,
            candidate.explanation_basis,
            candidate.matched_reason,
            candidate.confidence,
            1 if candidate.escalation_recommended else 0,
            status,
            "rule_engine",
            "template",
            _ts(now),
            delivered_at,
        ),
    )
    return nudge_id


def _create_escalation(
    conn: sqlite3.Connection, member_id: str, nudge_id: str, reason: str
) -> str:
    """Insert an escalation row and return its ID."""
    esc_id = _id()
    conn.execute(
        """INSERT INTO escalations (id, nudge_id, member_id, reason, source, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (esc_id, nudge_id, member_id, reason, "rule_engine", "open", _ts(_now())),
    )
    return esc_id


def create_nudge_from_candidate(
    conn: sqlite3.Connection, member_id: str, candidate: NudgeCandidate
) -> dict:
    """Persist a nudge (and escalation if needed). Returns result dict."""
    if candidate.confidence < CONFIDENCE_LOW_THRESHOLD or candidate.escalation_recommended:
        nudge_id = _create_nudge_row(conn, member_id, candidate, "escalated")
        esc_id = _create_escalation(conn, member_id, nudge_id, candidate.explanation_basis)
        return {"state": "escalated", "nudge_id": nudge_id, "escalation_id": esc_id}
    else:
        nudge_id = _create_nudge_row(conn, member_id, candidate, "active")
        nudge = conn.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()
        return {"state": "active", "nudge": dict(nudge)}


# ── Top-Level Entry Point ───────────────────────────────────────────────────


def evaluate_member(conn: sqlite3.Connection, member_id: str) -> dict:
    """Evaluate a member and return the nudge decision.

    Returns a dict with:
      - {"state": "active", "nudge": {...}}        — active nudge (existing or new)
      - {"state": "escalated", "nudge_id": ..., "escalation_id": ...} — low-confidence escalation
      - {"state": "no_nudge"}                       — nothing to show
    """
    # Idempotent unless newer member input arrived after the nudge was created.
    existing = get_active_nudge(conn, member_id)
    if existing:
        if not _has_newer_signal(conn, member_id, existing["created_at"]):
            return {"state": "active", "nudge": dict(existing)}

        _supersede_active_nudge(conn, existing["id"])

    candidate = select_nudge(conn, member_id)
    if not candidate:
        conn.commit()
        return {"state": "no_nudge"}

    result = create_nudge_from_candidate(conn, member_id, candidate)
    conn.commit()
    return result

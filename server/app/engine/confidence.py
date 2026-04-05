"""Computed confidence scoring for nudge candidates.

Each scorer starts from a base score reflecting the inherent reliability of the
rule type, then applies bounded adjustments from observable evidence: recency,
classification clarity, overdue severity, member engagement, and dismissal
patterns.  Every adjustment is recorded as a named factor so coaches and auditors
can inspect *why* a score landed where it did.
"""

from __future__ import annotations

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 2)))


def _hours_since(ts: str) -> float:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 3600)


# ---------------------------------------------------------------------------
# Meal guidance
# ---------------------------------------------------------------------------

def score_meal_guidance(
    *,
    signal_ts: str,
    meal_profile: str,
    lookback_hours: float = 24.0,
) -> tuple[float, list[dict]]:
    """Confidence for a meal-guidance candidate.

    Factors:
      base      0.70  — rule matched a clear goal–meal mismatch
      recency   up to +0.12, linear decay over the lookback window
      clarity   +0.08 if classification is definitive, −0.08 if 'unclear'
    """
    factors: list[dict] = []

    base = 0.70
    factors.append({"name": "base", "value": base, "label": "Goal–meal mismatch matched"})

    hours_ago = _hours_since(signal_ts)
    recency_max = 0.12
    recency_value = round(max(0.0, recency_max * (1.0 - hours_ago / lookback_hours)), 2)
    if hours_ago < 1:
        recency_label = "Meal logged less than an hour ago"
    elif hours_ago < 12:
        recency_label = f"Meal logged {hours_ago:.0f}h ago"
    else:
        recency_label = f"Meal logged {hours_ago:.0f}h ago (decayed)"
    factors.append({"name": "recency", "value": recency_value, "label": recency_label})

    if meal_profile != "unclear":
        clarity_value = 0.08
        clarity_label = f"Classification clear ({meal_profile})"
    else:
        clarity_value = -0.08
        clarity_label = "Classification unclear — lower certainty"
    factors.append({"name": "clarity", "value": clarity_value, "label": clarity_label})

    score = _clamp(base + recency_value + clarity_value)
    return score, factors


# ---------------------------------------------------------------------------
# Weight check-in
# ---------------------------------------------------------------------------

def score_weight_check_in(
    *,
    days_since_last_weight: float,
    threshold_days: int,
    has_recent_activity: bool,
) -> tuple[float, list[dict]]:
    """Confidence for a weight-check-in candidate.

    Factors:
      base      0.50  — absence-of-data signal is inherently weaker
      overdue   up to +0.18, linear ramp as days past threshold increase
      activity  +0.08 if the member has other recent signals (engaged but not weighing)
    """
    factors: list[dict] = []

    base = 0.50
    factors.append({"name": "base", "value": base, "label": "Weight log overdue"})

    extra_days = max(0.0, days_since_last_weight - threshold_days)
    overdue_max = 0.18
    overdue_value = round(min(overdue_max, extra_days / threshold_days * overdue_max), 2)
    factors.append({
        "name": "overdue",
        "value": overdue_value,
        "label": f"{days_since_last_weight:.0f}d since last weight log ({extra_days:.0f}d past threshold)",
    })

    if has_recent_activity:
        activity_value = 0.08
        activity_label = "Member active on other signals"
    else:
        activity_value = 0.0
        activity_label = "No other recent activity"
    factors.append({"name": "activity", "value": activity_value, "label": activity_label})

    score = _clamp(base + overdue_value + activity_value)
    return score, factors


# ---------------------------------------------------------------------------
# Support risk
# ---------------------------------------------------------------------------

_SUPPORT_RISK_CAP = 0.48  # hard cap — keeps score below automation threshold


def score_support_risk(
    *,
    mood_signal_ts: str,
    dismiss_count: int,
    mood_lookback_days: int = 3,
    dismiss_lookback_days: int = 7,
) -> tuple[float, list[dict]]:
    """Confidence for a support-risk candidate.

    Intentionally conservative: this is a safety-sensitive path where under-
    escalation is costlier than over-escalation.  The score is hard-capped
    below the automation threshold so routing always defers to coach review
    via the escalation_recommended flag.

    Factors:
      base           0.25  — conservative starting point
      mood_recency   up to +0.12, decaying over the mood lookback window
      dismiss_pattern up to +0.12, based on recent dismissal count
    """
    factors: list[dict] = []

    base = 0.25
    factors.append({"name": "base", "value": base, "label": "Safety path — conservative base"})

    hours_ago = _hours_since(mood_signal_ts)
    days_ago = hours_ago / 24.0
    mood_max = 0.12
    mood_value = round(max(0.0, mood_max * (1.0 - days_ago / mood_lookback_days)), 2)
    if days_ago < 1:
        mood_label = "Low mood reported today"
    else:
        mood_label = f"Low mood reported {days_ago:.1f}d ago"
    factors.append({"name": "mood_recency", "value": mood_value, "label": mood_label})

    dismiss_min = 2
    dismiss_max_bonus = 0.12
    extra = max(0, dismiss_count - dismiss_min)
    dismiss_value = round(min(dismiss_max_bonus, 0.04 + extra * 0.03), 2)
    factors.append({
        "name": "dismiss_pattern",
        "value": dismiss_value,
        "label": f"{dismiss_count} nudges dismissed in last {dismiss_lookback_days}d",
    })

    raw = base + mood_value + dismiss_value
    score = _clamp(min(raw, _SUPPORT_RISK_CAP))
    return score, factors

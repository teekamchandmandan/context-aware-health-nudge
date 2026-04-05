from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

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


class NudgeCandidate(BaseModel):
    nudge_type: str
    matched_reason: str
    explanation_basis: str
    confidence: float = Field(ge=0, le=1)
    confidence_factors: list[dict] = Field(default_factory=list)
    escalation_recommended: bool
    source_signal_ids: list[str]
    priority: int
    latest_signal_ts: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _id() -> str:
    return uuid4().hex


__all__ = [
    "CONFIDENCE_LOW_THRESHOLD",
    "COOLDOWN_HOURS",
    "DAILY_CAP",
    "MISSING_WEIGHT_DAYS",
    "MEAL_CARB_THRESHOLD",
    "MEAL_LOOKBACK_HOURS",
    "MOOD_LOOKBACK_DAYS",
    "DISMISS_LOOKBACK_DAYS",
    "PRIORITY",
    "NudgeCandidate",
    "_now",
    "_ts",
    "_id",
    "timedelta",
]
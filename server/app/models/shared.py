from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    act_now = "act_now"
    dismiss = "dismiss"
    ask_for_help = "ask_for_help"


class SignalType(str, Enum):
    weight_logged = "weight_logged"
    mood_logged = "mood_logged"
    sleep_logged = "sleep_logged"


class NudgeState(str, Enum):
    active = "active"
    no_nudge = "no_nudge"
    escalated = "escalated"


class MemberRef(BaseModel):
    id: str
    name: str


class NudgeDetail(BaseModel):
    id: str
    nudge_type: str
    content: str | None = None
    explanation: str | None = None
    matched_reason: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    escalation_recommended: bool = False
    status: str
    phrasing_source: str = "template"
    created_at: str
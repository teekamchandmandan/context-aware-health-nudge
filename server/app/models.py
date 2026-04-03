"""Pydantic request and response models for Phase 03 API contracts."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


# ── Enums ────────────────────────────────────────────────────────────────────


class ActionType(str, Enum):
    act_now = "act_now"
    dismiss = "dismiss"
    ask_for_help = "ask_for_help"


class SignalType(str, Enum):
    meal_logged = "meal_logged"
    weight_logged = "weight_logged"
    mood_logged = "mood_logged"


class NudgeState(str, Enum):
    active = "active"
    no_nudge = "no_nudge"
    escalated = "escalated"


# ── Shared Fragments ─────────────────────────────────────────────────────────


class MemberRef(BaseModel):
    id: str
    name: str


class NudgeDetail(BaseModel):
    id: str
    nudge_type: str
    content: str | None = None
    explanation: str | None = None
    matched_reason: str | None = None
    confidence: float | None = None
    escalation_recommended: bool = False
    status: str
    phrasing_source: str = "template"
    created_at: str


# ── Member Nudge Response ────────────────────────────────────────────────────


class MemberNudgeResponse(BaseModel):
    state: NudgeState
    member: MemberRef
    nudge: NudgeDetail | None = None
    escalation_created: bool | None = None


# ── Action Request / Response ────────────────────────────────────────────────


class ActionRequest(BaseModel):
    action_type: ActionType


class ActionResponse(BaseModel):
    nudge_id: str
    action_type: str
    nudge_status: str
    escalation_created: bool
    recorded_at: str


# ── Coach List Responses ─────────────────────────────────────────────────────


class CoachNudgeItem(BaseModel):
    nudge_id: str
    member_id: str
    member_name: str
    nudge_type: str
    content: str | None = None
    explanation: str | None = None
    matched_reason: str | None = None
    confidence: float | None = None
    escalation_recommended: bool = False
    status: str
    latest_action: str | None = None
    phrasing_source: str = "template"
    created_at: str


class CoachNudgeListResponse(BaseModel):
    items: list[CoachNudgeItem]
    limit: int
    count: int


class CoachEscalationItem(BaseModel):
    escalation_id: str
    member_id: str
    member_name: str
    reason: str | None = None
    source: str | None = None
    status: str
    created_at: str


class CoachEscalationListResponse(BaseModel):
    items: list[CoachEscalationItem]
    limit: int
    count: int


# ── Signal Intake ────────────────────────────────────────────────────────────


class SignalPayload(BaseModel):
    """Flexible payload validated per signal_type in a model validator."""

    # meal_logged
    meal_type: str | None = None
    carbs_g: float | None = None
    meal_tag: str | None = None
    protein_g: float | None = None
    photo_attached: bool | None = None

    # weight_logged
    weight_lb: float | None = None

    # mood_logged
    mood: str | None = None
    note: str | None = None


class SignalRequest(BaseModel):
    signal_type: SignalType
    payload: SignalPayload

    @model_validator(mode="after")
    def validate_payload_fields(self) -> SignalRequest:
        p = self.payload
        if self.signal_type == SignalType.meal_logged:
            if not p.meal_type:
                raise ValueError("meal_type is required for meal_logged")
            if p.carbs_g is None and not p.meal_tag:
                raise ValueError("At least one of carbs_g or meal_tag is required for meal_logged")
        elif self.signal_type == SignalType.weight_logged:
            if p.weight_lb is None:
                raise ValueError("weight_lb is required for weight_logged")
        elif self.signal_type == SignalType.mood_logged:
            if not p.mood:
                raise ValueError("mood is required for mood_logged")
        return self


class SignalResponse(BaseModel):
    id: str
    member_id: str
    signal_type: str
    payload: dict
    created_at: str

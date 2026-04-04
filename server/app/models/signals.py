from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .shared import SignalType

ALLOWED_MOODS = ("low", "neutral", "high")


class SignalPayload(BaseModel):
    """Current live payload accepted by the /signals endpoint."""

    model_config = ConfigDict(extra="forbid")

    weight_lb: float | None = Field(default=None, gt=0)

    mood: str | None = Field(default=None, max_length=50)

    sleep_hours: float | None = Field(default=None, gt=0, le=24)

    @model_validator(mode="after")
    def normalize_fields(self) -> SignalPayload:
        if self.mood is not None:
            self.mood = self.mood.strip().lower() or None
        return self


class SignalRequest(BaseModel):
    signal_type: SignalType
    payload: SignalPayload

    @model_validator(mode="after")
    def validate_payload_fields(self) -> SignalRequest:
        payload = self.payload
        if self.signal_type == SignalType.weight_logged:
            if payload.weight_lb is None:
                raise ValueError("weight_lb is required for weight_logged")
        elif self.signal_type == SignalType.mood_logged:
            if not payload.mood:
                raise ValueError("mood is required for mood_logged")
            if payload.mood not in ALLOWED_MOODS:
                raise ValueError("mood must be one of: low, neutral, high")
        elif self.signal_type == SignalType.sleep_logged:
            if payload.sleep_hours is None:
                raise ValueError("sleep_hours is required for sleep_logged")
        return self


class SignalResponse(BaseModel):
    id: str
    member_id: str
    signal_type: str
    payload: dict
    created_at: str
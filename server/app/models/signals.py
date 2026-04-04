from __future__ import annotations

from pydantic import BaseModel, model_validator

from .shared import SignalType


class SignalPayload(BaseModel):
    """Flexible payload validated per signal type."""

    meal_input_method: str | None = None
    meal_type: str | None = None
    description: str | None = None
    carbs_g: float | None = None
    meal_tag: str | None = None
    protein_g: float | None = None
    photo_attached: bool | None = None
    analysis_summary: str | None = None
    analysis_confidence: float | None = None
    analysis_status: str | None = None
    analysis_source: str | None = None
    analysis_confirmed: bool | None = None

    weight_lb: float | None = None

    mood: str | None = None
    note: str | None = None

    water_ml: float | None = None

    sleep_hours: float | None = None


class SignalRequest(BaseModel):
    signal_type: SignalType
    payload: SignalPayload

    @model_validator(mode="after")
    def validate_payload_fields(self) -> SignalRequest:
        payload = self.payload
        if self.signal_type == SignalType.meal_logged:
            legacy_payload = bool(payload.meal_type) and (
                payload.carbs_g is not None or bool(payload.meal_tag)
            )
            description_first_payload = bool(payload.meal_input_method) and bool(
                (payload.description and payload.description.strip())
                or (payload.meal_type and payload.meal_type.strip())
            )
            if not (legacy_payload or description_first_payload):
                raise ValueError(
                    "meal_logged requires either legacy structured fields or a description-first meal payload"
                )
        elif self.signal_type == SignalType.weight_logged:
            if payload.weight_lb is None:
                raise ValueError("weight_lb is required for weight_logged")
        elif self.signal_type == SignalType.mood_logged:
            if not payload.mood:
                raise ValueError("mood is required for mood_logged")
        elif self.signal_type == SignalType.water_logged:
            if payload.water_ml is None:
                raise ValueError("water_ml is required for water_logged")
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
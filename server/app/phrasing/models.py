from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

BLOCKED_TERMS = (
    "diagnose",
    "diagnosis",
    "medication",
    "prescription",
    "dose",
    "treatment plan",
    "medical advice",
    "doctor",
    "clinician",
    "therapy",
    "therapist",
    "cure",
    "remedy",
)


class FallbackReason(str, Enum):
    missing_key = "missing_key"
    timeout = "timeout"
    provider_error = "provider_error"
    invalid_json = "invalid_json"
    validation_failure = "validation_failure"


class PhrasingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nudge_type: str
    member_goal: str
    matched_reason: str
    explanation_basis: str
    tone: str = "clear and empathetic"
    max_content_chars: int = 120
    max_explanation_chars: int = 120


class PhrasingOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_safe_copy(self) -> "PhrasingOutput":
        self.content = self.content.strip()
        self.explanation = self.explanation.strip()
        if not self.content or not self.explanation:
            raise ValueError("content and explanation must be non-empty")

        lower_text = f"{self.content} {self.explanation}".lower()
        if any(term in lower_text for term in BLOCKED_TERMS):
            raise ValueError("blocked safety term present")
        return self
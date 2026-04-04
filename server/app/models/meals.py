from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class MealDraftResponse(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    meal_type: str | None = None
    carbs_g: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    photo_attached: bool = False
    analysis_summary: str | None = Field(default=None, max_length=200)
    analysis_confidence: float | None = Field(default=None, ge=0, le=1)
    analysis_status: str = "needs_review"
    analysis_source: str = "fallback"

    @model_validator(mode="after")
    def normalize_fields(self) -> MealDraftResponse:
        self.description = self.description.strip()
        if self.meal_type is not None:
            self.meal_type = self.meal_type.strip().lower() or None
        if self.analysis_summary is not None:
            self.analysis_summary = self.analysis_summary.strip() or None
        return self


class MealLogInput(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    photo_attached: bool = False

    @model_validator(mode="after")
    def validate_fields(self) -> MealLogInput:
        if self.description is not None:
            self.description = self.description.strip() or None
        if not self.description and not self.photo_attached:
            raise ValueError("meal logging requires a description or photo")
        return self
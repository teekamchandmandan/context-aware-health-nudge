from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

ALLOWED_MEAL_PROFILES = {"higher_carb", "higher_protein", "balanced", "unclear"}


class MealDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meal_profile: str
    visible_food_summary: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def normalize_fields(self) -> MealDraftResponse:
        self.meal_profile = self.meal_profile.strip().lower()
        if self.meal_profile not in ALLOWED_MEAL_PROFILES:
            raise ValueError("unsupported meal_profile")
        if self.visible_food_summary is not None:
            self.visible_food_summary = self.visible_food_summary.strip() or None
        return self
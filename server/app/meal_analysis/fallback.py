from app.models.meals import MealDraftResponse


def fallback_meal_analysis() -> MealDraftResponse:
    return MealDraftResponse(meal_profile="unclear")
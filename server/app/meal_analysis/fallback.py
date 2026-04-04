from app.models.meals import MealDraftResponse

FALLBACK_CONFIDENCE_PARTIAL = 0.28


def fallback_meal_analysis() -> MealDraftResponse:
    return MealDraftResponse(
        analysis_summary="We saved your meal photo, but could not estimate macros confidently.",
        analysis_confidence=FALLBACK_CONFIDENCE_PARTIAL,
        analysis_status="partial",
        analysis_source="fallback",
    )
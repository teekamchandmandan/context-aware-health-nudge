from app.models.meals import MealDraftResponse

FALLBACK_MEAL_PATTERNS: tuple[dict[str, object], ...] = (
    {
        "keywords": ("pasta", "carbonara", "spaghetti", "noodles"),
        "meal_name": "Pasta dish",
        "meal_type": "dinner",
        "carbs_g": 72,
        "protein_g": 22,
    },
    {
        "keywords": ("pizza",),
        "meal_name": "Pizza",
        "meal_type": "dinner",
        "carbs_g": 68,
        "protein_g": 24,
    },
    {
        "keywords": ("burrito", "taco", "quesadilla"),
        "meal_name": "Mexican-style meal",
        "meal_type": "lunch",
        "carbs_g": 58,
        "protein_g": 21,
    },
    {
        "keywords": ("salad",),
        "meal_name": "Salad",
        "meal_type": "lunch",
        "carbs_g": 18,
        "protein_g": 10,
    },
    {
        "keywords": ("oatmeal", "porridge", "granola"),
        "meal_name": "Breakfast bowl",
        "meal_type": "breakfast",
        "carbs_g": 30,
        "protein_g": 8,
    },
    {
        "keywords": ("smoothie", "banana", "yogurt"),
        "meal_name": "Snack or smoothie",
        "meal_type": "snack",
        "carbs_g": 26,
        "protein_g": 11,
    },
)

MEAL_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "breakfast": ("breakfast", "coffee", "eggs", "toast", "oatmeal", "yogurt"),
    "lunch": ("lunch", "sandwich", "salad", "bowl", "wrap"),
    "dinner": ("dinner", "pasta", "rice", "curry", "steak", "chicken", "pizza"),
    "snack": ("snack", "bar", "fruit", "smoothie", "chips"),
}


def fallback_meal_draft(description: str, *, photo_attached: bool) -> MealDraftResponse:
    lower_description = description.lower()
    inferred = next(
        (
            pattern
            for pattern in FALLBACK_MEAL_PATTERNS
            if any(keyword in lower_description for keyword in pattern["keywords"])
        ),
        None,
    )

    meal_name = None
    meal_type = infer_meal_type(lower_description)
    carbs_g = None
    protein_g = None
    confidence = 0.28

    if inferred is not None:
        meal_name = str(inferred["meal_name"])
        meal_type = str(inferred["meal_type"])
        carbs_g = float(inferred["carbs_g"])
        protein_g = float(inferred["protein_g"])
        confidence = 0.52

    summary = (
        "Estimated from your meal input. Saved values may be approximate."
        if inferred is not None
        else "We saved the meal input, but could not estimate macros confidently."
    )

    return MealDraftResponse(
        description=description,
        meal_name=meal_name,
        meal_type=meal_type,
        carbs_g=carbs_g,
        protein_g=protein_g,
        photo_attached=photo_attached,
        analysis_summary=summary,
        analysis_confidence=confidence,
        analysis_status="estimated" if inferred is not None else "partial",
        analysis_source="fallback",
    )


def infer_meal_type(description: str) -> str | None:
    for meal_type, keywords in MEAL_TYPE_KEYWORDS.items():
        if any(keyword in description for keyword in keywords):
            return meal_type
    return None
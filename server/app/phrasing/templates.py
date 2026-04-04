TEMPLATE_PHRASING: dict[str, dict[str, str]] = {
    "meal_guidance": {
        "content": "Try a lighter, lower-carb dinner to balance today's earlier meal.",
        "explanation": "You logged a higher-carb meal today and your goal is low carb.",
    },
    "weight_check_in": {
        "content": "Take a quick weight check-in when you have a minute.",
        "explanation": "You have not logged weight in the last few days.",
    },
    "support_risk": {
        "content": "A coach follow-up is a better next step than another automated nudge.",
        "explanation": "Recent signals suggest you may benefit from direct support.",
    },
}


def get_template_phrasing(nudge_type: str) -> dict[str, str]:
    return TEMPLATE_PHRASING[nudge_type].copy()


CONFIDENT_TONE_THRESHOLD = 0.75


def desired_tone_for_confidence(confidence: float) -> str:
    if confidence >= CONFIDENT_TONE_THRESHOLD:
        return "clear, supportive, and practical"
    return "gentle, supportive, and practical"
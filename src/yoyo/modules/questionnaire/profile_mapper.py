from __future__ import annotations

from typing import Any

from yoyo.modules.questionnaire.flow import DEFAULT_GUIDE_ROLE, GUIDE_ROLE_TO_STYLE


DEFAULTS = {
    "preferred_language": "en",
    "interests": ["history", "culture"],
    "travel_style": "balanced",
    "walking_preference": "moderate",
    "pace_preference": "balanced",
    "audience_type": "general",
    "answer_length_preference": "medium",
}


def map_answers_to_profile_fields(answers: dict[str, Any]) -> dict[str, Any]:
    guide_role = str(answers.get("guide_role") or DEFAULT_GUIDE_ROLE)
    travel_style = str(answers.get("travel_style") or DEFAULTS["travel_style"])
    interests = answers.get("interests") or DEFAULTS["interests"]
    if not isinstance(interests, list):
        interests = DEFAULTS["interests"]

    return {
        "preferred_language": str(answers.get("preferred_language") or DEFAULTS["preferred_language"]),
        "interests_json": [str(item) for item in interests],
        "travel_style": travel_style,
        "walking_preference": str(answers.get("walking_preference") or DEFAULTS["walking_preference"]),
        "pace_preference": travel_style,
        "audience_type": str(answers.get("audience_type") or DEFAULTS["audience_type"]),
        "answer_length_preference": str(
            answers.get("answer_length_preference") or DEFAULTS["answer_length_preference"]
        ),
        "guide_style_preference": GUIDE_ROLE_TO_STYLE.get(guide_role, GUIDE_ROLE_TO_STYLE[DEFAULT_GUIDE_ROLE]),
        "profile_source": "questionnaire_flow",
        "profile_version": "v1",
    }

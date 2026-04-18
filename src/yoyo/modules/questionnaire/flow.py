from __future__ import annotations

from typing import Any

QUESTIONNAIRE_FLOW_VERSION = "v1"
DEFAULT_GUIDE_ROLE = "balanced_storyteller"

GUIDE_ROLE_TO_STYLE = {
    "balanced_storyteller": "SJ",
    "history_scholar": "NT",
    "emotional_companion": "NF",
    "city_explorer": "SP",
}

QUESTIONNAIRE_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "guide_role",
        "type": "single_select",
        "title": "Choose your guide role",
        "options": [
            {"value": "balanced_storyteller", "label": "Balanced storyteller"},
            {"value": "history_scholar", "label": "History scholar"},
            {"value": "emotional_companion", "label": "Emotional companion"},
            {"value": "city_explorer", "label": "City explorer"},
        ],
    },
    {
        "id": "preferred_language",
        "type": "single_select",
        "title": "Preferred guide language",
        "options": [
            {"value": "en", "label": "English"},
            {"value": "zh", "label": "中文"},
            {"value": "es", "label": "Español"},
        ],
    },
    {
        "id": "interests",
        "type": "multi_select",
        "title": "What are you most interested in?",
        "options": [
            {"value": "history", "label": "History"},
            {"value": "culture", "label": "Culture"},
            {"value": "architecture", "label": "Architecture"},
            {"value": "photography", "label": "Photography"},
            {"value": "food", "label": "Food"},
            {"value": "views", "label": "Views"},
            {"value": "family", "label": "Family-friendly spots"},
        ],
    },
    {
        "id": "travel_style",
        "type": "single_select",
        "title": "Which trip rhythm fits you best?",
        "options": [
            {"value": "balanced", "label": "Balanced"},
            {"value": "relaxed", "label": "Relaxed"},
            {"value": "focused", "label": "Focused"},
            {"value": "scenic", "label": "Scenic"},
        ],
    },
    {
        "id": "walking_preference",
        "type": "single_select",
        "title": "How much walking feels comfortable?",
        "options": [
            {"value": "light", "label": "Light walking"},
            {"value": "moderate", "label": "Moderate walking"},
            {"value": "high", "label": "High walking"},
        ],
    },
    {
        "id": "audience_type",
        "type": "single_select",
        "title": "Who are you traveling with?",
        "options": [
            {"value": "general", "label": "General / mixed group"},
            {"value": "family", "label": "Family"},
            {"value": "solo", "label": "Solo"},
            {"value": "couple", "label": "Couple"},
        ],
    },
    {
        "id": "answer_length_preference",
        "type": "single_select",
        "title": "How detailed should explanations be?",
        "options": [
            {"value": "short", "label": "Short"},
            {"value": "medium", "label": "Medium"},
            {"value": "long", "label": "Long"},
        ],
    },
]

QUESTION_IDS = {question["id"] for question in QUESTIONNAIRE_QUESTIONS}
MULTI_SELECT_IDS = {
    question["id"]
    for question in QUESTIONNAIRE_QUESTIONS
    if question["type"] == "multi_select"
}
SINGLE_SELECT_IDS = QUESTION_IDS - MULTI_SELECT_IDS
ALLOWED_OPTIONS = {
    question["id"]: {option["value"] for option in question["options"]}
    for question in QUESTIONNAIRE_QUESTIONS
}


def get_questionnaire_flow() -> dict[str, Any]:
    return {
        "version": QUESTIONNAIRE_FLOW_VERSION,
        "question_count": len(QUESTIONNAIRE_QUESTIONS),
        "questions": QUESTIONNAIRE_QUESTIONS,
    }

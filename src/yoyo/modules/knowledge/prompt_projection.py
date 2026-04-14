from __future__ import annotations

from typing import Any

from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext

PROMPT_SAFE_ATTRACTION_FIELDS = [
    "name",
    "aliases",
    "category",
    "recommended_duration_minutes",
    "tags",
    "short_intro",
    "history",
    "highlights",
    "visitor_tips",
    "practical_notes",
    "photo_spot_notes",
]

PROMPT_SAFE_PROFILE_FIELDS = [
    "preferred_language",
    "interests",
    "travel_style",
    "walking_preference",
    "pace_preference",
    "audience_type",
    "answer_length_preference",
    "guide_style_preference",
]

GUIDE_STYLE_LABELS = {
    "NF": "idealist",
    "NT": "rational",
    "SJ": "guardian",
    "SP": "artisan",
}


def project_attraction_for_prompt(attraction: AttractionContext | None) -> dict[str, Any]:
    if attraction is None:
        return {}
    data = attraction.model_dump()
    return {key: data[key] for key in PROMPT_SAFE_ATTRACTION_FIELDS if key in data}



def project_profile_for_prompt(profile: ProfileContext | None) -> dict[str, Any]:
    if profile is None:
        return {}
    data = profile.model_dump()
    return {key: data[key] for key in PROMPT_SAFE_PROFILE_FIELDS if key in data}



def describe_guide_style(style: str | None) -> str:
    if style is None:
        return "balanced"
    return GUIDE_STYLE_LABELS.get(style, style.lower())

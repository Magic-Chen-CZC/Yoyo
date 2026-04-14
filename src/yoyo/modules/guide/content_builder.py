from __future__ import annotations

from yoyo.modules.knowledge.prompt_projection import describe_guide_style
from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext


def build_guide_bundle(
    *,
    summary: str | None,
    attractions: list[AttractionContext],
    profile: ProfileContext | None,
    llm_bundle: dict[str, object] | None = None,
) -> dict[str, object]:
    profile_language = profile.preferred_language if profile is not None else "en"
    profile_interests = profile.interests if profile is not None else []
    profile_style = profile.travel_style if profile is not None else "balanced"
    guide_style = describe_guide_style(profile.guide_style_preference if profile is not None else "SJ")

    guide_stops: list[dict[str, object]] = []
    stop_names: list[str] = []
    practical_tips: list[str] = []
    route_highlights: list[str] = []

    for attraction in attractions:
        stop_names.append(attraction.name)
        if attraction.visitor_tips:
            practical_tips.append(attraction.visitor_tips[0])
        if attraction.highlights:
            route_highlights.append(attraction.highlights[0])

        llm_stop = _find_llm_stop(llm_bundle, attraction.name)
        guide_stops.append(
            {
                "stop_id": attraction.id,
                "stop_name": attraction.name,
                "narration": str(llm_stop.get("narration")) if llm_stop and llm_stop.get("narration") else _build_narration(attraction, profile_interests, guide_style),
                "why_it_matters": str(llm_stop.get("why_it_matters")) if llm_stop and llm_stop.get("why_it_matters") else (attraction.history or attraction.short_intro),
                "visitor_tip": str(llm_stop.get("visitor_tip")) if llm_stop and llm_stop.get("visitor_tip") else (attraction.visitor_tips[0] if attraction.visitor_tips else "Keep the pacing comfortable."),
                "recommended_duration_minutes": attraction.recommended_duration_minutes,
            }
        )

    title = summary or "Beijing guide route"
    intro = _coerce_text(llm_bundle, "intro") or _build_intro(title, attractions, profile, guide_style)
    outro = _coerce_text(llm_bundle, "outro") or _build_outro(profile_style, profile_language, len(attractions), guide_style)

    return {
        "summary": title,
        "stop_count": len(attractions),
        "stops": stop_names,
        "guide_script": {
            "title": title,
            "intro": intro,
            "language": profile_language,
            "stops": guide_stops,
            "outro": outro,
        },
        "card": {
            "headline": _coerce_text(llm_bundle, "card_headline") or title,
            "highlights": _coerce_string_list(llm_bundle, "card_highlights") or route_highlights[:3] or stop_names[:3],
            "route_style": profile_style,
            "guide_style": guide_style,
            "practical_tips": _coerce_string_list(llm_bundle, "card_practical_tips") or practical_tips[:3],
        },
        "audio": {
            "status": "not_generated",
            "url": None,
            "language": profile_language,
            "voice": "default",
            "estimated_duration_seconds": max(30, len(attractions) * 45),
            "segments": [
                {
                    "stop_id": stop["stop_id"],
                    "stop_name": stop["stop_name"],
                    "status": "not_generated",
                }
                for stop in guide_stops
            ],
        },
    }


def _build_intro(summary: str, attractions: list[AttractionContext], profile: ProfileContext | None, guide_style: str) -> str:
    if not attractions:
        return "This route has no planned stops yet."
    first_stop = attractions[0].name
    interests = ", ".join(profile.interests[:2]) if profile and profile.interests else "general sightseeing"
    return (
        f"{summary}. This route starts at {first_stop} and is tuned for {interests}. "
        f"Keep a {profile.travel_style if profile else 'balanced'} pace as you move through the stops. "
        f"Narrative tone: {guide_style}."
    )


def _build_outro(travel_style: str, language: str, stop_count: int, guide_style: str) -> str:
    return (
        f"You have {stop_count} stop(s) in this guide. Continue with a {travel_style} rhythm, use {language} guidance cues as needed, and keep a {guide_style} tone throughout the route."
    )


def _build_narration(attraction: AttractionContext, interests: list[str], guide_style: str) -> str:
    focus = ", ".join(interests[:2]) if interests else attraction.category
    if guide_style == "idealist":
        return (
            f"{attraction.name}: {attraction.short_intro} Focus on the meaning and emotional resonance of {focus}. "
            f"Highlight: {attraction.highlights[0] if attraction.highlights else attraction.history}"
        )
    if guide_style == "rational":
        return (
            f"{attraction.name}: {attraction.short_intro} Focus on the structure and logic behind {focus}. "
            f"Highlight: {attraction.highlights[0] if attraction.highlights else attraction.history}"
        )
    if guide_style == "artisan":
        return (
            f"{attraction.name}: {attraction.short_intro} Focus on the immediate experience of {focus}. "
            f"Highlight: {attraction.highlights[0] if attraction.highlights else attraction.history}"
        )
    return (
        f"{attraction.name}: {attraction.short_intro} Focus on the practical, well-structured side of {focus}. "
        f"Highlight: {attraction.highlights[0] if attraction.highlights else attraction.history}"
    )



def _coerce_text(payload: dict[str, object] | None, key: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None



def _coerce_string_list(payload: dict[str, object] | None, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]



def _find_llm_stop(payload: dict[str, object] | None, stop_name: str) -> dict[str, object] | None:
    if not isinstance(payload, dict):
        return None
    stop_scripts = payload.get("stop_scripts")
    if not isinstance(stop_scripts, list):
        return None
    for item in stop_scripts:
        if isinstance(item, dict) and str(item.get("stop_name")) == stop_name:
            return item
    return None

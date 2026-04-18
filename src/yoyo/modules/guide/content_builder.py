from __future__ import annotations

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.prompt_projection import describe_guide_style
from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext
from yoyo.modules.shared_text_sanitizer import sanitize_llm_string_list, sanitize_llm_text


def _segment_matches_preferences(segment: str, profile: ProfileContext | None, attraction: AttractionContext) -> tuple[int, int]:
    lowered = segment.lower()
    score = 0
    if profile is not None:
        if profile.answer_length_preference == "short":
            score += max(0, 200 - len(segment))
        elif profile.answer_length_preference == "long":
            score += len(segment)
        for interest in profile.interests:
            if interest.lower() in lowered:
                score += 120
        if profile.guide_style_preference == "NF" and any(token in lowered for token in ["meaning", "story", "human", "memory"]):
            score += 80
        if profile.guide_style_preference == "NT" and any(token in lowered for token in ["structure", "logic", "system", "organized"]):
            score += 80
        if profile.guide_style_preference == "SJ" and any(token in lowered for token in ["practical", "clear", "route", "pace"]):
            score += 80
        if profile.guide_style_preference == "SP" and any(token in lowered for token in ["view", "experience", "on-site", "immediate"]):
            score += 80
    if attraction.category.lower() in lowered:
        score += 40
    return score, -len(segment)



def select_guide_segments_for_stop(
    attraction: AttractionContext,
    profile: ProfileContext | None,
    *,
    limit: int = 3,
) -> list[str]:
    segments = [segment for segment in attraction.guide_segments if segment.strip()]
    if not segments:
        return []
    ranked = sorted(
        enumerate(segments),
        key=lambda item: _segment_matches_preferences(item[1], profile, attraction),
        reverse=True,
    )
    selected = [segments[index] for index, _segment in ranked[:limit]]
    return selected


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
        selected_segments = select_guide_segments_for_stop(attraction, profile, limit=3)
        guide_stops.append(
            {
                "stop_id": attraction.id,
                "stop_name": attraction.name,
                "narration": _sanitize_llm_stop_text(llm_stop, "narration") or _build_narration(attraction, profile_interests, guide_style),
                "why_it_matters": _sanitize_llm_stop_text(llm_stop, "why_it_matters") or (attraction.history or attraction.short_intro),
                "visitor_tip": _sanitize_llm_stop_text(llm_stop, "visitor_tip") or (attraction.visitor_tips[0] if attraction.visitor_tips else "Take your time here and follow the next cue when you're ready to move on."),
                "recommended_duration_minutes": attraction.recommended_duration_minutes,
                "guide_segments": selected_segments,
                "segment_count": len(attraction.guide_segments),
                "more_content_available": len(attraction.guide_segments) > len(selected_segments),
            }
        )

    title = summary or "Beijing guide route"
    intro = _coerce_text(llm_bundle, "intro") or _build_intro(title, attractions, profile, guide_style)
    outro = _coerce_text(llm_bundle, "outro") or _build_outro(profile_style, profile_language, len(attractions), guide_style)

    settings = get_settings()
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
            "status": "pending" if settings.tts_api_key else "unavailable",
            "url": None,
            "language": profile_language,
            "voice": settings.tts_voice,
            "estimated_duration_seconds": max(30, len(attractions) * 45),
            "segments": [
                {
                    "stop_id": stop["stop_id"],
                    "stop_name": stop["stop_name"],
                    "status": "pending" if settings.tts_api_key else "unavailable",
                    "segment_index": 0,
                    "url": None,
                }
                for stop in guide_stops
            ],
        },
    }


def _build_intro(summary: str, attractions: list[AttractionContext], profile: ProfileContext | None, guide_style: str) -> str:
    if not attractions:
        return "Your guide route is still being prepared. Once stops are ready, I can walk you through them one by one."
    first_stop = attractions[0].name
    interests = ", ".join(profile.interests[:2]) if profile and profile.interests else "the main sights"
    pace = profile.travel_style if profile else "balanced"
    return (
        f"{summary}. We'll begin at {first_stop} and keep the route focused on {interests}. "
        f"Expect a {pace} pace with short, easy-to-follow guidance at each stop."
    )


def _build_outro(travel_style: str, language: str, stop_count: int, guide_style: str) -> str:
    return (
        f"This guide covers {stop_count} stop(s). Continue at a {travel_style} pace, and I'll keep the directions clear and easy to follow in {language}."
    )


def _build_narration(attraction: AttractionContext, interests: list[str], guide_style: str) -> str:
    if attraction.guide_segments:
        return " ".join(attraction.guide_segments[:2])
    focus = ", ".join(interests[:2]) if interests else attraction.category
    if guide_style == "idealist":
        return (
            f"{attraction.name}: {attraction.short_intro} This stop is best understood through its meaning and human story, especially around {focus}. "
            f"A good detail to notice is {attraction.highlights[0] if attraction.highlights else attraction.history}."
        )
    if guide_style == "rational":
        return (
            f"{attraction.name}: {attraction.short_intro} This stop makes the most sense when you look at the structure and logic behind {focus}. "
            f"A useful detail to notice is {attraction.highlights[0] if attraction.highlights else attraction.history}."
        )
    if guide_style == "artisan":
        return (
            f"{attraction.name}: {attraction.short_intro} This stop is easiest to enjoy through the immediate on-site experience of {focus}. "
            f"A good detail to notice is {attraction.highlights[0] if attraction.highlights else attraction.history}."
        )
    return (
        f"{attraction.name}: {attraction.short_intro} This stop is easiest to follow when explained clearly and practically, with attention to {focus}. "
        f"A useful detail to notice is {attraction.highlights[0] if attraction.highlights else attraction.history}."
    )



def _coerce_text(payload: dict[str, object] | None, key: str) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if not isinstance(value, str):
        return None
    return sanitize_llm_text(value)



def _coerce_string_list(payload: dict[str, object] | None, key: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    value = payload.get(key)
    return sanitize_llm_string_list(value if isinstance(value, list) else None)



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



def _sanitize_llm_stop_text(llm_stop: dict[str, object] | None, key: str) -> str | None:
    if not isinstance(llm_stop, dict):
        return None
    value = llm_stop.get(key)
    if not isinstance(value, str):
        return None
    return sanitize_llm_text(value)

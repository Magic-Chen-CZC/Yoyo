from __future__ import annotations

from yoyo.modules.knowledge.prompt_projection import describe_guide_style
from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, PromptMessage



def build_guide_generation_request(
    *,
    provider: str,
    model: str,
    summary: str | None,
    attractions: list[AttractionContext],
    profile: ProfileContext | None,
) -> LLMRequest:
    route_summary = summary or "Beijing guide route"
    profile_language = profile.preferred_language if profile is not None else "en"
    guide_style = describe_guide_style(profile.guide_style_preference if profile is not None else "SJ")
    interests = ", ".join(profile.interests[:3]) if profile and profile.interests else "general sightseeing"
    attraction_lines: list[str] = []
    for attraction in attractions:
        attraction_lines.append(
            "\n".join(
                [
                    f"Stop: {attraction.name}",
                    f"Category: {attraction.category}",
                    f"Recommended duration: {attraction.recommended_duration_minutes}",
                    f"Short intro: {attraction.short_intro}",
                    f"History: {attraction.history}",
                    f"Highlights: {', '.join(attraction.highlights[:3])}",
                    f"Visitor tips: {', '.join(attraction.visitor_tips[:2])}",
                    f"Practical notes: {', '.join(attraction.practical_notes[:2])}",
                    f"Photo notes: {', '.join(attraction.photo_spot_notes[:2])}",
                ]
            )
        )

    system_prompt = (
        "You are generating a structured Beijing guide bundle. "
        "Use only the provided route and SQL-grounded attraction/profile facts. "
        "Do not invent new attractions, historical claims, or runtime state. "
        "Return concise, user-facing copy in valid JSON with keys: intro, outro, card_headline, card_highlights, card_practical_tips, and stop_scripts. "
        "Each item in stop_scripts must contain stop_name, narration, why_it_matters, and visitor_tip."
    )

    user_prompt = "\n\n".join(
        [
            f"Route summary: {route_summary}",
            f"Output language: {profile_language}",
            f"Guide style: {guide_style}",
            f"User interests: {interests}",
            f"Travel style: {profile.travel_style if profile else 'balanced'}",
            f"Walking preference: {profile.walking_preference if profile else 'moderate'}",
            "Attraction facts:",
            "\n\n".join(attraction_lines) if attraction_lines else "No attractions available.",
        ]
    )

    return LLMRequest(
        provider=provider,
        model=model,
        messages=[
            PromptMessage(role="system", content=system_prompt),
            PromptMessage(role="user", content=user_prompt),
        ],
        options=GenerationOptions(max_tokens=900, temperature=0.4, timeout_seconds=45.0),
        metadata={"prompt_version": "guide-v1"},
    )

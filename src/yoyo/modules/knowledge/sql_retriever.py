from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.attraction import Attraction
from yoyo.db.models.profile import UserProfile
from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext
from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE

_ALLOWED_DATASETS = {"attractions", "profiles"}


def query_mock_dataset(dataset: str) -> list[AttractionContext | ProfileContext]:
    if dataset not in _ALLOWED_DATASETS:
        raise ValueError(f"unsupported dataset: {dataset}")
    if dataset == "attractions":
        return list(MOCK_SEED_BUNDLE.attractions)
    return list(MOCK_SEED_BUNDLE.profiles)



def filter_by_name(records: Iterable[AttractionContext], query: str) -> list[AttractionContext]:
    lowered = query.strip().lower()
    if not lowered:
        return list(records)
    return [
        record
        for record in records
        if lowered in record.name.lower() or any(lowered in alias.lower() for alias in record.aliases)
    ]



def filter_by_user_id(records: Iterable[ProfileContext], user_id: str | None) -> ProfileContext | None:
    if not user_id:
        return None
    lowered = user_id.strip().lower()
    for record in records:
        if record.user_id.lower() == lowered:
            return record
    return None



async def fetch_attraction_by_name(session: AsyncSession, name: str | None) -> AttractionContext | None:
    if not name:
        return None

    lowered = name.strip().lower()
    result = await session.execute(select(Attraction).where(Attraction.name == name))
    attraction = result.scalar_one_or_none()
    if attraction is None:
        result = await session.execute(select(Attraction))
        for candidate in result.scalars().all():
            aliases = candidate.aliases_json or []
            if lowered == candidate.name.lower() or any(lowered == alias.lower() for alias in aliases):
                attraction = candidate
                break

    if attraction is None:
        return None
    return _to_attraction_context(attraction)



async def fetch_user_profile(session: AsyncSession, user_id: str | None) -> ProfileContext | None:
    if not user_id:
        return None
    result = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return _to_profile_context(profile)



def _to_attraction_context(attraction: Attraction) -> AttractionContext:
    return AttractionContext(
        id=attraction.id,
        name=attraction.name,
        aliases=list(attraction.aliases_json or []),
        category=attraction.category,
        latitude=attraction.latitude,
        longitude=attraction.longitude,
        recommended_duration_minutes=attraction.recommended_duration_minutes,
        tags=list(attraction.tags_json or []),
        short_intro=attraction.short_intro,
        history=attraction.history,
        highlights=list(attraction.highlights_json or []),
        visitor_tips=list(attraction.visitor_tips_json or []),
        practical_notes=list(attraction.practical_notes_json or []),
        family_friendly_notes=list(attraction.family_friendly_notes_json or []),
        photo_spot_notes=list(attraction.photo_spot_notes_json or []),
        guide_segments=list(attraction.guide_segments_json or []),
        source="postgresql",
    )



def _to_profile_context(profile: UserProfile) -> ProfileContext:
    return ProfileContext(
        user_id=profile.user_id,
        preferred_language=profile.preferred_language,
        interests=list(profile.interests_json or []),
        travel_style=profile.travel_style,
        walking_preference=profile.walking_preference,
        pace_preference=profile.pace_preference,
        audience_type=profile.audience_type,
        answer_length_preference=profile.answer_length_preference,
        guide_style_preference=profile.guide_style_preference,
        source="postgresql",
    )

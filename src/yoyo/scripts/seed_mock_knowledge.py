from __future__ import annotations

import asyncio

from sqlalchemy import delete, select

from yoyo.db.models.attraction import Attraction
from yoyo.db.models.profile import UserProfile
from yoyo.db.session import get_session_factory
from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE


async def seed_mock_knowledge() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(Attraction))
        await session.execute(delete(UserProfile))

        for attraction in MOCK_SEED_BUNDLE.attractions:
            session.add(
                Attraction(
                    id=attraction.id,
                    city_code="beijing",
                    name=attraction.name,
                    aliases_json=attraction.aliases,
                    category=attraction.category,
                    latitude=attraction.latitude,
                    longitude=attraction.longitude,
                    recommended_duration_minutes=attraction.recommended_duration_minutes,
                    tags_json=attraction.tags,
                    short_intro=attraction.short_intro,
                    history=attraction.history,
                    highlights_json=attraction.highlights,
                    visitor_tips_json=attraction.visitor_tips,
                    practical_notes_json=attraction.practical_notes,
                    family_friendly_notes_json=attraction.family_friendly_notes,
                    photo_spot_notes_json=attraction.photo_spot_notes,
                )
            )

        for profile in MOCK_SEED_BUNDLE.profiles:
            session.add(
                UserProfile(
                    user_id=profile.user_id,
                    preferred_language=profile.preferred_language,
                    interests_json=profile.interests,
                    travel_style=profile.travel_style,
                    walking_preference=profile.walking_preference,
                    pace_preference=profile.pace_preference,
                    audience_type=profile.audience_type,
                    answer_length_preference=profile.answer_length_preference,
                    guide_style_preference=profile.guide_style_preference,
                )
            )

        await session.commit()

        attraction_count = len((await session.execute(select(Attraction))).scalars().all())
        profile_count = len((await session.execute(select(UserProfile))).scalars().all())
        print(f"Seeded attractions: {attraction_count}")
        print(f"Seeded profiles: {profile_count}")


if __name__ == "__main__":
    asyncio.run(seed_mock_knowledge())

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import delete, select

from yoyo.db.models.attraction import Attraction
from yoyo.db.models.profile import UserProfile
from yoyo.db.session import get_session_factory


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = PROJECT_ROOT / "evals" / "datasets"
ATTRACTIONS_PATH = DATASET_DIR / "beijing_attractions_structured_v1.json"
PROFILES_PATH = DATASET_DIR / "benchmark_profiles_v1.json"


async def seed_benchmark_fixtures() -> None:
    attractions = json.loads(ATTRACTIONS_PATH.read_text(encoding="utf-8"))
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))

    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(delete(Attraction))
        await session.execute(delete(UserProfile))

        for attraction in attractions:
            session.add(
                Attraction(
                    id=attraction["id"],
                    city_code=attraction.get("city_code", "beijing"),
                    name=attraction["name"],
                    aliases_json=list(attraction.get("aliases") or []),
                    category=attraction.get("category", "attraction"),
                    latitude=attraction.get("latitude"),
                    longitude=attraction.get("longitude"),
                    recommended_duration_minutes=attraction.get("recommended_duration_minutes"),
                    tags_json=list(attraction.get("tags") or []),
                    short_intro=attraction.get("short_intro", ""),
                    history=attraction.get("history", ""),
                    highlights_json=list(attraction.get("highlights") or []),
                    visitor_tips_json=list(attraction.get("visitor_tips") or []),
                    practical_notes_json=list(attraction.get("practical_notes") or []),
                    family_friendly_notes_json=list(attraction.get("family_friendly_notes") or []),
                    photo_spot_notes_json=list(attraction.get("photo_spot_notes") or []),
                    guide_segments_json=list(attraction.get("guide_segments") or []),
                )
            )

        for profile in profiles:
            session.add(
                UserProfile(
                    user_id=profile["user_id"],
                    preferred_language=profile.get("preferred_language", "en"),
                    interests_json=list(profile.get("interests") or []),
                    travel_style=profile.get("travel_style", "balanced"),
                    walking_preference=profile.get("walking_preference", "moderate"),
                    pace_preference=profile.get("pace_preference", "balanced"),
                    audience_type=profile.get("audience_type", "general"),
                    answer_length_preference=profile.get("answer_length_preference", "medium"),
                    guide_style_preference=profile.get("guide_style_preference", "SJ"),
                    profile_source=profile.get("source", "benchmark_profile_v1"),
                    profile_version=profile.get("profile_version", "v1"),
                )
            )

        await session.commit()

        attraction_count = len((await session.execute(select(Attraction))).scalars().all())
        profile_count = len((await session.execute(select(UserProfile))).scalars().all())
        print(f"Seeded benchmark attractions: {attraction_count}")
        print(f"Seeded benchmark profiles: {profile_count}")


if __name__ == "__main__":
    asyncio.run(seed_benchmark_fixtures())

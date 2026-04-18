from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.schemas import ProfileContext
from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE
from yoyo.modules.knowledge.sql_retriever import fetch_user_profile, filter_by_user_id


def allow_mock_profile_fallback() -> bool:
    settings = get_settings()
    return settings.app_env in {"local", "test"}


async def get_profile_context(user_id: str | None, session: AsyncSession | None = None) -> ProfileContext | None:
    if session is not None:
        profile = await fetch_user_profile(session, user_id)
        if profile is not None:
            return profile

    if allow_mock_profile_fallback():
        profile = filter_by_user_id(MOCK_SEED_BUNDLE.profiles, user_id)
        if profile is not None:
            return profile
    if user_id is None:
        return None
    return ProfileContext(user_id=user_id, source="derived_default")

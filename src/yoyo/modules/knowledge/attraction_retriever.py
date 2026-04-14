from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.modules.knowledge.schemas import AttractionContext
from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE
from yoyo.modules.knowledge.sql_retriever import fetch_attraction_by_name, filter_by_name


DEFAULT_ATTRACTION_NAMES = {
    "tiananmen": "Tiananmen Square",
    "forbidden city": "Forbidden City",
    "jingshan": "Jingshan Park",
    "temple of heaven": "Temple of Heaven",
    "summer palace": "Summer Palace",
}



def list_mock_attractions(limit: int | None = None) -> list[AttractionContext]:
    if limit is None:
        return list(MOCK_SEED_BUNDLE.attractions)
    return list(MOCK_SEED_BUNDLE.attractions[:limit])


async def get_attraction_context(name: str | None, session: AsyncSession | None = None) -> AttractionContext | None:
    if not name:
        return None

    if session is not None:
        attraction = await fetch_attraction_by_name(session, name)
        if attraction is not None:
            return attraction

    exact = next((item for item in MOCK_SEED_BUNDLE.attractions if item.name == name), None)
    if exact is not None:
        return exact

    matches = filter_by_name(MOCK_SEED_BUNDLE.attractions, name)
    if matches:
        return matches[0]

    lowered = name.strip().lower()
    canonical_name = DEFAULT_ATTRACTION_NAMES.get(lowered)
    if canonical_name is None:
        return None

    return next((item for item in MOCK_SEED_BUNDLE.attractions if item.name == canonical_name), None)

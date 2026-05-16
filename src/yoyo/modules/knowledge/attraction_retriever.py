from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.schemas import AttractionContext
from yoyo.modules.knowledge.seed_postgres import MOCK_SEED_BUNDLE
from yoyo.modules.knowledge.sql_retriever import fetch_attraction_by_name, filter_by_name


KNOWN_ATTRACTION_ALIASES: dict[str, tuple[str, ...]] = {
    "Tiananmen Square": ("天安门", "天安门广场", "Tiananmen", "Tiananmen Plaza"),
    "Forbidden City": ("故宫", "故宫博物院", "紫禁城", "Palace Museum", "Imperial Palace"),
    "Jingshan Park": ("景山", "景山公园", "煤山公园", "Jingshan", "Coal Hill Park"),
    "Temple of Heaven": ("天坛", "祈年殿", "Tiantan", "Heaven Temple"),
    "Summer Palace": ("颐和园", "Yiheyuan"),
    "Zhengyangmen": ("正阳门", "前门", "Qianmen", "Front Gate"),
}

DEFAULT_ATTRACTION_NAMES = {
    alias.strip().lower(): canonical_name
    for canonical_name, aliases in KNOWN_ATTRACTION_ALIASES.items()
    for alias in (canonical_name, *aliases)
}



def list_mock_attractions(limit: int | None = None) -> list[AttractionContext]:
    if limit is None:
        return list(MOCK_SEED_BUNDLE.attractions)
    return list(MOCK_SEED_BUNDLE.attractions[:limit])



def allow_mock_knowledge_fallback() -> bool:
    settings = get_settings()
    return settings.app_env in {"local", "test"}



def get_known_attraction_aliases(name: str | None) -> list[str]:
    if not name:
        return []
    merged: list[str] = []
    for alias in (name, *KNOWN_ATTRACTION_ALIASES.get(name, ())):
        stripped = alias.strip()
        if stripped and stripped not in merged:
            merged.append(stripped)
    return merged



def resolve_attraction_name_candidate(text: str | None) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    exact = DEFAULT_ATTRACTION_NAMES.get(lowered)
    if exact is not None:
        return exact
    for alias, canonical_name in sorted(DEFAULT_ATTRACTION_NAMES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias and alias in lowered:
            return canonical_name
    return None


async def get_attraction_context(name: str | None, session: AsyncSession | None = None) -> AttractionContext | None:
    if not name:
        return None

    canonical_name = resolve_attraction_name_candidate(name)
    candidate_names = [name]
    if canonical_name is not None and canonical_name != name:
        candidate_names.append(canonical_name)

    if session is not None:
        for candidate_name in candidate_names:
            attraction = await fetch_attraction_by_name(session, candidate_name)
            if attraction is not None:
                return _with_known_aliases(attraction)

    if not allow_mock_knowledge_fallback():
        return None

    for candidate_name in candidate_names:
        exact = next((item for item in MOCK_SEED_BUNDLE.attractions if item.name == candidate_name), None)
        if exact is not None:
            return _with_known_aliases(exact)

        matches = filter_by_name(MOCK_SEED_BUNDLE.attractions, candidate_name)
        if matches:
            return _with_known_aliases(matches[0])

    if canonical_name is None:
        return None

    match = next((item for item in MOCK_SEED_BUNDLE.attractions if item.name == canonical_name), None)
    if match is None:
        return None
    return _with_known_aliases(match)



def _with_known_aliases(attraction: AttractionContext) -> AttractionContext:
    known_aliases = get_known_attraction_aliases(attraction.name)
    merged_aliases = list(attraction.aliases)
    for alias in known_aliases:
        if alias not in merged_aliases:
            merged_aliases.append(alias)
    if merged_aliases == attraction.aliases:
        return attraction
    return attraction.model_copy(update={"aliases": merged_aliases})

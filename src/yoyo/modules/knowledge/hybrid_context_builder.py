from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.modules.knowledge.attraction_retriever import get_attraction_context
from yoyo.modules.knowledge.live_retriever import get_live_info_context
from yoyo.modules.knowledge.profile_retriever import get_profile_context
from yoyo.modules.knowledge.prompt_projection import project_attraction_for_prompt, project_profile_for_prompt
from yoyo.modules.knowledge.schemas import HybridContext


async def build_hybrid_context(
    *,
    intent: str,
    query: str,
    attraction_name: str | None,
    user_id: str | None,
    session_context: dict,
    dialogue_history: list[dict],
    session: AsyncSession | None = None,
) -> HybridContext:
    attraction = await get_attraction_context(attraction_name, session=session)
    profile = await get_profile_context(user_id, session=session)
    live_info = None
    if intent == "live_info":
        live_info = await get_live_info_context(query, attraction.name if attraction else attraction_name)

    return HybridContext(
        attraction=attraction,
        profile=profile,
        live_info=live_info,
        prompt_safe_attraction=project_attraction_for_prompt(attraction),
        prompt_safe_profile=project_profile_for_prompt(profile),
        session_context=session_context,
        dialogue_history=dialogue_history,
    )

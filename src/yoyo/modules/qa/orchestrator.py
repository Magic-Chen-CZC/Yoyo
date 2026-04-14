from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.hybrid_context_builder import build_hybrid_context
from yoyo.modules.qa.context_builder import build_context
from yoyo.modules.qa.domain_guard import is_supported_query
from yoyo.modules.qa.formatters import (
    format_attraction_answer,
    format_live_info_answer,
    format_planner_handoff_answer,
    format_translation_answer,
    format_trip_assistant_answer,
)
from yoyo.modules.qa.generator import generate_qa_answer
from yoyo.modules.qa.history import append_assistant_message, append_user_message, load_recent_history
from yoyo.modules.qa.intent_router import score_intent
from yoyo.modules.qa.planner_handoff import build_planner_handoff
from yoyo.modules.qa.retrieval import get_attraction_explanation
from yoyo.modules.qa.schemas import QAAskRequest, QAAskResponse
from yoyo.modules.qa.skill_registry import get_allowed_skills
from yoyo.modules.qa.validators import validate_answer
from yoyo.modules.session.service import get_guide_session, get_itinerary_version_plan


OUT_OF_SCOPE_MESSAGE = (
    "I can help with Beijing tour topics such as attractions, itinerary guidance, translation, and travel info."
)


# 这是 QA 模块最核心的总编排器。
# 当前阶段加入了：多轮历史记忆、SQL-first knowledge context、intent-aware metadata。
async def answer_question(session: AsyncSession, payload: QAAskRequest) -> QAAskResponse:
    if not is_supported_query(payload.query):
        return QAAskResponse(
            supported=False,
            intent="out_of_scope",
            answer=OUT_OF_SCOPE_MESSAGE,
            used_skills=[],
            metadata={},
        )

    session_context = await _load_session_context(session, payload.guide_session_id)
    dialogue_history = await load_recent_history(session, payload.guide_session_id)
    intent_result = score_intent(payload.query, dialogue_history)
    intent = str(intent_result["intent"])
    allowed_skills = get_allowed_skills(intent)

    await append_user_message(
        session,
        guide_session_id=payload.guide_session_id,
        intent=intent,
        content=payload.query,
        metadata={
            "language": payload.language,
            "request_context": payload.context,
            "intent_router": intent_result,
        },
    )

    hybrid_context = await build_hybrid_context(
        intent=intent,
        query=payload.query,
        attraction_name=_resolve_attraction_name(payload.query, session_context, dialogue_history),
        user_id=payload.user_id or _as_str(payload.context.get("user_id")),
        session_context=session_context,
        dialogue_history=dialogue_history,
        session=session,
    )
    context = build_context(
        payload.query,
        payload.language,
        payload.context,
        {
            **session_context,
            "dialogue_history": dialogue_history,
            "hybrid_context": hybrid_context.model_dump() if hybrid_context else {},
        },
    )

    answer, extra_metadata = await _generate_answer(intent, payload.query, payload.language, session_context, hybrid_context)
    combined_metadata = {
        "context": context,
        "intent_router": intent_result,
        **extra_metadata,
    }
    validation = validate_answer(intent, answer, combined_metadata)
    combined_metadata["validation"] = validation

    await append_assistant_message(
        session,
        guide_session_id=payload.guide_session_id,
        intent=intent,
        content=answer,
        metadata=combined_metadata,
        valid=bool(validation.get("valid")),
    )

    return QAAskResponse(
        supported=True,
        intent=intent,
        answer=answer,
        used_skills=allowed_skills,
        metadata=combined_metadata,
    )


async def _load_session_context(session: AsyncSession, guide_session_id: str | None) -> dict[str, object]:
    if guide_session_id is None:
        return {}

    guide_session = await get_guide_session(session, guide_session_id)
    if guide_session is None:
        return {}

    plan = await get_itinerary_version_plan(session, guide_session.itinerary_version_id)
    stops = plan.get("stops", []) if plan else []
    raw_index = guide_session.context.get("current_stop_index", 0)
    current_index = raw_index if isinstance(raw_index, int) and raw_index >= 0 else 0
    if current_index >= len(stops):
        current_index = 0

    current_stop = stops[current_index] if len(stops) > current_index else None
    next_stop = stops[current_index + 1] if len(stops) > current_index + 1 else None

    return {
        "guide_session_id": guide_session.id,
        "itinerary_version_id": guide_session.itinerary_version_id,
        "itinerary_id": guide_session.itinerary_id,
        "playback_state": guide_session.context.get("playback_state"),
        "current_stop_index": current_index,
        "current_stop_name": _safe_get(current_stop, "name"),
        "current_stop_id": _safe_get(current_stop, "id"),
        "current_stop_category": _safe_get(current_stop, "category"),
        "next_stop_name": _safe_get(next_stop, "name"),
        "next_stop_id": _safe_get(next_stop, "id"),
        "stop_count": len(stops),
        "remaining_stop_count": max(0, len(stops) - current_index - 1),
        "plan_summary": plan.get("summary") if plan else None,
    }



async def _generate_answer(
    intent: str,
    query: str,
    language: str,
    session_context: dict[str, object],
    hybrid_context,
) -> tuple[str, dict[str, object]]:
    settings = get_settings()
    profile = hybrid_context.profile if hybrid_context else None
    attraction = hybrid_context.attraction if hybrid_context else None
    live_info = hybrid_context.live_info if hybrid_context else None

    if intent in {"translation", "live_info", "trip_assistant", "attraction_explain"}:
        llm_answer, llm_metadata = await generate_qa_answer(
            provider=settings.llm_provider,
            model=settings.llm_model,
            intent=intent,
            query=query,
            language=language,
            hybrid_context=hybrid_context,
        )
        if llm_answer:
            extra = {
                "attraction": attraction.model_dump() if attraction else None,
                "profile": profile.model_dump() if profile else None,
                **llm_metadata,
            }
            if intent == "live_info":
                extra.update(
                    {
                        "sources": live_info.sources if live_info else [],
                        "updated_at": live_info.updated_at if live_info else None,
                        "not_confirmed": live_info.not_confirmed if live_info else True,
                        "confidence": live_info.confidence if live_info else "low",
                    }
                )
            return llm_answer, extra

    if intent == "translation":
        return format_translation_answer(query), {"profile": profile.model_dump() if profile else None, "llm": {"fallback_used": True}}

    if intent == "live_info":
        summary = live_info.summary if live_info else "No live information is currently available."
        answer = format_live_info_answer(summary, live_info.not_confirmed if live_info else True, attraction.name if attraction else None)
        return answer, {
            "sources": live_info.sources if live_info else [],
            "updated_at": live_info.updated_at if live_info else None,
            "not_confirmed": live_info.not_confirmed if live_info else True,
            "confidence": live_info.confidence if live_info else "low",
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "llm": {"fallback_used": True},
        }

    if intent == "trip_assistant":
        answer = format_trip_assistant_answer(
            _as_str(session_context.get("current_stop_name")),
            _as_str(session_context.get("next_stop_name")),
            _as_int(session_context.get("stop_count")),
            _as_str(session_context.get("plan_summary")),
            profile.travel_style if profile else None,
            profile.walking_preference if profile else None,
            _as_int(session_context.get("remaining_stop_count")),
            profile.guide_style_preference if profile else None,
        )
        return answer, {
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "llm": {"fallback_used": True},
        }

    if intent == "planner_handoff":
        available_stops = _build_available_stop_names(session_context)
        handoff = build_planner_handoff(query, available_stops)
        answer = format_planner_handoff_answer(handoff.operation, handoff.target, handoff.constraints)
        return answer, {
            "planner_handoff": handoff.model_dump(),
            "profile": profile.model_dump() if profile else None,
        }

    retrieval = get_attraction_explanation(
        attraction.name if attraction else _as_str(session_context.get("current_stop_name")),
        attraction=attraction,
    )
    if retrieval is not None:
        answer = format_attraction_answer(
            str(retrieval["name"]),
            str(retrieval["summary"]),
            str(retrieval["history"]),
            list(retrieval["tips"]),
            list(retrieval.get("highlights", [])),
            _as_str(retrieval.get("category")),
            profile.guide_style_preference if profile else None,
        )
        return answer, {
            "retrieval": retrieval,
            "profile": profile.model_dump() if profile else None,
            "llm": {"fallback_used": True},
        }

    fallback_name = attraction.name if attraction else _as_str(session_context.get("current_stop_name")) or "this attraction"
    return (
        f"{fallback_name}: I can give a brief overview once more attraction details are available in the SQL knowledge store.",
        {
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "llm": {"fallback_used": True},
        },
    )



def _build_available_stop_names(session_context: dict[str, object]) -> list[str]:
    names = []
    current_name = _as_str(session_context.get("current_stop_name"))
    next_name = _as_str(session_context.get("next_stop_name"))
    if current_name:
        names.append(current_name)
    if next_name and next_name not in names:
        names.append(next_name)
    return names



def _resolve_attraction_name(
    query: str,
    session_context: dict[str, object],
    dialogue_history: list[dict[str, object]],
) -> str | None:
    current_name = _as_str(session_context.get("current_stop_name"))
    next_name = _as_str(session_context.get("next_stop_name"))
    lowered = query.lower()
    if next_name and any(token in lowered for token in ["next", "after", "下一站"]):
        return next_name
    if current_name:
        return current_name
    for item in reversed(dialogue_history):
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            retrieval = metadata.get("retrieval")
            if isinstance(retrieval, dict):
                name = retrieval.get("name")
                if isinstance(name, str):
                    return name
    return None



def _safe_get(value: object, key: str) -> str | None:
    if isinstance(value, dict):
        inner = value.get(key)
        if isinstance(inner, str):
            return inner
    return None



def _as_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None



def _as_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None

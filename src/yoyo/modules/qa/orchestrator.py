from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.hybrid_context_builder import build_hybrid_context
from yoyo.modules.qa.context_builder import build_context
from yoyo.modules.qa.domain_guard import is_supported_query
from yoyo.modules.qa.formatters import (
    format_attraction_answer,
    format_live_info_answer,
    format_manual_route_edit_redirect_answer,
    format_translation_answer,
    format_trip_assistant_answer,
)
from yoyo.modules.qa.generator import generate_qa_answer
from yoyo.modules.qa.history import append_assistant_message, append_user_message, load_recent_history
from yoyo.modules.qa.intent_router import score_intent
from yoyo.modules.qa.retrieval import get_attraction_explanation
from yoyo.modules.qa.schemas import QAAskRequest, QAAskResponse
from yoyo.modules.qa.skill_registry import get_allowed_skills
from yoyo.modules.qa.validators import validate_answer
from yoyo.modules.session.service import get_guide_session_current


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


def _looks_like_manual_route_edit_request(query: str) -> bool:
    lowered = query.lower().strip()
    return any(
        token in lowered
        for token in [
            "replace",
            "swap",
            "remove",
            "delete",
            "change route",
            "reorder",
            "move",
            "shorten",
            "fewer",
            "less walking",
            "easier route",
            "换一个",
            "删掉",
            "调整路线",
        ]
    )


async def _load_session_context(session: AsyncSession, guide_session_id: str | None) -> dict[str, object]:
    if guide_session_id is None:
        return {}

    current = await get_guide_session_current(session, guide_session_id)
    if current is None:
        return {}

    current_stop = current.current_stop or None
    next_stop = current.next_stop or None

    return {
        "guide_session_id": current.guide_session_id,
        "itinerary_version_id": current.itinerary_version_id,
        "itinerary_id": current.itinerary_id,
        "playback_state": current.playback_state,
        "current_stop_index": current.current_stop_index,
        "current_stop_name": _safe_get(current_stop, "name"),
        "current_stop_id": _safe_get(current_stop, "id"),
        "current_stop_category": _safe_get(current_stop, "category"),
        "next_stop_name": _safe_get(next_stop, "name"),
        "next_stop_id": _safe_get(next_stop, "id"),
        "stop_count": current.stop_count,
        "remaining_stop_count": max(current.stop_count - current.completed_stop_count - 1, 0),
        "plan_summary": current.plan_summary,
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
    rag = hybrid_context.rag if hybrid_context else None

    route_edit_requested = intent == "trip_assistant" and _looks_like_manual_route_edit_request(query)
    llm_attempt_metadata: dict[str, object] | None = None

    if intent in {"translation", "live_info", "trip_assistant", "attraction_explain"} and not route_edit_requested:
        llm_answer, llm_attempt_metadata = await generate_qa_answer(
            provider=settings.llm_provider,
            model=settings.llm_model,
            intent=intent,
            query=query,
            language=language,
            hybrid_context=hybrid_context,
        )
        if llm_answer:
            structured = ((llm_attempt_metadata.get("llm") or {}).get("structured_output") or {})
            extra = {
                "attraction": attraction.model_dump() if attraction else None,
                "profile": profile.model_dump() if profile else None,
                "rag": rag.model_dump() if rag else None,
                "retrieval_strategy": rag.retrieval_mode if rag else "sql_only",
                "rag_retrieval_mode": rag.retrieval_mode if rag else "sql_only",
                "rag_backend_ready": (
                    rag.chunks[0].metadata.get("backend_ready") if rag and rag.chunks else False
                ),
                "rag_backend_reason": (
                    rag.chunks[0].metadata.get("backend_reason") if rag and rag.chunks else None
                ),
                "rag_query_status": (
                    rag.chunks[0].metadata.get("query_status") if rag and rag.chunks else None
                ),
                "rag_query_reason": (
                    rag.chunks[0].metadata.get("query_reason") if rag and rag.chunks else None
                ),
                **llm_attempt_metadata,
            }
            if intent == "translation":
                extra.update(
                    {
                        "structured": structured,
                        "degraded": structured.get("status") == "degraded",
                        "degraded_reason": structured.get("reason"),
                    }
                )
            if intent == "live_info":
                extra.update(
                    {
                        "sources": live_info.sources if live_info else [],
                        "updated_at": live_info.updated_at if live_info else None,
                        "not_confirmed": structured.get("not_confirmed", live_info.not_confirmed if live_info else True),
                        "confidence": structured.get("confidence", live_info.confidence if live_info else "low"),
                        "status": structured.get("status", live_info.status if live_info else "available"),
                        "reason": structured.get("reason", live_info.reason if live_info else None),
                        "structured": structured,
                        "degraded": structured.get("status") in {"degraded", "unavailable"},
                        "degraded_reason": structured.get("reason"),
                    }
                )
            if intent == "trip_assistant":
                manual_route_edit_redirect = structured.get("status") == "redirect" or structured.get("route_focus") == "manual_edit_redirect"
                extra.update(
                    {
                        "status": structured.get("status", "ok"),
                        "reason": structured.get("reason"),
                        "route_focus": structured.get("route_focus"),
                        "references_current_stop": structured.get("references_current_stop", False),
                        "references_next_stop": structured.get("references_next_stop", False),
                        "structured": structured,
                        "manual_route_edit_redirect": manual_route_edit_redirect,
                        "degraded": structured.get("status") == "degraded",
                        "degraded_reason": structured.get("reason") if structured.get("status") == "degraded" else None,
                    }
                )
            if intent == "attraction_explain":
                extra.update(
                    {
                        "status": structured.get("status", "ok"),
                        "reason": structured.get("reason"),
                        "grounding": structured.get("grounding"),
                        "includes_history": structured.get("includes_history", False),
                        "includes_tips": structured.get("includes_tips", False),
                        "structured": structured,
                        "degraded": structured.get("status") in {"degraded", "unavailable"},
                        "degraded_reason": structured.get("reason") if structured.get("status") in {"degraded", "unavailable"} else None,
                    }
                )
            return llm_answer, extra

    if intent == "translation":
        return format_translation_answer(query), {
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": rag.retrieval_mode if rag else "sql_only",
            **_build_llm_fallback_metadata(llm_attempt_metadata),
            "degraded": True,
            "degraded_reason": "runtime_translation_unavailable",
        }

    if intent == "live_info":
        summary = live_info.summary if live_info else "Live information is currently unavailable."
        answer = format_live_info_answer(summary, live_info.not_confirmed if live_info else True, attraction.name if attraction else None)
        return answer, {
            "sources": live_info.sources if live_info else [],
            "updated_at": live_info.updated_at if live_info else None,
            "not_confirmed": live_info.not_confirmed if live_info else True,
            "confidence": live_info.confidence if live_info else "low",
            "status": live_info.status if live_info else "unavailable",
            "reason": live_info.reason if live_info else "live_info_unavailable",
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": rag.retrieval_mode if rag else "sql_only",
            "rag_retrieval_mode": rag.retrieval_mode if rag else "sql_only",
            "rag_backend_ready": (
                rag.chunks[0].metadata.get("backend_ready") if rag and rag.chunks else False
            ),
            "rag_backend_reason": (
                rag.chunks[0].metadata.get("backend_reason") if rag and rag.chunks else None
            ),
            "rag_query_status": (
                rag.chunks[0].metadata.get("query_status") if rag and rag.chunks else None
            ),
            "rag_query_reason": (
                rag.chunks[0].metadata.get("query_reason") if rag and rag.chunks else None
            ),
            **_build_llm_fallback_metadata(llm_attempt_metadata),
            "degraded": (live_info.status != "available") if live_info else True,
            "degraded_reason": live_info.reason if live_info else "live_info_unavailable",
        }

    if intent == "trip_assistant":
        route_edit_requested = _looks_like_manual_route_edit_request(query)
        if route_edit_requested:
            answer = format_manual_route_edit_redirect_answer()
        else:
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
        fallback_reason = _trip_assistant_fallback_reason(llm_attempt_metadata)
        return answer, {
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": rag.retrieval_mode if rag else "sql_only",
            **_build_llm_fallback_metadata(llm_attempt_metadata),
            "status": "redirect" if route_edit_requested else "degraded",
            "reason": "manual_route_edit_redirect" if route_edit_requested else fallback_reason,
            "route_focus": "manual_edit_redirect" if route_edit_requested else "route_overview",
            "manual_route_edit_redirect": route_edit_requested,
            "degraded": not route_edit_requested,
            "degraded_reason": None if route_edit_requested else fallback_reason,
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
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": rag.retrieval_mode if rag else "sql_only",
            "rag_retrieval_mode": rag.retrieval_mode if rag else "sql_only",
            "rag_backend_ready": (
                rag.chunks[0].metadata.get("backend_ready") if rag and rag.chunks else False
            ),
            "rag_backend_reason": (
                rag.chunks[0].metadata.get("backend_reason") if rag and rag.chunks else None
            ),
            "rag_query_status": (
                rag.chunks[0].metadata.get("query_status") if rag and rag.chunks else None
            ),
            "rag_query_reason": (
                rag.chunks[0].metadata.get("query_reason") if rag and rag.chunks else None
            ),
            **_build_llm_fallback_metadata(llm_attempt_metadata),
            "status": "ok",
            "reason": None,
            "grounding": _normalize_grounding(retrieval.get("source_type")),
            "includes_history": bool(retrieval.get("history")),
            "includes_tips": bool(retrieval.get("tips")),
            "degraded": False,
            "degraded_reason": None,
        }

    fallback_name = attraction.name if attraction else _as_str(session_context.get("current_stop_name")) or "this attraction"
    if rag is not None and rag.chunks:
        rag_snippet = rag.chunks[0].text.strip()
        return (
            f"I can share a limited background note about {fallback_name}: {rag_snippet}",
            {
                "attraction": attraction.model_dump() if attraction else None,
                "profile": profile.model_dump() if profile else None,
                "rag": rag.model_dump(),
                "retrieval_strategy": rag.retrieval_mode,
                "rag_retrieval_mode": rag.retrieval_mode,
                "rag_backend_ready": rag.chunks[0].metadata.get("backend_ready"),
                "rag_backend_reason": rag.chunks[0].metadata.get("backend_reason"),
                "rag_query_status": rag.chunks[0].metadata.get("query_status"),
                "rag_query_reason": rag.chunks[0].metadata.get("query_reason"),
                **_build_llm_fallback_metadata(llm_attempt_metadata),
                "status": "degraded",
                "reason": "rag_snippet_only",
                "grounding": "rag",
                "includes_history": False,
                "includes_tips": False,
                "degraded": True,
                "degraded_reason": "rag_snippet_only",
            },
        )
    return (
        f"I don't have enough confirmed detail to explain {fallback_name} clearly yet. Please try again shortly, or ask me about another stop on your route.",
        {
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": rag.retrieval_mode if rag else "sql_only",
            "rag_retrieval_mode": rag.retrieval_mode if rag else "sql_only",
            "rag_backend_ready": (
                rag.chunks[0].metadata.get("backend_ready") if rag and rag.chunks else False
            ),
            "rag_backend_reason": (
                rag.chunks[0].metadata.get("backend_reason") if rag and rag.chunks else None
            ),
            "rag_query_status": (
                rag.chunks[0].metadata.get("query_status") if rag and rag.chunks else None
            ),
            "rag_query_reason": (
                rag.chunks[0].metadata.get("query_reason") if rag and rag.chunks else None
            ),
            **_build_llm_fallback_metadata(llm_attempt_metadata),
            "status": "unavailable",
            "reason": "insufficient_grounded_attraction_detail",
            "grounding": "limited",
            "includes_history": False,
            "includes_tips": False,
            "degraded": True,
            "degraded_reason": "insufficient_grounded_attraction_detail",
        },
    )



def _build_llm_fallback_metadata(llm_attempt_metadata: dict[str, object] | None) -> dict[str, object]:
    if llm_attempt_metadata is None:
        return {"llm": {"fallback_used": True}}
    llm_metadata = llm_attempt_metadata.get("llm")
    if not isinstance(llm_metadata, dict):
        return {"llm": {"fallback_used": True}}
    fallback_llm_metadata = dict(llm_metadata)
    fallback_llm_metadata["fallback_used"] = True
    return {"llm": fallback_llm_metadata}



def _normalize_grounding(source_type: object) -> str:
    if not isinstance(source_type, str):
        return "limited"
    lowered = source_type.lower()
    if "rag" in lowered:
        return "rag"
    if any(token in lowered for token in ["sql", "postgres"]):
        return "sql"
    return "limited"



def _trip_assistant_fallback_reason(llm_attempt_metadata: dict[str, object] | None) -> str:
    llm_metadata = (llm_attempt_metadata or {}).get("llm")
    if isinstance(llm_metadata, dict) and llm_metadata.get("structured_output_valid") is False:
        return "trip_assistant_structured_output_invalid"
    return "trip_assistant_runtime_unavailable"



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

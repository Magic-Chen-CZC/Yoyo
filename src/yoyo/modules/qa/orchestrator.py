import re
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.attraction_retriever import resolve_attraction_name_candidate
from yoyo.modules.knowledge.hybrid_context_builder import build_hybrid_context
from yoyo.modules.qa.context_builder import build_context
from yoyo.modules.qa.domain_guard import evaluate_domain_support
from yoyo.modules.qa.formatters import (
    format_attraction_answer,
    format_live_info_answer,
    format_manual_route_edit_redirect_answer,
    format_navigation_text_answer,
    format_smalltalk_answer,
    format_trip_assistant_answer,
    format_weather_info_answer,
)
from yoyo.modules.qa.generator import generate_qa_answer
from yoyo.modules.qa.history import append_assistant_message, append_user_message, load_recent_history
from yoyo.modules.qa.intent_router import score_intent
from yoyo.modules.qa.playground import (
    apply_hybrid_context_playground_overrides,
    merge_session_context_with_playground,
    resolve_dialogue_history_for_playground,
)
from yoyo.modules.qa.prompts import build_qa_generation_request
from yoyo.modules.qa.retrieval import get_attraction_explanation
from yoyo.modules.qa.router_fallback import resolve_router_fallback
from yoyo.modules.qa.schemas import IntentRouterFallbackResult, QAAskRequest, QAAskResponse, QAResolvedQuery
from yoyo.modules.qa.skill_registry import get_allowed_skills
from yoyo.modules.qa.validators import validate_answer
from yoyo.modules.session.service import get_guide_session_current
from yoyo.modules.translator.service import preprocess_query, translate_answer, translate_for_qa


OUT_OF_SCOPE_MESSAGE = "我目前主要能帮助你处理北京旅游相关问题，比如景点介绍、行程引导、翻译、天气、文字导航和官方景点通知。"


def _short_circuit_latency(*, started_at: float, preprocess_ms: int, routing_ms: int) -> dict[str, int]:
    return {
        "preprocess_ms": preprocess_ms,
        "routing_ms": routing_ms,
        "context_build_ms": 0,
        "generation_ms": 0,
        "postprocess_ms": 0,
        "total_ms": _elapsed_ms(started_at),
    }

_BOUNDARY_TOPIC_MESSAGE = (
    "这类实时话题我这里暂时还不能稳定确认；如果你要看交通或拥挤情况，建议直接查看对应的实时服务。"
    "我仍然可以继续帮你处理北京景点、行程引导、翻译、天气、文字导航和官方景点通知。"
)


# 这是 QA 模块最核心的总编排器。
# 当前阶段加入了：多轮历史记忆、SQL-first knowledge context、intent-aware metadata。
async def answer_question(session: AsyncSession, payload: QAAskRequest) -> QAAskResponse:
    started_at = perf_counter()
    settings = get_settings()
    session_context = await _load_session_context(session, payload.guide_session_id)
    session_context, playground_applied = merge_session_context_with_playground(session_context, payload.context)
    dialogue_history = await load_recent_history(session, payload.guide_session_id)
    dialogue_history = resolve_dialogue_history_for_playground(dialogue_history, payload.context, playground_applied)
    preprocessing_started_at = perf_counter()
    resolved_query, preprocessing_metadata = await _resolve_query(payload.query, payload.language)
    preprocess_ms = _elapsed_ms(preprocessing_started_at)
    routing_started_at = perf_counter()
    domain_guard = evaluate_domain_support(_domain_guard_query(resolved_query))
    pending_navigation_clarification = _latest_navigation_place_clarification(dialogue_history)
    navigation_clarification_selection = _resolve_pending_navigation_clarification_selection(
        resolved_query.effective_query,
        dialogue_history,
    )
    if navigation_clarification_selection is not None:
        intent_rule_result = {
            "intent": "navigation_text",
            "confidence": 1.0,
            "margin": 1.0,
            "needs_fallback": False,
            "fallback_reason": None,
            "signals": ["navigation_place_clarification_selection"],
            "candidates": {"navigation_text": 1.0},
            "runner_up_intent": None,
            "last_intent": _last_intent(dialogue_history),
        }
    else:
        intent_rule_result = score_intent(
            resolved_query.effective_query,
            dialogue_history,
            raw_query=resolved_query.raw_query,
        )
    fallback_result = None
    fallback_metadata = None
    final_intent_result = dict(intent_rule_result)

    fallback_reason = intent_rule_result.get("fallback_reason")
    should_try_fallback = (
        domain_guard.supported
        and settings.qa_router_fallback_enabled
        and (
            bool(intent_rule_result.get("needs_fallback"))
            or _should_try_pending_clarification_fallback(
                pending_navigation_clarification,
                navigation_clarification_selection,
                intent_rule_result,
            )
        )
        and fallback_reason not in {"boundary_topic_conflict"}
        and intent_rule_result.get("intent") != "manual_route_edit_redirect"
    )
    if should_try_fallback:
        fallback_result, fallback_metadata = await resolve_router_fallback(
            query=resolved_query.effective_query,
            raw_query=resolved_query.raw_query,
            pivot_query=resolved_query.pivot_query,
            language=resolved_query.processing_language,
            market=_as_str(payload.context.get("market")),
            dialogue_history=dialogue_history,
            rule_result=intent_rule_result,
            session_context=session_context,
            pending_clarification=pending_navigation_clarification if navigation_clarification_selection is None else None,
        )
        if fallback_result is not None:
            fallback_selection = _navigation_clarification_selection_from_fallback(
                fallback_result,
                pending_navigation_clarification,
            )
            if fallback_selection is not None:
                navigation_clarification_selection = fallback_selection
                final_intent_result = {
                    **intent_rule_result,
                    "intent": "navigation_text",
                    "confidence": fallback_result.confidence,
                    "needs_fallback": False,
                    "fallback_reason": intent_rule_result.get("fallback_reason"),
                    "clarification_action": fallback_result.clarification_action,
                    "selected_index": fallback_result.selected_index,
                }
            else:
                final_intent_result = {
                    **intent_rule_result,
                    "intent": fallback_result.intent,
                    "confidence": max(float(intent_rule_result.get("confidence", 0.0)), fallback_result.confidence),
                    "needs_fallback": False,
                    "fallback_reason": intent_rule_result.get("fallback_reason"),
                    "clarification_action": fallback_result.clarification_action,
                    "selected_index": fallback_result.selected_index,
                }
                if fallback_result.intent == "weather_info":
                    final_intent_result["weather_location_name"] = fallback_result.weather_location_name
    routing_ms = _elapsed_ms(routing_started_at)

    intent = str(final_intent_result["intent"])
    allowed_skills = get_allowed_skills(intent)
    boundary_topic = final_intent_result.get("boundary_topic")
    out_of_scope_subtype = final_intent_result.get("out_of_scope_subtype")
    router_metadata = {
        "rule_result": intent_rule_result,
        "fallback_result": fallback_result.model_dump() if fallback_result else fallback_metadata,
        "final_result": final_intent_result,
        "preprocessing": preprocessing_metadata,
        "latency_ms": routing_ms,
    }

    if domain_guard.hard_deny:
        return QAAskResponse(
            supported=False,
            intent="out_of_scope",
            answer=OUT_OF_SCOPE_MESSAGE,
            used_skills=[],
            metadata={
                "domain_guard": domain_guard.model_dump(),
                "intent_router": {
                    **router_metadata,
                    "final_result": {
                        **intent_rule_result,
                        "intent": "out_of_scope",
                        "out_of_scope_subtype": "general_out_of_scope",
                    },
                },
                "boundary_redirect": False,
                "boundary_topic": None,
                "out_of_scope_subtype": "general_out_of_scope",
                "resolved_query": resolved_query.model_dump(),
                "latency_ms": _short_circuit_latency(
                    started_at=started_at,
                    preprocess_ms=preprocess_ms,
                    routing_ms=routing_ms,
                ),
            },
        )

    if not domain_guard.supported and intent == "out_of_scope":
        return QAAskResponse(
            supported=False,
            intent="out_of_scope",
            answer=OUT_OF_SCOPE_MESSAGE,
            used_skills=[],
            metadata={
                "domain_guard": domain_guard.model_dump(),
                "intent_router": router_metadata,
                "boundary_redirect": False,
                "boundary_topic": None,
                "out_of_scope_subtype": out_of_scope_subtype or "general_out_of_scope",
                "resolved_query": resolved_query.model_dump(),
                "latency_ms": _short_circuit_latency(
                    started_at=started_at,
                    preprocess_ms=preprocess_ms,
                    routing_ms=routing_ms,
                ),
            },
        )

    if intent == "out_of_scope":
        boundary_message = _boundary_topic_message(resolved_query.effective_query)
        return QAAskResponse(
            supported=False,
            intent="out_of_scope",
            answer=boundary_message or OUT_OF_SCOPE_MESSAGE,
            used_skills=[],
            metadata={
                "domain_guard": domain_guard.model_dump(),
                "intent_router": router_metadata,
                "boundary_redirect": boundary_message is not None,
                "boundary_topic": boundary_topic,
                "out_of_scope_subtype": out_of_scope_subtype or "general_out_of_scope",
                "resolved_query": resolved_query.model_dump(),
                "latency_ms": _short_circuit_latency(
                    started_at=started_at,
                    preprocess_ms=preprocess_ms,
                    routing_ms=routing_ms,
                ),
            },
        )

    if intent == "manual_route_edit_redirect":
        return QAAskResponse(
            supported=True,
            intent="manual_route_edit_redirect",
            answer=format_manual_route_edit_redirect_answer(),
            used_skills=allowed_skills,
            metadata={
                "domain_guard": domain_guard.model_dump(),
                "intent_router": router_metadata,
                "status": "redirect",
                "reason": "manual_route_edit_redirect",
                "route_focus": "manual_edit_redirect",
                "manual_route_edit_redirect": True,
                "degraded": False,
                "degraded_reason": None,
                "resolved_query": resolved_query.model_dump(),
                "latency_ms": _short_circuit_latency(
                    started_at=started_at,
                    preprocess_ms=preprocess_ms,
                    routing_ms=routing_ms,
                ),
            },
        )

    if intent == "smalltalk":
        return QAAskResponse(
            supported=True,
            intent="smalltalk",
            answer=format_smalltalk_answer(resolved_query.raw_query),
            used_skills=allowed_skills,
            metadata={
                "domain_guard": domain_guard.model_dump(),
                "intent_router": router_metadata,
                "status": "ok",
                "reason": "smalltalk_supported",
                "degraded": False,
                "degraded_reason": None,
                "resolved_query": resolved_query.model_dump(),
                "latency_ms": {
                    "preprocess_ms": preprocess_ms,
                    "routing_ms": routing_ms,
                    "context_build_ms": 0,
                    "generation_ms": 0,
                    "postprocess_ms": 0,
                    "total_ms": _elapsed_ms(started_at),
                },
            },
        )

    await append_user_message(
        session,
        guide_session_id=payload.guide_session_id,
        intent=intent,
        content=resolved_query.raw_query,
        metadata={
            "language": payload.language,
            "request_context": payload.context,
            "resolved_query": resolved_query.model_dump(),
            "intent_router": router_metadata,
        },
    )

    context_build_started_at = perf_counter()
    resolved_attraction_name = _resolve_attraction_name(
        _entity_resolution_query(resolved_query),
        session_context,
        dialogue_history,
    )
    routing_session_context = {
        **session_context,
        "weather_location_name": _as_str(final_intent_result.get("weather_location_name")),
    }
    if navigation_clarification_selection is not None:
        routing_session_context["navigation_clarification_selection"] = navigation_clarification_selection
    hybrid_context = await build_hybrid_context(
        intent=intent,
        query=resolved_query.effective_query,
        attraction_name=resolved_attraction_name,
        user_id=payload.user_id or _as_str(payload.context.get("user_id")),
        session_context=routing_session_context,
        dialogue_history=dialogue_history,
        session=session,
    )
    hybrid_context = apply_hybrid_context_playground_overrides(
        hybrid_context,
        payload.context,
        session_context=session_context,
        dialogue_history=dialogue_history,
        fallback_user_id=payload.user_id or _as_str(payload.context.get("user_id")),
        applied=playground_applied,
    )
    context = build_context(
        resolved_query.effective_query,
        resolved_query.processing_language,
        payload.context,
        {
            **session_context,
            "dialogue_history": dialogue_history,
            "hybrid_context": hybrid_context.model_dump() if hybrid_context else {},
            "resolved_query": resolved_query.model_dump(),
        },
    )
    context_build_ms = _elapsed_ms(context_build_started_at)
    context_build_debug = getattr(hybrid_context, "build_debug", {}) if hybrid_context else {}

    generation_started_at = perf_counter()
    internal_answer, extra_metadata = await _generate_answer(
        intent,
        resolved_query.effective_query,
        resolved_query.user_language,
        resolved_query.processing_language,
        session_context,
        hybrid_context,
        payload.llm_provider,
        payload.llm_model,
        resolved_query.raw_query,
    )
    generation_ms = _elapsed_ms(generation_started_at)
    postprocess_started_at = perf_counter()
    final_answer, answer_translation_metadata = await _finalize_answer(
        intent=intent,
        internal_answer=internal_answer,
        user_language=resolved_query.user_language,
        processing_language=resolved_query.processing_language,
    )
    postprocess_ms = _elapsed_ms(postprocess_started_at)
    final_answer = _align_session_stop_names(final_answer, session_context)
    combined_metadata = {
        "context": context,
        "resolved_query": resolved_query.model_dump(),
        "domain_guard": domain_guard.model_dump(),
        "intent_router": router_metadata,
        "internal_answer": internal_answer,
        "output_language": resolved_query.user_language,
        "answer_translation": answer_translation_metadata,
        "requested_llm_provider": payload.llm_provider,
        "requested_llm_model": payload.llm_model,
        "playground": playground_applied.model_dump(),
        "latency_ms": {
            "preprocess_ms": preprocess_ms,
            "routing_ms": routing_ms,
            "context_build_ms": context_build_ms,
            "context_build_breakdown_ms": context_build_debug.get("timings_ms", {}),
            "generation_ms": generation_ms,
            "postprocess_ms": postprocess_ms,
            "total_ms": _elapsed_ms(started_at),
        },
        **extra_metadata,
    }
    validation = validate_answer(intent, final_answer, combined_metadata)
    combined_metadata["validation"] = validation

    await append_assistant_message(
        session,
        guide_session_id=payload.guide_session_id,
        intent=intent,
        content=final_answer,
        metadata=combined_metadata,
        valid=bool(validation.get("valid")),
    )

    return QAAskResponse(
        supported=True,
        intent=intent,
        answer=final_answer,
        used_skills=allowed_skills,
        metadata=combined_metadata,
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
        "city_code": current.city_code,
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
    user_language: str,
    processing_language: str,
    session_context: dict[str, object],
    hybrid_context,
    llm_provider_override: str | None = None,
    llm_model_override: str | None = None,
    raw_query: str | None = None,
) -> tuple[str, dict[str, object]]:
    settings = get_settings()
    profile = hybrid_context.profile if hybrid_context else None
    attraction = hybrid_context.attraction if hybrid_context else None
    live_info = hybrid_context.live_info if hybrid_context else None
    weather = hybrid_context.weather if hybrid_context else None
    navigation = hybrid_context.navigation if hybrid_context else None
    rag = hybrid_context.rag if hybrid_context else None

    llm_attempt_metadata: dict[str, object] | None = None
    llm_provider = llm_provider_override or settings.llm_provider
    llm_model = llm_model_override or settings.llm_model
    route_status_query = intent == "trip_assistant" and _looks_like_route_status_query(query, raw_query)

    if intent == "translation":
        translator_result = await translate_for_qa(
            query=raw_query or query,
            user_language=user_language,
            provider=_translator_provider(settings),
            model=_translator_model(settings),
            timeout_seconds=settings.translator_timeout_seconds,
            enabled=settings.translator_enabled,
            bilingual_enabled=settings.translator_bilingual_enabled,
        )
        llm_metadata = {
            "provider": translator_result.provider,
            "model": translator_result.model,
            "latency_ms": translator_result.latency_ms,
            "fallback_used": translator_result.degraded,
            "error": translator_result.llm_error,
        }
        if translator_result.structured_output_valid is not None:
            llm_metadata["structured_output_valid"] = translator_result.structured_output_valid
        return translator_result.text, {
            "translation": {
                "status": translator_result.status,
                "reason": translator_result.reason,
                "mode": translator_result.mode,
                "source_language": translator_result.source_language,
                "target_language": translator_result.target_language,
                "display_blocks": [block.model_dump() for block in translator_result.display_blocks],
                "user_visible_lines": translator_result.user_visible_lines,
                "execution_path": translator_result.execution_path,
                "degraded": translator_result.degraded,
                "degraded_reason": translator_result.reason,
                "provider": translator_result.provider,
                "model": translator_result.model,
                "latency_ms": translator_result.latency_ms,
            },
            "structured": {
                "status": translator_result.status,
                "reason": translator_result.reason,
                "mode": translator_result.mode,
            },
            "llm": llm_metadata,
            "degraded": translator_result.degraded,
            "degraded_reason": translator_result.reason,
        }

    if intent == "weather_info" and weather is not None and weather.status == "available":
        llm_answer, llm_attempt_metadata = await generate_qa_answer(
            provider=llm_provider,
            model=llm_model,
            intent=intent,
            query=query,
            language=processing_language,
            hybrid_context=hybrid_context,
        )
        if llm_answer:
            structured = ((llm_attempt_metadata.get("llm") or {}).get("structured_output") or {})
            return llm_answer, {
                "weather": weather.model_dump() if weather else None,
                "attraction": attraction.model_dump() if attraction else None,
                "profile": profile.model_dump() if profile else None,
                "status": structured.get("status", "ok"),
                "reason": structured.get("reason"),
                "structured": structured,
                "degraded": structured.get("status") in {"degraded", "unavailable"},
                "degraded_reason": structured.get("reason") if structured.get("status") in {"degraded", "unavailable"} else None,
                **llm_attempt_metadata,
            }
        llm_attempt_metadata = llm_attempt_metadata

    if intent == "weather_info":
        answer = format_weather_info_answer(
            weather.location_name if weather else None,
            weather.weather if weather else None,
            weather.temperature_celsius if weather else None,
            weather.wind_direction if weather else None,
            weather.wind_power if weather else None,
            weather.humidity if weather else None,
            weather.report_time if weather else None,
            degraded_reason=weather.reason if weather and weather.status != "available" else None,
        )
        return answer, {
            "weather": weather.model_dump() if weather else None,
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "status": weather.status if weather else "unavailable",
            "reason": weather.reason if weather else "weather_unavailable",
            "degraded": (weather.status != "available") if weather else True,
            "degraded_reason": weather.reason if weather else "weather_unavailable",
            **_build_llm_fallback_metadata(llm_attempt_metadata),
        }

    if intent == "navigation_text":
        answer = format_navigation_text_answer(
            navigation.origin_name if navigation else None,
            navigation.destination_name if navigation else None,
            navigation.steps if navigation else [],
            navigation.distance_meters if navigation else None,
            navigation.duration_seconds if navigation else None,
            degraded_reason=navigation.reason if navigation and navigation.status != "available" else None,
            legs=navigation.legs if navigation else None,
            clarification=navigation.clarification if navigation and navigation.status == "clarification" else None,
        )
        status = navigation.status if navigation else "unavailable"
        degraded = status not in {"available", "clarification"}
        return answer, {
            "navigation": navigation.model_dump() if navigation else None,
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "status": status,
            "reason": navigation.reason if navigation else "navigation_unavailable",
            "degraded": degraded,
            "degraded_reason": navigation.reason if degraded and navigation else ("navigation_unavailable" if degraded else None),
            "llm": {"fallback_used": True},
        }

    if intent == "live_info" and (live_info is None or live_info.status == "unavailable"):
        answer = format_live_info_answer(
            live_info.summary if live_info and live_info.summary else "暂时还没有可确认的实时信息",
            True,
            attraction.name if attraction else None,
        )
        return answer, {
            "sources": live_info.sources if live_info else [],
            "updated_at": live_info.updated_at if live_info else None,
            "not_confirmed": True,
            "confidence": live_info.confidence if live_info else "low",
            "status": live_info.status if live_info else "unavailable",
            "reason": live_info.reason if live_info else "live_info_unavailable",
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": _retrieval_strategy(attraction, rag),
            "rag_retrieval_mode": _rag_retrieval_mode(rag),
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
            "llm": {"fallback_used": True},
            "degraded": True,
            "degraded_reason": live_info.reason if live_info else "live_info_unavailable",
        }

    if intent in {"live_info", "trip_assistant", "attraction_explain"} and not route_status_query:
        llm_answer, llm_attempt_metadata = await generate_qa_answer(
            provider=llm_provider,
            model=llm_model,
            intent=intent,
            query=query,
            language=processing_language,
            hybrid_context=hybrid_context,
        )
        if llm_answer:
            structured = ((llm_attempt_metadata.get("llm") or {}).get("structured_output") or {})
            extra = {
                "attraction": attraction.model_dump() if attraction else None,
                "profile": profile.model_dump() if profile else None,
                "rag": rag.model_dump() if rag else None,
                "retrieval_strategy": _retrieval_strategy(attraction, rag),
                "rag_retrieval_mode": _rag_retrieval_mode(rag),
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
                        **_live_info_cache_metadata(live_info),
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
                        "grounding": _attraction_grounding(structured.get("grounding"), attraction, rag),
                        "includes_history": structured.get("includes_history", False),
                        "includes_tips": structured.get("includes_tips", False),
                        "structured": structured,
                        "degraded": structured.get("status") in {"degraded", "unavailable"},
                        "degraded_reason": structured.get("reason") if structured.get("status") in {"degraded", "unavailable"} else None,
                    }
                )
            return llm_answer, extra

    if intent == "live_info":
        summary = live_info.summary if live_info else "暂时还没有可确认的实时信息。"
        answer = format_live_info_answer(summary, live_info.not_confirmed if live_info else True, attraction.name if attraction else None)
        return answer, {
            "sources": live_info.sources if live_info else [],
            "updated_at": live_info.updated_at if live_info else None,
            "not_confirmed": live_info.not_confirmed if live_info else True,
            "confidence": live_info.confidence if live_info else "low",
            "status": live_info.status if live_info else "unavailable",
            "reason": live_info.reason if live_info else "live_info_unavailable",
            **_live_info_cache_metadata(live_info),
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": _retrieval_strategy(attraction, rag),
            "rag_retrieval_mode": _rag_retrieval_mode(rag),
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
        current_stop_name = _as_str(session_context.get("current_stop_name"))
        next_stop_name = _as_str(session_context.get("next_stop_name"))
        answer = format_trip_assistant_answer(
            current_stop_name,
            next_stop_name,
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
            "retrieval_strategy": _retrieval_strategy(attraction, rag),
            **_build_llm_fallback_metadata(llm_attempt_metadata),
            "status": "ok" if route_status_query and current_stop_name else "degraded",
            "reason": None if route_status_query and current_stop_name else fallback_reason,
            "route_focus": "current_stop" if route_status_query and current_stop_name else "route_overview",
            "references_current_stop": bool(route_status_query and current_stop_name),
            "references_next_stop": bool(route_status_query and next_stop_name),
            "manual_route_edit_redirect": False,
            "degraded": False if route_status_query and current_stop_name else True,
            "degraded_reason": None if route_status_query and current_stop_name else fallback_reason,
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
            "retrieval_strategy": _retrieval_strategy(attraction, rag),
            "rag_retrieval_mode": _rag_retrieval_mode(rag),
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

    fallback_name = attraction.name if attraction else _as_str(session_context.get("current_stop_name")) or "这个景点"
    if rag is not None and rag.chunks:
        rag_snippet = rag.chunks[0].text.strip()
        return (
            f"我现在能先告诉你一条关于{fallback_name}的补充信息：{rag_snippet}",
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
        f"我暂时还没有足够可靠的信息把{fallback_name}讲清楚，你可以稍后再试，或者先问我路线里的其他站点。",
        {
            "attraction": attraction.model_dump() if attraction else None,
            "profile": profile.model_dump() if profile else None,
            "rag": rag.model_dump() if rag else None,
            "retrieval_strategy": _retrieval_strategy(attraction, rag),
            "rag_retrieval_mode": _rag_retrieval_mode(rag),
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



async def _resolve_query(query: str, user_language: str) -> tuple[QAResolvedQuery, dict[str, object]]:
    settings = get_settings()
    normalized_language = user_language.strip().lower()
    if normalized_language.startswith("zh") or _should_treat_query_as_zh(query, normalized_language):
        resolved_language = "zh" if _should_treat_query_as_zh(query, normalized_language) else user_language
        resolved = QAResolvedQuery(
            raw_query=query,
            effective_query=query,
            user_language=resolved_language,
            processing_language="zh",
            used_translation_pivot=False,
            pivot_query=None,
        )
        return resolved, {
            "used_translation_pivot": False,
            "pivot_query": None,
            "source_language": resolved_language,
            "target_language": None,
            "degraded": False,
            "degraded_reason": None,
            "execution_path": "disabled",
        }

    translator_result = await preprocess_query(
        query=query,
        source_language=user_language,
        target_language=settings.translator_pivot_language,
        provider=_translator_provider(settings),
        model=_translator_model(settings),
        timeout_seconds=settings.translator_timeout_seconds,
        enabled=settings.translator_enabled,
    )
    if translator_result.degraded and settings.translator_fail_open:
        resolved = QAResolvedQuery(
            raw_query=query,
            effective_query=query,
            user_language=user_language,
            processing_language=user_language,
            used_translation_pivot=False,
            pivot_query=None,
        )
    else:
        resolved = QAResolvedQuery(
            raw_query=query,
            effective_query=translator_result.text,
            user_language=user_language,
            processing_language=settings.translator_pivot_language,
            used_translation_pivot=not translator_result.degraded,
            pivot_query=translator_result.text if not translator_result.degraded else None,
        )
    return resolved, {
        "used_translation_pivot": resolved.used_translation_pivot,
        "pivot_query": resolved.pivot_query,
        "source_language": translator_result.source_language,
        "target_language": translator_result.target_language,
        "degraded": translator_result.degraded,
        "degraded_reason": translator_result.reason,
        "execution_path": translator_result.execution_path,
        "provider": translator_result.provider,
        "model": translator_result.model,
        "latency_ms": translator_result.latency_ms,
    }


async def _finalize_answer(
    *,
    intent: str,
    internal_answer: str,
    user_language: str,
    processing_language: str,
) -> tuple[str, dict[str, object]]:
    settings = get_settings()
    if intent == "translation" or user_language.lower().startswith("zh"):
        return internal_answer, {
            "used_answer_translation": False,
            "source_language": processing_language,
            "target_language": user_language,
            "degraded": False,
            "degraded_reason": None,
            "execution_path": "disabled",
            "language_alignment_fallback_used": False,
        }

    translator_result = await translate_answer(
        answer=internal_answer,
        source_language=processing_language,
        target_language=user_language,
        provider=_translator_provider(settings),
        model=_translator_model(settings),
        timeout_seconds=settings.translator_timeout_seconds,
        enabled=settings.translator_answer_enabled,
    )
    if translator_result.degraded:
        aligned_answer = internal_answer
        language_alignment_fallback_used = False
        if _needs_language_alignment_fallback(internal_answer, processing_language=processing_language, user_language=user_language):
            aligned_answer = _best_effort_language_alignment(internal_answer, user_language=user_language, intent=intent)
            language_alignment_fallback_used = aligned_answer != internal_answer
        return aligned_answer, {
            "used_answer_translation": False,
            "source_language": processing_language,
            "target_language": user_language,
            "degraded": True,
            "degraded_reason": translator_result.reason,
            "execution_path": translator_result.execution_path,
            "provider": translator_result.provider,
            "model": translator_result.model,
            "latency_ms": translator_result.latency_ms,
            "language_alignment_fallback_used": language_alignment_fallback_used,
        }
    return translator_result.text, {
        "used_answer_translation": True,
        "source_language": processing_language,
        "target_language": user_language,
        "degraded": False,
        "degraded_reason": None,
        "execution_path": translator_result.execution_path,
        "provider": translator_result.provider,
        "model": translator_result.model,
        "latency_ms": translator_result.latency_ms,
        "language_alignment_fallback_used": False,
    }



def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)



def _should_treat_query_as_zh(query: str, normalized_language: str) -> bool:
    return normalized_language == "en" and _contains_cjk(query) and not _contains_latin_letters(query)



def _contains_latin_letters(text: str) -> bool:
    return any("a" <= char.lower() <= "z" for char in text)



def _needs_language_alignment_fallback(answer: str, *, processing_language: str, user_language: str) -> bool:
    if processing_language.lower().startswith("zh") and user_language.lower().startswith("en"):
        return _contains_cjk(answer)
    return False



def _best_effort_language_alignment(answer: str, *, user_language: str, intent: str) -> str:
    if user_language.lower().startswith("en"):
        trip_answer = _best_effort_english_trip_alignment(answer)
        if trip_answer:
            return trip_answer
        if intent == "live_info":
            return "I can't confirm the official live information right now. Please verify with the official site or ticketing channel before you go."
        return "I can help explain this Beijing attraction, but the English post-processing step degraded just now. Please retry once for a cleaner English answer."
    return answer



def _best_effort_english_trip_alignment(answer: str) -> str | None:
    current_match = re.search(r"你现在在\s*(?P<current>[^。]+)。", answer)
    next_match = re.search(r"下一站是\s*(?P<next>[^。]+)。", answer)
    remaining_match = re.search(r"还剩\s*(?P<count>\d+)\s*个站点", answer)
    current_name = current_match.group("current").strip() if current_match else None
    next_name = next_match.group("next").strip() if next_match else None
    remaining_count = remaining_match.group("count").strip() if remaining_match else None
    if next_name:
        parts = []
        if current_name:
            parts.append(f"You are currently at {current_name}.")
        parts.append(f"Your next route stop is {next_name}.")
        if remaining_count is not None:
            parts.append(f"After this stop, {remaining_count} stop(s) remain.")
        parts.append(f"You can head toward {next_name} next.")
        return " ".join(parts)
    if current_name:
        parts = [f"Your current route stop is {current_name}."]
        if remaining_count is not None:
            parts.append(f"After this stop, {remaining_count} stop(s) remain.")
        parts.append("You can continue this stop first, then decide the next step.")
        return " ".join(parts)
    return None



def _contains_cjk(text: str) -> bool:
    return any("一" <= char <= "鿿" for char in text)



def _translator_provider(settings) -> str:
    return settings.translator_provider or settings.llm_provider



def _translator_model(settings) -> str:
    return settings.translator_model or settings.llm_model


async def preview_question(session: AsyncSession, payload: QAAskRequest) -> dict[str, object]:
    settings = get_settings()
    session_context = await _load_session_context(session, payload.guide_session_id)
    session_context, playground_applied = merge_session_context_with_playground(session_context, payload.context)
    dialogue_history = await load_recent_history(session, payload.guide_session_id)
    dialogue_history = resolve_dialogue_history_for_playground(dialogue_history, payload.context, playground_applied)
    resolved_query, preprocessing_metadata = await _resolve_query(payload.query, payload.language)
    domain_guard = evaluate_domain_support(_domain_guard_query(resolved_query))
    intent_rule_result = score_intent(
        resolved_query.effective_query,
        dialogue_history,
        raw_query=resolved_query.raw_query,
    )
    final_intent_result = dict(intent_rule_result)
    fallback_result = None
    fallback_metadata = None

    fallback_reason = intent_rule_result.get("fallback_reason")
    should_try_fallback = (
        domain_guard.supported
        and settings.qa_router_fallback_enabled
        and bool(intent_rule_result.get("needs_fallback"))
        and fallback_reason not in {"boundary_topic_conflict"}
        and intent_rule_result.get("intent") != "manual_route_edit_redirect"
    )
    if should_try_fallback:
        fallback_result, fallback_metadata = await resolve_router_fallback(
            query=resolved_query.effective_query,
            raw_query=resolved_query.raw_query,
            pivot_query=resolved_query.pivot_query,
            language=resolved_query.processing_language,
            market=_as_str(payload.context.get("market")),
            dialogue_history=dialogue_history,
            rule_result=intent_rule_result,
            session_context=session_context,
        )
        if fallback_result is not None:
            final_intent_result = {
                **intent_rule_result,
                "intent": fallback_result.intent,
                "confidence": max(float(intent_rule_result.get("confidence", 0.0)), fallback_result.confidence),
                "needs_fallback": False,
                "fallback_reason": intent_rule_result.get("fallback_reason"),
            }
            if fallback_result.intent == "weather_info":
                final_intent_result["weather_location_name"] = fallback_result.weather_location_name

    intent = str(final_intent_result["intent"])
    resolved_attraction_name = _resolve_attraction_name(
        _entity_resolution_query(resolved_query),
        session_context,
        dialogue_history,
    )
    routing_session_context = {
        **session_context,
        "weather_location_name": _as_str(final_intent_result.get("weather_location_name")),
    }
    hybrid_context = await build_hybrid_context(
        intent=intent,
        query=resolved_query.effective_query,
        attraction_name=resolved_attraction_name,
        user_id=payload.user_id or _as_str(payload.context.get("user_id")),
        session_context=routing_session_context,
        dialogue_history=dialogue_history,
        session=session,
    )
    hybrid_context = apply_hybrid_context_playground_overrides(
        hybrid_context,
        payload.context,
        session_context=session_context,
        dialogue_history=dialogue_history,
        fallback_user_id=payload.user_id or _as_str(payload.context.get("user_id")),
        applied=playground_applied,
    )
    context = build_context(
        resolved_query.effective_query,
        resolved_query.processing_language,
        payload.context,
        {
            **session_context,
            "dialogue_history": dialogue_history,
            "hybrid_context": hybrid_context.model_dump() if hybrid_context else {},
            "resolved_query": resolved_query.model_dump(),
        },
    )

    prompt_preview = None
    if intent in {"live_info", "trip_assistant", "attraction_explain"}:
        request = build_qa_generation_request(
            provider=payload.llm_provider or settings.llm_provider,
            model=payload.llm_model or settings.llm_model,
            intent=intent,
            query=resolved_query.effective_query,
            language=resolved_query.processing_language,
            hybrid_context=hybrid_context,
        )
        prompt_preview = request.model_dump()

    return {
        "resolved_query": resolved_query.model_dump(),
        "domain_guard": domain_guard.model_dump(),
        "intent_router": {
            "rule_result": intent_rule_result,
            "fallback_result": fallback_result.model_dump() if fallback_result else fallback_metadata,
            "final_result": final_intent_result,
            "preprocessing": preprocessing_metadata,
        },
        "session_context": session_context,
        "dialogue_history": dialogue_history,
        "hybrid_context": hybrid_context.model_dump() if hybrid_context else {},
        "context": context,
        "playground": playground_applied.model_dump(),
        "prompt_preview": prompt_preview,
    }



def _live_info_cache_metadata(live_info: object | None) -> dict[str, object]:
    if live_info is None:
        return {
            "live_info_cache_hit": False,
            "live_info_cache_key": None,
            "live_info_cached_at": None,
            "live_info_cache_ttl_seconds": None,
            "live_info_info_type": None,
        }
    return {
        "live_info_cache_hit": bool(getattr(live_info, "cache_hit", False)),
        "live_info_cache_key": getattr(live_info, "cache_key", None),
        "live_info_cached_at": getattr(live_info, "cached_at", None),
        "live_info_cache_ttl_seconds": getattr(live_info, "cache_ttl_seconds", None),
        "live_info_info_type": getattr(live_info, "info_type", None),
    }


def _build_llm_fallback_metadata(llm_attempt_metadata: dict[str, object] | None) -> dict[str, object]:
    if llm_attempt_metadata is None:
        return {"llm": {"fallback_used": True}}
    llm_metadata = llm_attempt_metadata.get("llm")
    if not isinstance(llm_metadata, dict):
        return {"llm": {"fallback_used": True}}
    fallback_llm_metadata = dict(llm_metadata)
    fallback_llm_metadata["fallback_used"] = True
    return {"llm": fallback_llm_metadata}



def _detect_boundary_topic(query: str) -> str | None:
    lowered = query.lower().strip()
    if any(token in lowered for token in ["traffic", "congestion", "交通", "堵"]):
        return "traffic"
    if any(token in lowered for token in ["crowd", "busy", "拥挤", "人多", "排队", "队长", "队伍"]):
        return "crowd"
    return None



def _boundary_topic_message(query: str) -> str | None:
    topic = _detect_boundary_topic(query)
    if topic is None:
        return None
    return _BOUNDARY_TOPIC_MESSAGE



def _normalize_grounding(source_type: object) -> str:
    if not isinstance(source_type, str):
        return "limited"
    lowered = source_type.lower()
    if "rag" in lowered:
        return "rag"
    if any(token in lowered for token in ["sql", "postgres"]):
        return "sql"
    return "limited"


def _retrieval_strategy(attraction: object, rag: object) -> str:
    if rag is not None and getattr(rag, "retrieval_mode", None):
        return str(getattr(rag, "retrieval_mode"))
    if attraction is None:
        return "model_knowledge"
    return "sql_only"


def _rag_retrieval_mode(rag: object) -> str:
    if rag is not None and getattr(rag, "retrieval_mode", None):
        return str(getattr(rag, "retrieval_mode"))
    return "not_used"


def _attraction_grounding(grounding: object, attraction: object, rag: object) -> str:
    if isinstance(grounding, str) and grounding:
        if grounding == "limited" and attraction is None and rag is None:
            return "model_knowledge"
        return grounding
    return _retrieval_strategy(attraction, rag).replace("sql_only", "sql")



def _trip_assistant_fallback_reason(llm_attempt_metadata: dict[str, object] | None) -> str:
    llm_metadata = (llm_attempt_metadata or {}).get("llm")
    if isinstance(llm_metadata, dict) and llm_metadata.get("structured_output_valid") is False:
        return "trip_assistant_structured_output_invalid"
    return "trip_assistant_runtime_unavailable"



def _looks_like_route_status_query(query: str, raw_query: str | None = None) -> bool:
    lowered_query = query.lower()
    lowered_raw_query = raw_query.lower() if isinstance(raw_query, str) else ""
    combined = f"{lowered_query} {lowered_raw_query}".strip()
    explicit_current_route_tokens = (
        "current route",
        "current stop",
        "active stop",
        "where am i",
        "where i am",
        "what stop am i at",
        "which stop am i at",
        "现在到哪",
        "当前站点",
        "当前路线",
        "我现在在哪一站",
        "我现在到哪了",
    )
    current_markers = ("current", "active", "now", "where am i", "现在", "当前")
    route_markers = ("itinerary", "route", "stop", "行程", "路线", "站点", "哪一站")
    if any(token in combined for token in explicit_current_route_tokens):
        return True
    return any(token in combined for token in current_markers) and any(token in combined for token in route_markers)



def _align_session_stop_names(answer: str, session_context: dict[str, object]) -> str:
    current_stop_name = _as_str(session_context.get("current_stop_name"))
    next_stop_name = _as_str(session_context.get("next_stop_name"))
    normalized = answer
    if current_stop_name == "Forbidden City":
        normalized = normalized.replace("Palace Museum", "Forbidden City")
    if next_stop_name == "Forbidden City":
        normalized = normalized.replace("Palace Museum", "Forbidden City")
    if current_stop_name == "Jingshan Park":
        normalized = normalized.replace("Jingshan Hill Park", "Jingshan Park")
    if next_stop_name == "Jingshan Park":
        normalized = normalized.replace("Jingshan Hill Park", "Jingshan Park")
    return normalized



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
    query_candidate = resolve_attraction_name_candidate(query)
    if query_candidate is not None:
        return query_candidate
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


def _entity_resolution_query(resolved_query: QAResolvedQuery) -> str:
    parts = [resolved_query.effective_query]
    if resolved_query.raw_query and resolved_query.raw_query not in parts:
        parts.append(resolved_query.raw_query)
    if resolved_query.pivot_query and resolved_query.pivot_query not in parts:
        parts.append(resolved_query.pivot_query)
    return " ".join(part for part in parts if part)


def _resolve_pending_navigation_clarification_selection(
    query: str,
    dialogue_history: list[dict[str, object]],
) -> dict[str, object] | None:
    clarification = _latest_navigation_place_clarification(dialogue_history)
    if clarification is None:
        return None
    candidates = clarification.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None

    selected_candidate = None
    selected_index = _extract_selection_index(query, candidate_count=len(candidates))
    if selected_index is not None and selected_index < 1:
        return {
            "selection_error": "ambiguous_middle_selection",
            "candidate_count": len(candidates),
            "slot_result": clarification.get("slot_result"),
            "target_role": clarification.get("target_role") or "destination",
            "target_index": clarification.get("target_index") or 0,
            "raw_text": clarification.get("raw_text"),
            "candidates": candidates,
        }
    if selected_index is not None and selected_index > len(candidates):
        return {
            "selection_error": "selection_index_out_of_range",
            "selected_index": selected_index,
            "candidate_count": len(candidates),
            "slot_result": clarification.get("slot_result"),
            "target_role": clarification.get("target_role") or "destination",
            "target_index": clarification.get("target_index") or 0,
            "raw_text": clarification.get("raw_text"),
            "candidates": candidates,
        }
    if selected_index is not None and 1 <= selected_index <= len(candidates):
        candidate = candidates[selected_index - 1]
        if isinstance(candidate, dict):
            selected_candidate = candidate
    if selected_candidate is None:
        selected_candidate = _match_candidate_by_name(query, candidates)
    if selected_candidate is None:
        return None

    return {
        "selected_index": selected_candidate.get("index") if isinstance(selected_candidate, dict) else selected_index,
        "candidate": selected_candidate,
        "slot_result": clarification.get("slot_result"),
        "target_role": clarification.get("target_role") or "destination",
        "target_index": clarification.get("target_index") or 0,
        "raw_text": clarification.get("raw_text"),
    }


def _should_try_pending_clarification_fallback(
    pending_clarification: dict[str, object] | None,
    deterministic_selection: dict[str, object] | None,
    intent_rule_result: dict[str, object],
) -> bool:
    if pending_clarification is None or deterministic_selection is not None:
        return False
    intent = str(intent_rule_result.get("intent") or "")
    confidence = _safe_float(intent_rule_result.get("confidence")) or 0.0
    needs_fallback = bool(intent_rule_result.get("needs_fallback"))
    if needs_fallback:
        return True
    strong_new_intents = {
        "translation",
        "live_info",
        "weather_info",
        "attraction_explain",
        "manual_route_edit_redirect",
    }
    if intent in strong_new_intents and confidence >= 0.7:
        return False
    return True


def _navigation_clarification_selection_from_fallback(
    fallback_result: IntentRouterFallbackResult,
    pending_clarification: dict[str, object] | None,
) -> dict[str, object] | None:
    if pending_clarification is None or fallback_result.clarification_action is None:
        return None
    if fallback_result.clarification_action == "not_a_selection":
        return None
    candidates = pending_clarification.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    base = {
        "slot_result": pending_clarification.get("slot_result"),
        "target_role": pending_clarification.get("target_role") or "destination",
        "target_index": pending_clarification.get("target_index") or 0,
        "raw_text": pending_clarification.get("raw_text"),
        "candidates": candidates,
        "source": "router_fallback",
    }
    if fallback_result.clarification_action == "needs_clarification" or fallback_result.confidence < 0.75:
        return {
            **base,
            "selection_error": "clarification_fallback_needs_clarification",
            "candidate_count": len(candidates),
        }
    selected_index = fallback_result.selected_index
    if selected_index is None:
        return {
            **base,
            "selection_error": "clarification_fallback_needs_clarification",
            "candidate_count": len(candidates),
        }
    if selected_index < 1 or selected_index > len(candidates):
        return {
            **base,
            "selection_error": "selection_index_out_of_range",
            "selected_index": selected_index,
            "candidate_count": len(candidates),
        }
    selected_candidate = candidates[selected_index - 1]
    if not isinstance(selected_candidate, dict):
        return {
            **base,
            "selection_error": "clarification_fallback_needs_clarification",
            "candidate_count": len(candidates),
        }
    return {
        **base,
        "selected_index": selected_candidate.get("index") or selected_index,
        "candidate": selected_candidate,
    }


def _latest_navigation_place_clarification(
    dialogue_history: list[dict[str, object]],
) -> dict[str, object] | None:
    for item in reversed(dialogue_history):
        if item.get("role") != "assistant":
            continue
        if item.get("intent") != "navigation_text":
            return None
        metadata = item.get("metadata")
        if not isinstance(metadata, dict):
            return None
        navigation = metadata.get("navigation")
        if not isinstance(navigation, dict) or navigation.get("status") != "clarification":
            return None
        clarification = navigation.get("clarification")
        return clarification if isinstance(clarification, dict) else None
    return None


def _extract_selection_index(query: str, *, candidate_count: int | None = None) -> int | None:
    normalized = query.strip().lower()
    normalized = normalized.replace(" ", "")
    top_patterns = (
        "上面的",
        "上面那个",
        "最上面",
        "第一个上面",
        "选上面",
        "选上面的",
        "就上面",
        "就上面的",
    )
    bottom_patterns = (
        "下面的",
        "下面那个",
        "最下面",
        "最后一个",
        "最后那个",
        "选下面",
        "选下面的",
        "选最后",
        "就下面",
        "就下面的",
        "末尾那个",
    )
    middle_patterns = (
        "中间的",
        "中间那个",
        "选中间",
        "选中间的",
        "就中间",
        "就中间的",
    )
    if any(pattern in normalized for pattern in top_patterns):
        return 1
    if any(pattern in normalized for pattern in bottom_patterns):
        return candidate_count if candidate_count else None
    if any(pattern in normalized for pattern in middle_patterns):
        if not candidate_count:
            return None
        if candidate_count % 2 == 1:
            return candidate_count // 2 + 1
        return -1
    ordinal_map = {
        "一": 1,
        "1": 1,
        "二": 2,
        "两": 2,
        "2": 2,
        "三": 3,
        "3": 3,
        "四": 4,
        "4": 4,
        "五": 5,
        "5": 5,
    }
    if normalized in ordinal_map:
        return ordinal_map[normalized]
    for token, index in ordinal_map.items():
        patterns = (
            f"第{token}个",
            f"第{token}项",
            f"第{token}条",
            f"选第{token}个",
            f"选第{token}项",
            f"选{token}",
            f"要{token}",
            f"就{token}",
            f"{token}号",
            f"{token}.",
        )
        if any(pattern in normalized for pattern in patterns):
            return index
    digit_match = re.search(r"(?:选|第|要|就)?([1-5])(?:个|项|条|号)?", normalized)
    if digit_match:
        return int(digit_match.group(1))
    return None


def _match_candidate_by_name(query: str, candidates: list[object]) -> dict[str, object] | None:
    normalized = query.strip().lower()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        names = [
            candidate.get("display_name"),
            candidate.get("name"),
            candidate.get("address"),
        ]
        if any(isinstance(name, str) and name and name.lower() in normalized for name in names):
            return candidate
    return None


def _last_intent(dialogue_history: list[dict[str, object]]) -> str | None:
    for item in reversed(dialogue_history):
        intent = item.get("intent")
        if isinstance(intent, str):
            return intent
    return None


def _domain_guard_query(resolved_query: QAResolvedQuery) -> str:
    parts = [resolved_query.effective_query]
    if resolved_query.raw_query and resolved_query.raw_query not in parts:
        parts.append(resolved_query.raw_query)
    if resolved_query.pivot_query and resolved_query.pivot_query not in parts:
        parts.append(resolved_query.pivot_query)
    return " ".join(part for part in parts if part)



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


def _safe_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None

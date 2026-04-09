from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.modules.qa.context_builder import build_context
from yoyo.modules.qa.domain_guard import is_supported_query
from yoyo.modules.qa.intent_router import detect_intent
from yoyo.modules.qa.formatters import (
    format_attraction_answer,
    format_translation_answer,
    format_trip_assistant_answer,
)
from yoyo.modules.qa.live_info import build_live_info_payload
from yoyo.modules.qa.planner_handoff import build_planner_handoff
from yoyo.modules.qa.retrieval import get_attraction_explanation
from yoyo.modules.qa.schemas import QAAskRequest, QAAskResponse
from yoyo.modules.qa.skill_registry import get_allowed_skills
from yoyo.modules.qa.validators import validate_answer
from yoyo.modules.session.service import get_guide_session, get_itinerary_version_plan


OUT_OF_SCOPE_MESSAGE = (
    "I can help with Beijing tour topics such as attractions, itinerary guidance, translation, and travel info."
)


async def answer_question(session: AsyncSession, payload: QAAskRequest) -> QAAskResponse:
    if not is_supported_query(payload.query):
        return QAAskResponse(
            supported=False,
            intent="out_of_scope",
            answer=OUT_OF_SCOPE_MESSAGE,
            used_skills=[],
            metadata={},
        )

    intent = detect_intent(payload.query)
    allowed_skills = get_allowed_skills(intent)
    session_context = await _load_session_context(session, payload.guide_session_id)
    context = build_context(payload.query, payload.language, payload.context, session_context)

    answer, extra_metadata = await _generate_answer(intent, payload.query, session_context)
    validation = validate_answer(intent, answer)

    return QAAskResponse(
        supported=True,
        intent=intent,
        answer=answer,
        used_skills=allowed_skills,
        metadata={
            "context": context,
            "validation": validation,
            **extra_metadata,
        },
    )


async def _load_session_context(session: AsyncSession, guide_session_id: str | None) -> dict[str, object]:
    if guide_session_id is None:
        return {}

    guide_session = await get_guide_session(session, guide_session_id)
    if guide_session is None:
        return {}

    plan = await get_itinerary_version_plan(session, guide_session.itinerary_version_id)
    stops = plan.get("stops", []) if plan else []
    current_stop_name = None
    if stops:
        current_stop_name = str(stops[0].get("name"))

    next_stop_name = None
    if len(stops) > 1:
        next_stop_name = str(stops[1].get("name"))

    return {
        "guide_session_id": guide_session.id,
        "itinerary_version_id": guide_session.itinerary_version_id,
        "current_stop_name": current_stop_name,
        "next_stop_name": next_stop_name,
        "stop_count": len(stops),
        "plan_summary": plan.get("summary") if plan else None,
    }


async def _generate_answer(intent: str, query: str, session_context: dict[str, object]) -> tuple[str, dict[str, object]]:
    current_stop_name = session_context.get("current_stop_name")
    next_stop_name = session_context.get("next_stop_name")
    stop_count = session_context.get("stop_count")
    plan_summary = session_context.get("plan_summary")

    if intent == "translation":
        return format_translation_answer(query), {}

    if intent == "live_info":
        live_info = await build_live_info_payload(query, _as_str(current_stop_name))
        return str(live_info["summary"]), {
            "sources": live_info["sources"],
            "updated_at": live_info["updated_at"],
            "not_confirmed": live_info["not_confirmed"],
            "confidence": live_info["confidence"],
        }

    if intent == "trip_assistant":
        return format_trip_assistant_answer(
            _as_str(current_stop_name),
            _as_str(next_stop_name),
            _as_int(stop_count),
            _as_str(plan_summary),
        ), {}

    if intent == "planner_handoff":
        handoff = build_planner_handoff(query)
        return "This request should be handed off to Planner for route updates.", {
            "planner_handoff": handoff.model_dump()
        }

    attraction = get_attraction_explanation(_as_str(current_stop_name))
    if attraction is not None:
        answer = format_attraction_answer(
            str(attraction["name"]),
            str(attraction["summary"]),
            str(attraction["history"]),
            list(attraction["tips"]),
        )
        return answer, {"retrieval": attraction}

    if current_stop_name:
        return f"Attraction explanation placeholder for {current_stop_name}. Retrieval-backed explanation will be added next.", {}
    return "Attraction explanation placeholder. Retrieval-backed explanation will be added next.", {}


def _as_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None

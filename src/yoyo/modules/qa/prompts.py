from __future__ import annotations

from yoyo.modules.knowledge.prompt_projection import describe_guide_style
from yoyo.modules.knowledge.schemas import HybridContext
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, PromptMessage



def build_qa_generation_request(
    *,
    provider: str,
    model: str,
    intent: str,
    query: str,
    language: str,
    hybrid_context: HybridContext,
) -> LLMRequest:
    system_prompt = _build_system_prompt(intent, language)
    user_prompt = _build_user_prompt(intent, query, hybrid_context)
    return LLMRequest(
        provider=provider,
        model=model,
        messages=[
            PromptMessage(role="system", content=system_prompt),
            PromptMessage(role="user", content=user_prompt),
        ],
        options=GenerationOptions(max_tokens=700, temperature=0.35, timeout_seconds=35.0),
        metadata={"prompt_version": f"qa-{intent}-v1"},
    )



def _build_system_prompt(intent: str, language: str) -> str:
    base = (
        "You are a Beijing tour guide assistant. "
        "Use SQL-grounded attraction/profile facts first, then use retrieved RAG snippets only as supporting context when they are present. "
        "Do not invent attractions, route state, or real-time facts. "
        "If SQL and RAG disagree, stay conservative and prefer the structured SQL facts unless the RAG snippet clearly adds historical/background detail. "
        "If facts are uncertain, say so clearly. "
        f"Respond in {language}."
    )
    if intent == "translation":
        return base + (
            " Return only a JSON object with keys: answer, status, reason, mode. "
            "Allowed status values: ok, clarification, degraded. "
            "Allowed mode values: direct_translation, needs_phrase, degraded. "
            "If the exact phrase is missing, return clarification. "
            "Do not add markdown fences or extra text."
        )
    if intent == "live_info":
        return base + (
            " Return only a JSON object with keys: answer, status, reason, not_confirmed, confidence. "
            "Allowed status values: ok, degraded, unavailable. "
            "Allowed confidence values: low, medium, high. "
            "If live info is unavailable or degraded, state that clearly instead of sounding confident. "
            "Do not add markdown fences or extra text."
        )
    if intent == "trip_assistant":
        return base + (
            " Return only a JSON object with keys: answer, status, reason, route_focus, references_current_stop, references_next_stop. "
            "Allowed status values: ok, degraded, clarification, redirect. "
            "Allowed route_focus values: current_stop, next_stop, route_overview, manual_edit_redirect, general_guidance. "
            "Keep the route progression explicit, practical, and action-oriented. "
            "Do not suggest that QA can execute route edits. "
            "Do not add markdown fences or extra text."
        )
    if intent == "attraction_explain":
        return base + (
            " Return only a JSON object with keys: answer, status, reason, grounding, includes_history, includes_tips. "
            "Allowed status values: ok, degraded, unavailable, clarification. "
            "Allowed grounding values: sql, rag, sql_then_rag, limited. "
            "Keep the explanation concise, grounded, and user-facing. "
            "Prefer SQL-grounded facts and use RAG only as supporting context. "
            "Do not add markdown fences or extra text."
        )
    return base + " Keep the explanation concise, grounded, and user-facing."



def _build_user_prompt(intent: str, query: str, hybrid_context: HybridContext) -> str:
    attraction = hybrid_context.prompt_safe_attraction
    profile = hybrid_context.prompt_safe_profile
    session_context = hybrid_context.session_context
    history = hybrid_context.dialogue_history[-4:]
    sections = [
        f"Intent: {intent}",
        f"User query: {query}",
        f"Session context: {session_context}",
        f"Recent dialogue history: {history}",
        f"Prompt-safe attraction context: {attraction}",
        f"Prompt-safe profile context: {profile}",
    ]
    if hybrid_context.live_info is not None:
        sections.append(f"Live info context: {hybrid_context.live_info.model_dump()}")
    if hybrid_context.rag is not None:
        sections.append(f"RAG retrieval context: {hybrid_context.rag.model_dump()}")
    style = describe_guide_style(profile.get("guide_style_preference")) if profile else "guardian"
    sections.append(f"Guide/answer style preference: {style}")
    return "\n\n".join(sections)

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
        "Use only the provided SQL-grounded attraction/profile facts, session context, dialogue history, and live-info context if present. "
        "Do not invent attractions, route state, or real-time facts. "
        "If facts are uncertain, say so clearly. "
        f"Respond in {language}."
    )
    if intent == "translation":
        return base + " Return a direct translation when possible, without extra meta explanation."
    if intent == "live_info":
        return base + " For live info, remind the user to verify same-day official information."
    if intent == "trip_assistant":
        return base + " For trip guidance, keep the route progression explicit and practical."
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
    style = describe_guide_style(profile.get("guide_style_preference")) if profile else "guardian"
    sections.append(f"Guide/answer style preference: {style}")
    return "\n\n".join(sections)

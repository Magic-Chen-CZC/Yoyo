from __future__ import annotations

from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, PromptMessage


def build_routing_translation_request(
    *,
    provider: str,
    model: str,
    query: str,
    source_language: str | None,
    target_language: str,
    timeout_seconds: float,
) -> LLMRequest:
    return LLMRequest(
        provider=provider,
        model=model,
        messages=[
            PromptMessage(
                role="system",
                content=(
                    "You are a travel-query normalization translator for a Beijing tourism QA system. "
                    "Translate the user query into natural simplified Chinese for internal routing and retrieval only. "
                    "Preserve intent, negation, route-edit requests, attraction names, same-day signals, mixed-intent structure, and ambiguity. "
                    "Do not simplify a mixed-intent query into a single intent. Do not remove signals like 'don't change the route', 'today', 'notice', or 'translate into English'. "
                    "Do not answer the question. Return JSON only with keys: text, status, reason, source_language, target_language. "
                    "Allowed status values: ok, degraded."
                ),
            ),
            PromptMessage(
                role="user",
                content=(
                    f"source_language={source_language or ''}\n"
                    f"target_language={target_language}\n"
                    f"query={query}"
                ),
            ),
        ],
        options=GenerationOptions(max_tokens=220, temperature=0.0, timeout_seconds=timeout_seconds),
        metadata={"prompt_version": "translator-routing-v1"},
    )


def build_answer_translation_request(
    *,
    provider: str,
    model: str,
    answer: str,
    source_language: str,
    target_language: str,
    timeout_seconds: float,
) -> LLMRequest:
    return LLMRequest(
        provider=provider,
        model=model,
        messages=[
            PromptMessage(
                role="system",
                content=(
                    "You are a response translator for a Beijing tourism QA system. "
                    "Translate the answer faithfully into the requested target language. "
                    "Keep structure, tone, uncertainty, safety boundaries, and route guidance intact. "
                    "Do not add or remove facts. Return JSON only with keys: text, status, reason, source_language, target_language. "
                    "Allowed status values: ok, degraded."
                ),
            ),
            PromptMessage(
                role="user",
                content=(
                    f"source_language={source_language}\n"
                    f"target_language={target_language}\n"
                    f"answer={answer}"
                ),
            ),
        ],
        options=GenerationOptions(max_tokens=500, temperature=0.0, timeout_seconds=timeout_seconds),
        metadata={"prompt_version": "translator-answer-v1"},
    )


def build_qa_translation_request(
    *,
    provider: str,
    model: str,
    query: str,
    user_language: str,
    timeout_seconds: float,
    bilingual_enabled: bool,
) -> LLMRequest:
    bilingual_rule = (
        "If the user wants a sentence to show or say to local staff, prefer bilingual_for_display. "
        "In that mode, include a short user-facing instruction in the user's language and the translated sentence for the local person. "
        if bilingual_enabled
        else "Prefer direct_translation unless clarification is necessary. "
    )
    return LLMRequest(
        provider=provider,
        model=model,
        messages=[
            PromptMessage(
                role="system",
                content=(
                    "You are a practical travel translation assistant for a Beijing tourism product. "
                    "Handle explicit translation requests only. "
                    "Return JSON only with keys: answer, status, reason, mode, source_language, target_language, translated_text, user_instruction, user_visible_lines. "
                    "Allowed status values: ok, clarification, degraded. "
                    "Allowed mode values: direct_translation, bilingual_for_display, clarification, degraded. "
                    "user_visible_lines must be an ordered array of short strings ready to show to the user. "
                    + bilingual_rule +
                    "If the user did not provide enough text to translate, use clarification. "
                    "Do not add markdown fences or extra text."
                ),
            ),
            PromptMessage(
                role="user",
                content=(
                    f"user_language={user_language}\n"
                    f"query={query}"
                ),
            ),
        ],
        options=GenerationOptions(max_tokens=520, temperature=0.15, timeout_seconds=timeout_seconds),
        metadata={"prompt_version": "translator-qa-v1"},
    )

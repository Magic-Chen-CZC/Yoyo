from __future__ import annotations

import json
import re

from yoyo.core.config import get_settings
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, LLMResponse, PromptMessage
from yoyo.modules.qa import generator as qa_generator
from yoyo.modules.qa.formatters import format_translation_answer
from yoyo.modules.shared_text_sanitizer import (
    extract_fenced_json_object,
    looks_like_malformed_wrapper,
    sanitize_llm_string_list,
    sanitize_llm_text,
)
from yoyo.modules.translator.prompts import (
    build_answer_translation_request,
    build_qa_translation_request,
    build_routing_translation_request,
)
from yoyo.modules.translator.schemas import (
    AnswerTranslationStructuredOutput,
    QATranslationStructuredOutput,
    RoutingTranslationStructuredOutput,
    TranslationDisplayBlock,
    TranslatorResult,
)


_PLAIN_MT_PROVIDERS = {"hy_mt", "xfyun_its"}


def _ensure_response_raw_response(response: object) -> dict[str, object]:
    raw_response = getattr(response, "raw_response", None)
    if isinstance(raw_response, dict):
        return raw_response
    raw_response = {}
    setattr(response, "raw_response", raw_response)
    return raw_response


_LANGUAGE_ALIASES = {
    "chinese": "zh",
    "中文": "zh",
    "english": "en",
    "英文": "en",
    "thai": "th",
    "泰语": "th",
    "vietnamese": "vi",
    "越南语": "vi",
    "indonesian": "id",
    "indonesia": "id",
    "印尼语": "id",
    "bahasa indonesia": "id",
    "malay": "ms",
    "malaysian": "ms",
    "马来语": "ms",
    "filipino": "fil",
    "philippine": "fil",
    "菲律宾语": "fil",
    "tagalog": "fil",
    "他加禄语": "fil",
    "burmese": "my",
    "myanmar": "my",
    "缅甸语": "my",
    "khmer": "km",
    "cambodian": "km",
    "高棉语": "km",
    "柬埔寨语": "km",
    "lao": "lo",
    "laotian": "lo",
    "老挝语": "lo",
}

async def preprocess_query(
    *,
    query: str,
    source_language: str | None,
    target_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
    enabled: bool,
) -> TranslatorResult:
    if not enabled:
        return TranslatorResult(
            text=query,
            status="degraded",
            reason="translator_disabled",
            source_language=source_language,
            target_language=target_language,
            mode="routing_preprocess",
            degraded=True,
            execution_path="disabled",
        )
    if _uses_plain_mt(provider):
        return await _plain_mt_preprocess_query(
            query=query,
            source_language=source_language,
            target_language=target_language,
            provider=provider,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    request = build_routing_translation_request(
        provider=provider,
        model=model,
        query=query,
        source_language=source_language,
        target_language=target_language,
        timeout_seconds=timeout_seconds,
    )
    response = await qa_generator.get_llm_runtime().generate(request)
    if response.error is not None or not response.text.strip():
        return _degraded_result(
            text=query,
            status="degraded",
            reason="runtime_translation_unavailable",
            source_language=source_language,
            target_language=target_language,
            mode="routing_preprocess",
            execution_path=_error_execution_path(response.error.model_dump() if response.error else None),
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            llm_error=response.error.model_dump() if response.error else None,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    structured = _parse_structured_output(response.text, RoutingTranslationStructuredOutput)
    if structured is None:
        return _degraded_result(
            text=query,
            status="degraded",
            reason="translator_structured_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="routing_preprocess",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    sanitized_text = sanitize_llm_text(structured.text)
    if sanitized_text is None:
        return _degraded_result(
            text=query,
            status="degraded",
            reason="translator_structured_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="routing_preprocess",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    return TranslatorResult(
        text=sanitized_text,
        status=structured.status,
        reason=structured.reason,
        source_language=structured.source_language or source_language,
        target_language=structured.target_language,
        mode="routing_preprocess",
        degraded=structured.status != "ok",
        execution_path="llm_structured",
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        structured_output_valid=True,
        raw_text=response.text,
        **_usage_kwargs(response),
        **_attempt_metadata_kwargs(response),
    )


async def translate_answer(
    *,
    answer: str,
    source_language: str,
    target_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
    enabled: bool,
) -> TranslatorResult:
    if not enabled or source_language == target_language:
        return TranslatorResult(
            text=answer,
            status="degraded" if not enabled else "ok",
            reason="translator_disabled" if not enabled else None,
            source_language=source_language,
            target_language=target_language,
            mode="answer_postprocess",
            degraded=not enabled,
            execution_path="disabled" if not enabled else "llm_structured",
        )
    if _uses_plain_mt(provider):
        return await _plain_mt_translate_answer(
            answer=answer,
            source_language=source_language,
            target_language=target_language,
            provider=provider,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    request = build_answer_translation_request(
        provider=provider,
        model=model,
        answer=answer,
        source_language=source_language,
        target_language=target_language,
        timeout_seconds=timeout_seconds,
    )
    response = await qa_generator.get_llm_runtime().generate(request)
    if response.error is not None or not response.text.strip():
        return _degraded_result(
            text=answer,
            status="degraded",
            reason="runtime_translation_unavailable",
            source_language=source_language,
            target_language=target_language,
            mode="answer_postprocess",
            execution_path=_error_execution_path(response.error.model_dump() if response.error else None),
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            llm_error=response.error.model_dump() if response.error else None,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    structured = _parse_structured_output(response.text, AnswerTranslationStructuredOutput)
    if structured is None:
        return _degraded_result(
            text=answer,
            status="degraded",
            reason="translator_structured_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="answer_postprocess",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    sanitized_text = sanitize_llm_text(structured.text)
    if sanitized_text is None:
        return _degraded_result(
            text=answer,
            status="degraded",
            reason="translator_structured_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="answer_postprocess",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    return TranslatorResult(
        text=sanitized_text,
        status=structured.status,
        reason=structured.reason,
        source_language=structured.source_language,
        target_language=structured.target_language,
        mode="answer_postprocess",
        degraded=structured.status != "ok",
        execution_path="llm_structured",
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        structured_output_valid=True,
        raw_text=response.text,
        **_usage_kwargs(response),
        **_attempt_metadata_kwargs(response),
    )


async def translate_for_qa(
    *,
    query: str,
    user_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
    enabled: bool,
    bilingual_enabled: bool,
) -> TranslatorResult:
    if not enabled:
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="degraded",
            reason="translator_disabled",
            source_language=None,
            target_language=user_language,
            mode="qa_translation",
            execution_path="disabled",
            user_visible_lines=[fallback_answer],
        )
    if _uses_plain_mt(provider):
        return await _plain_mt_translate_for_qa(
            query=query,
            user_language=user_language,
            provider=provider,
            model=model,
            timeout_seconds=timeout_seconds,
            bilingual_enabled=bilingual_enabled,
        )
    request = build_qa_translation_request(
        provider=provider,
        model=model,
        query=query,
        user_language=user_language,
        timeout_seconds=timeout_seconds,
        bilingual_enabled=bilingual_enabled,
    )
    response = await qa_generator.get_llm_runtime().generate(request)
    if response.error is not None or not response.text.strip():
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="degraded",
            reason="runtime_translation_unavailable",
            source_language=None,
            target_language=user_language,
            mode="qa_translation",
            execution_path=_error_execution_path(response.error.model_dump() if response.error else None),
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            llm_error=response.error.model_dump() if response.error else None,
            raw_text=response.text,
            user_visible_lines=[fallback_answer],
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    structured = _parse_structured_output(response.text, QATranslationStructuredOutput)
    if structured is None:
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="degraded",
            reason="translator_structured_output_invalid",
            source_language=None,
            target_language=user_language,
            mode="qa_translation",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            user_visible_lines=[fallback_answer],
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    raw_answer = structured.answer
    answer = sanitize_llm_text(raw_answer)
    if answer is None or looks_like_malformed_wrapper(raw_answer):
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="degraded",
            reason="translator_structured_output_invalid",
            source_language=structured.source_language,
            target_language=structured.target_language or user_language,
            mode="qa_translation",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            user_visible_lines=[fallback_answer],
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    instruction = sanitize_llm_text(structured.user_instruction)
    translated_text = sanitize_llm_text(structured.translated_text)
    user_visible_lines = sanitize_llm_string_list(structured.user_visible_lines)
    display_blocks: list[TranslationDisplayBlock] = []
    if instruction:
        display_blocks.append(TranslationDisplayBlock(role="instruction", language=user_language, text=instruction))
    if translated_text:
        display_blocks.append(
            TranslationDisplayBlock(
                role="translation",
                language=structured.target_language or "zh",
                text=translated_text,
            )
        )
    if not user_visible_lines:
        fallback_lines = [block.text for block in display_blocks]
        user_visible_lines = fallback_lines or [answer]
    return TranslatorResult(
        text=answer,
        status=structured.status,
        reason=structured.reason,
        source_language=structured.source_language,
        target_language=structured.target_language or user_language,
        mode=structured.mode,
        degraded=structured.status == "degraded",
        execution_path="llm_structured",
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        display_blocks=display_blocks,
        user_visible_lines=user_visible_lines,
        structured_output_valid=True,
        raw_text=response.text,
        **_usage_kwargs(response),
        **_attempt_metadata_kwargs(response),
    )


async def _plain_mt_preprocess_query(
    *,
    query: str,
    source_language: str | None,
    target_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
) -> TranslatorResult:
    response = await _generate_plain_mt(
        text=query,
        source_language=source_language,
        target_language=target_language,
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
        mode="routing_preprocess",
    )
    if response.error is not None or not response.text.strip():
        return _degraded_result(
            text=query,
            status="degraded",
            reason="runtime_translation_unavailable",
            source_language=source_language,
            target_language=target_language,
            mode="routing_preprocess",
            execution_path=_error_execution_path(response.error.model_dump() if response.error else None),
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            llm_error=response.error.model_dump() if response.error else None,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    translated_text = sanitize_llm_text(response.text)
    if translated_text is None:
        return _degraded_result(
            text=query,
            status="degraded",
            reason="translator_plain_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="routing_preprocess",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    return TranslatorResult(
        text=translated_text,
        status="ok",
        reason=None,
        source_language=source_language,
        target_language=target_language,
        mode="routing_preprocess",
        degraded=False,
        execution_path="plain_mt",
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        raw_text=response.text,
        **_usage_kwargs(response),
        **_attempt_metadata_kwargs(response),
    )


async def _plain_mt_translate_answer(
    *,
    answer: str,
    source_language: str,
    target_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
) -> TranslatorResult:
    response = await _generate_plain_mt(
        text=answer,
        source_language=source_language,
        target_language=target_language,
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
        mode="answer_postprocess",
    )
    if response.error is not None or not response.text.strip():
        return _degraded_result(
            text=answer,
            status="degraded",
            reason="runtime_translation_unavailable",
            source_language=source_language,
            target_language=target_language,
            mode="answer_postprocess",
            execution_path=_error_execution_path(response.error.model_dump() if response.error else None),
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            llm_error=response.error.model_dump() if response.error else None,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    translated_text = sanitize_llm_text(response.text)
    if translated_text is None:
        return _degraded_result(
            text=answer,
            status="degraded",
            reason="translator_plain_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="answer_postprocess",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    return TranslatorResult(
        text=translated_text,
        status="ok",
        reason=None,
        source_language=source_language,
        target_language=target_language,
        mode="answer_postprocess",
        degraded=False,
        execution_path="plain_mt",
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        raw_text=response.text,
        **_usage_kwargs(response),
        **_attempt_metadata_kwargs(response),
    )


async def _plain_mt_translate_for_qa(
    *,
    query: str,
    user_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
    bilingual_enabled: bool,
) -> TranslatorResult:
    parsed = _parse_explicit_translation_query(query)
    if parsed is None:
        parsed = _fallback_parse_translation_query(query)
    if parsed is None:
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="clarification",
            reason="missing_translation_text",
            source_language=None,
            target_language="zh",
            mode="qa_translation",
            execution_path="formatter_fallback",
            user_visible_lines=[fallback_answer],
        )
    source_text = parsed["text"]
    target_language = str(parsed["target_language"] or _infer_target_language_from_query(query, user_language))
    source_language = _resolve_explicit_translation_source_language(
        query_text=source_text,
        user_language=user_language,
        target_language=target_language,
    )
    response = await _generate_plain_mt(
        text=source_text,
        source_language=source_language,
        target_language=target_language,
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
        mode="qa_translation",
    )
    if response.error is not None or not response.text.strip():
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="degraded",
            reason="runtime_translation_unavailable",
            source_language=source_language,
            target_language=target_language,
            mode="qa_translation",
            execution_path=_error_execution_path(response.error.model_dump() if response.error else None),
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            llm_error=response.error.model_dump() if response.error else None,
            raw_text=response.text,
            user_visible_lines=[fallback_answer],
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    translated_text = sanitize_llm_text(response.text)
    if translated_text is None:
        fallback_answer = format_translation_answer(query)
        return _degraded_result(
            text=fallback_answer,
            status="degraded",
            reason="translator_plain_output_invalid",
            source_language=source_language,
            target_language=target_language,
            mode="qa_translation",
            execution_path="invalid_output",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            raw_text=response.text,
            user_visible_lines=[fallback_answer],
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    if parsed["show_to_local"] and bilingual_enabled:
        instruction = _build_display_instruction(user_language)
        answer = "\n".join([instruction, translated_text])
        display_blocks = [
            TranslationDisplayBlock(role="instruction", language=user_language, text=instruction),
            TranslationDisplayBlock(role="translation", language=target_language, text=translated_text),
        ]
        return TranslatorResult(
            text=answer,
            status="ok",
            reason=None,
            source_language=source_language,
            target_language=target_language,
            mode="bilingual_for_display",
            degraded=False,
            execution_path="plain_mt",
            provider=response.provider,
            model=response.model,
            latency_ms=response.latency_ms,
            display_blocks=display_blocks,
            user_visible_lines=[instruction, translated_text],
            raw_text=response.text,
            **_usage_kwargs(response),
            **_attempt_metadata_kwargs(response),
        )
    return TranslatorResult(
        text=translated_text,
        status="ok",
        reason=None,
        source_language=source_language,
        target_language=target_language,
        mode="direct_translation",
        degraded=False,
        execution_path="plain_mt",
        provider=response.provider,
        model=response.model,
        latency_ms=response.latency_ms,
        user_visible_lines=[translated_text],
        raw_text=response.text,
        **_usage_kwargs(response),
        **_attempt_metadata_kwargs(response),
    )


async def _generate_plain_mt(
    *,
    text: str,
    source_language: str | None,
    target_language: str,
    provider: str,
    model: str,
    timeout_seconds: float,
    mode: str,
):
    settings = get_settings()
    max_attempts = max(1, settings.translator_plain_mt_max_attempts)
    per_attempt_timeout = min(timeout_seconds, settings.translator_plain_mt_attempt_timeout_seconds)
    runtime = qa_generator.get_llm_runtime()
    attempts: list[dict[str, object]] = []
    last_response: LLMResponse | None = None

    for attempt in range(1, max_attempts + 1):
        request = LLMRequest(
            provider=provider,
            model=model,
            messages=[PromptMessage(role="user", content=text)],
            options=GenerationOptions(max_tokens=512, temperature=0.0, timeout_seconds=per_attempt_timeout),
            metadata={
                "translation_mode": mode,
                "plain_text": text,
                "source_language": source_language,
                "target_language": target_language,
            },
        )
        response = await runtime.generate(request)
        attempts.append(
            {
                "attempt": attempt,
                "latency_ms": response.latency_ms,
                "error": response.error.model_dump() if response.error else None,
                "raw_text": response.text or None,
            }
        )
        last_response = response
        raw_response = _ensure_response_raw_response(response)
        if response.error is None and response.text.strip():
            raw_response["attempts"] = attempts
            return response
        should_retry = bool(response.error and getattr(response.error, "retryable", False) and attempt < max_attempts)
        if not should_retry:
            break

    if last_response is None:
        last_response = LLMResponse(text="", provider=provider, model=model)
    _ensure_response_raw_response(last_response)["attempts"] = attempts
    return last_response


def _parse_structured_output(text: str, model_class):
    payload = _load_json_object(text)
    if payload is None:
        return None
    try:
        return model_class.model_validate(payload)
    except Exception:
        return None


def _load_json_object(text: str) -> dict[str, object] | None:
    cleaned = text.strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        payload = extract_fenced_json_object(cleaned)
        if payload is None:
            return None
    if not isinstance(payload, dict):
        return None
    return payload


def _error_execution_path(error: dict[str, object] | None) -> str:
    if not isinstance(error, dict):
        return "provider_error"
    message = str(error.get("message") or "").lower()
    error_type = str(error.get("error_type") or "").lower()
    if "timeout" in message or "timeout" in error_type:
        return "timeout"
    return "provider_error"


def _usage_kwargs(response: LLMResponse | None) -> dict[str, int | float | None]:
    if response is None:
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "estimated_input_cost": None,
            "estimated_output_cost": None,
            "estimated_total_cost": None,
        }
    usage = getattr(response, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "estimated_input_cost": None,
        "estimated_output_cost": None,
        "estimated_total_cost": getattr(usage, "cost", None),
    }


def _attempt_metadata_kwargs(response: LLMResponse | None) -> dict[str, object]:
    attempts = []
    if response is not None:
        raw_response = getattr(response, "raw_response", None)
        if isinstance(raw_response, dict):
            attempts = list(raw_response.get("attempts") or [])
    attempt_count = len(attempts) or 1
    retry_performed = attempt_count > 1
    return {
        "attempt_count": attempt_count,
        "retry_performed": retry_performed,
        "attempts": attempts,
    }


def _degraded_result(
    *,
    text: str,
    status: str,
    reason: str,
    source_language: str | None,
    target_language: str | None,
    mode: str,
    execution_path: str,
    provider: str | None = None,
    model: str | None = None,
    latency_ms: float | None = None,
    llm_error: dict[str, object] | None = None,
    raw_text: str | None = None,
    user_visible_lines: list[str] | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    estimated_input_cost: float | None = None,
    estimated_output_cost: float | None = None,
    estimated_total_cost: float | None = None,
    attempt_count: int = 1,
    retry_performed: bool = False,
    attempts: list[dict[str, object]] | None = None,
) -> TranslatorResult:
    return TranslatorResult(
        text=text,
        status=status,
        reason=reason,
        source_language=source_language,
        target_language=target_language,
        mode=mode,
        degraded=True,
        execution_path=execution_path,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_input_cost=estimated_input_cost,
        estimated_output_cost=estimated_output_cost,
        estimated_total_cost=estimated_total_cost,
        user_visible_lines=user_visible_lines or [],
        llm_error=llm_error,
        structured_output_valid=False if execution_path == "invalid_output" else None,
        raw_text=raw_text,
        attempt_count=attempt_count,
        retry_performed=retry_performed,
        attempts=attempts or [],
    )


def _uses_plain_mt(provider: str) -> bool:
    return provider in _PLAIN_MT_PROVIDERS


def _parse_explicit_translation_query(query: str) -> dict[str, object] | None:
    stripped = query.strip()
    lowered = stripped.lower()

    english_match = re.match(r"^(?:please\s+)?translate(?:\s+this)?\s+into\s+(.+?)\s*[:：]\s*(.+)$", stripped, re.IGNORECASE)
    if english_match:
        target_hint, text = english_match.groups()
        target_language = _find_language_code(target_hint) or "zh"
        return {
            "text": text.strip(),
            "target_language": target_language,
            "show_to_local": False,
        }

    chinese_colon_patterns = [
        r"^把这句话翻(?:译)?成(.+?)\s*[：:]\s*(.+)$",
        r"^把这句(?:话)?翻(?:译)?成(.+?)\s*[：:]\s*(.+)$",
        r"^这句话用(.+?)怎么说\s*[：:]\s*(.+)$",
    ]
    for pattern in chinese_colon_patterns:
        match = re.match(pattern, stripped)
        if not match:
            continue
        target_hint, text = match.groups()
        target_language = _find_language_code(target_hint) or "zh"
        return {
            "text": text.strip(),
            "target_language": target_language,
            "show_to_local": False,
        }

    quoted_text = _extract_quoted_text(stripped)
    if quoted_text and any(token in stripped for token in ["翻成中文", "翻译成中文", "用中文怎么说"]):
        return {
            "text": quoted_text,
            "target_language": "zh",
            "show_to_local": False,
        }
    if quoted_text and _looks_like_show_to_local_request(stripped):
        return {
            "text": quoted_text,
            "target_language": "zh",
            "show_to_local": True,
        }

    suffix_match = re.match(r"^(.+?)\s*用中文怎么说[？?]?$", stripped)
    if suffix_match:
        return {
            "text": suffix_match.group(1).strip(" ：:\n\t"),
            "target_language": "zh",
            "show_to_local": False,
        }

    suffix_translate_match = re.match(r"^(.+?)\s*翻(?:译)?成中文[？?]?$", stripped)
    if suffix_translate_match:
        return {
            "text": suffix_translate_match.group(1).strip(" ：:\n\t"),
            "target_language": "zh",
            "show_to_local": False,
        }

    separators = [
        "translate this into chinese:",
        "translate into chinese:",
        "translate this:",
        "translate:",
        "please translate:",
        "翻译成中文：",
        "翻译成中文:",
        "翻成中文：",
        "翻成中文:",
        "翻译：",
        "翻译:",
        "帮我问一下",
    ]
    for separator in separators:
        index = lowered.find(separator.lower())
        if index >= 0:
            text = stripped[index + len(separator):].strip(" ：:\n\t")
            if text:
                show_to_local = separator == "帮我问一下" or _looks_like_show_to_local_request(stripped)
                return {
                    "text": text,
                    "target_language": "zh",
                    "show_to_local": show_to_local,
                }
    if _looks_like_show_to_local_request(stripped):
        text = quoted_text or stripped
        for prefix in ["帮我问一下", "show this", "say this to", "show to local", "show to staff"]:
            if lowered.startswith(prefix):
                text = stripped[len(prefix):].strip(" ：:\n\t")
                break
        if text:
            return {
                "text": text,
                "target_language": "zh",
                "show_to_local": True,
            }
    return None



def _extract_quoted_text(text: str) -> str | None:
    match = re.search(r"[\"“”'‘’](.+?)[\"“”'‘’]", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None



def _looks_like_show_to_local_request(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ["show this", "say this to", "show to local", "show to staff"]) or any(
        token in text for token in ["帮我问一下", "给工作人员看", "给工作人员", "翻给工作人员看"]
    )


def _fallback_parse_translation_query(query: str) -> dict[str, object] | None:
    stripped = query.strip()
    quoted_text = _extract_quoted_text(stripped)
    if quoted_text:
        return {
            "text": quoted_text,
            "target_language": "zh",
            "show_to_local": _looks_like_show_to_local_request(stripped),
        }

    for separator in ["：", ":"]:
        if separator not in stripped:
            continue
        prefix, suffix = stripped.split(separator, 1)
        suffix = suffix.strip()
        if suffix and (
            any(token in prefix for token in ["翻译", "翻成", "怎么说"]) or _looks_like_show_to_local_request(prefix)
        ):
            return {
                "text": suffix,
                "target_language": "zh",
                "show_to_local": _looks_like_show_to_local_request(prefix),
            }

    for pattern in [r"^(.+?)\s*用中文怎么说[？?]?$", r"^(.+?)\s*翻(?:译)?成中文[？?]?$"]:
        match = re.match(pattern, stripped)
        if not match:
            continue
        text = match.group(1).strip(" ：:\n\t")
        if text:
            return {
                "text": text,
                "target_language": "zh",
                "show_to_local": False,
            }
    return None



def _find_language_code(text: str) -> str | None:
    lowered = text.lower()
    for alias, language_code in sorted(_LANGUAGE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in lowered or alias in text:
            return language_code
    return None


def _infer_target_language_from_query(query: str, fallback_language: str) -> str:
    inferred = _find_language_code(query)
    if inferred is not None:
        return inferred
    return "fil" if fallback_language == "tl" else fallback_language


def _resolve_explicit_translation_source_language(*, query_text: str, user_language: str, target_language: str) -> str | None:
    inferred_source_language = _infer_source_language_from_text(query_text)
    if inferred_source_language and _base_language_code(inferred_source_language) != _base_language_code(target_language):
        return inferred_source_language
    if _base_language_code(user_language) == _base_language_code(target_language):
        return None
    return user_language



def _infer_source_language_from_text(text: str) -> str | None:
    if _contains_cjk(text):
        return "zh"
    if _contains_latin_letters(text):
        return "en"
    return None


def _base_language_code(language: str | None) -> str | None:
    if not language:
        return None
    lowered = language.lower().replace("_", "-")
    base = lowered.split("-", 1)[0]
    return "fil" if base == "tl" else base



def _contains_cjk(text: str) -> bool:
    return any("一" <= char <= "鿿" for char in text)



def _contains_latin_letters(text: str) -> bool:
    return any("a" <= char.lower() <= "z" for char in text)


def _build_display_instruction(user_language: str) -> str:
    lowered = user_language.lower()
    if lowered.startswith("zh"):
        return "请向工作人员展示以下文字。"
    if lowered.startswith("th"):
        return "โปรดแสดงข้อความต่อไปนี้ให้เจ้าหน้าที่ดู"
    if lowered.startswith("vi"):
        return "Hãy đưa câu sau cho nhân viên xem."
    if lowered.startswith("id"):
        return "Tunjukkan kalimat berikut kepada staf."
    if lowered.startswith("ms"):
        return "Tunjukkan ayat berikut kepada kakitangan tempatan."
    if lowered.startswith("fil") or lowered.startswith("tl"):
        return "Ipakita ang sumusunod na pangungusap sa lokal na kawani."
    if lowered.startswith("my"):
        return "ကျေးဇူးပြု၍ အောက်ပါစာကို ဝန်ထမ်းအား ပြပါ။"
    if lowered.startswith("km"):
        return "សូមបង្ហាញប្រយោគខាងក្រោមទៅបុគ្គលិកមូលដ្ឋាន។"
    if lowered.startswith("lo"):
        return "ກະລຸນາສະແດງຂໍ້ຄວາມຕໍ່ໄປນີ້ໃຫ້ພະນັກງານທ້ອງຖິ່ນເບິ່ງ"
    return "Please show the following text to local staff."

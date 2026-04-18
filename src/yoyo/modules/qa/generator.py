from __future__ import annotations

import json

from yoyo.modules.knowledge.schemas import HybridContext
from yoyo.modules.shared_text_sanitizer import (
    extract_fenced_json_object,
    looks_like_malformed_wrapper,
    sanitize_llm_text,
)
from yoyo.modules.llm.factory import get_llm_runtime
from yoyo.modules.qa.prompts import build_qa_generation_request
from yoyo.modules.qa.schemas import (
    AttractionExplainStructuredAnswer,
    LiveInfoStructuredAnswer,
    TranslationStructuredAnswer,
    TripAssistantStructuredAnswer,
)


async def generate_qa_answer(
    *,
    provider: str,
    model: str,
    intent: str,
    query: str,
    language: str,
    hybrid_context: HybridContext,
) -> tuple[str | None, dict[str, object]]:
    runtime = get_llm_runtime()
    request = build_qa_generation_request(
        provider=provider,
        model=model,
        intent=intent,
        query=query,
        language=language,
        hybrid_context=hybrid_context,
    )
    response = await runtime.generate(request)
    metadata = {
        "llm": {
            "provider": response.provider,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "usage": response.usage.model_dump(),
            "prompt_version": request.metadata.get("prompt_version"),
            "fallback_used": response.error is not None,
            "error": response.error.model_dump() if response.error else None,
        }
    }
    if response.error is not None or not response.text.strip():
        return None, metadata

    if intent == "translation":
        structured = _parse_translation_structured_answer(response.text)
        if structured is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "translation"
            return None, metadata
        if looks_like_malformed_wrapper(structured.answer):
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "translation"
            return None, metadata
        sanitized_answer = sanitize_llm_text(structured.answer)
        if sanitized_answer is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "translation"
            return None, metadata
        structured.answer = sanitized_answer
        metadata["llm"]["structured_output_valid"] = True
        metadata["llm"]["structured_output_type"] = "translation"
        metadata["llm"]["structured_output"] = structured.model_dump()
        return structured.answer, metadata

    if intent == "live_info":
        structured = _parse_live_info_structured_answer(response.text)
        if structured is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "live_info"
            return None, metadata
        if looks_like_malformed_wrapper(structured.answer):
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "live_info"
            return None, metadata
        sanitized_answer = sanitize_llm_text(structured.answer)
        if sanitized_answer is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "live_info"
            return None, metadata
        structured.answer = sanitized_answer
        metadata["llm"]["structured_output_valid"] = True
        metadata["llm"]["structured_output_type"] = "live_info"
        metadata["llm"]["structured_output"] = structured.model_dump()
        return structured.answer, metadata

    if intent == "trip_assistant":
        structured = _parse_trip_assistant_structured_answer(response.text)
        if structured is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "trip_assistant"
            return None, metadata
        if looks_like_malformed_wrapper(structured.answer):
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "trip_assistant"
            return None, metadata
        sanitized_answer = sanitize_llm_text(structured.answer)
        if sanitized_answer is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "trip_assistant"
            return None, metadata
        structured.answer = sanitized_answer
        metadata["llm"]["structured_output_valid"] = True
        metadata["llm"]["structured_output_type"] = "trip_assistant"
        metadata["llm"]["structured_output"] = structured.model_dump()
        return structured.answer, metadata

    if intent == "attraction_explain":
        structured = _parse_attraction_explain_structured_answer(response.text)
        if structured is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "attraction_explain"
            return None, metadata
        if looks_like_malformed_wrapper(structured.answer):
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "attraction_explain"
            return None, metadata
        sanitized_answer = sanitize_llm_text(structured.answer)
        if sanitized_answer is None:
            metadata["llm"]["structured_output_valid"] = False
            metadata["llm"]["structured_output_type"] = "attraction_explain"
            return None, metadata
        structured.answer = sanitized_answer
        metadata["llm"]["structured_output_valid"] = True
        metadata["llm"]["structured_output_type"] = "attraction_explain"
        metadata["llm"]["structured_output"] = structured.model_dump()
        return structured.answer, metadata

    return response.text.strip(), metadata



def _parse_translation_structured_answer(text: str) -> TranslationStructuredAnswer | None:
    payload = _load_json_object(text)
    if payload is None:
        return None
    try:
        structured = TranslationStructuredAnswer.model_validate(payload)
    except Exception:
        return None
    if not structured.answer.strip():
        return None
    return structured



def _parse_live_info_structured_answer(text: str) -> LiveInfoStructuredAnswer | None:
    payload = _load_json_object(text)
    if payload is None:
        return None
    try:
        structured = LiveInfoStructuredAnswer.model_validate(payload)
    except Exception:
        return None
    if not structured.answer.strip():
        return None
    return structured



def _parse_trip_assistant_structured_answer(text: str) -> TripAssistantStructuredAnswer | None:
    payload = _load_json_object(text)
    if payload is None:
        return None
    try:
        structured = TripAssistantStructuredAnswer.model_validate(payload)
    except Exception:
        return None
    if not structured.answer.strip():
        return None
    return structured



def _parse_attraction_explain_structured_answer(text: str) -> AttractionExplainStructuredAnswer | None:
    payload = _load_json_object(text)
    if payload is None:
        return None
    try:
        structured = AttractionExplainStructuredAnswer.model_validate(payload)
    except Exception:
        return None
    if not structured.answer.strip():
        return None
    return structured



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

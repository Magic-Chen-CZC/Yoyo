from __future__ import annotations

import json

from yoyo.modules.guide.prompts import build_guide_generation_request
from yoyo.modules.shared_text_sanitizer import extract_fenced_json_object
from yoyo.modules.guide.schemas import GuideBundleStructured
from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext
from yoyo.modules.llm.factory import get_llm_runtime


async def generate_guide_text_blocks(
    *,
    provider: str,
    model: str,
    summary: str | None,
    attractions: list[AttractionContext],
    profile: ProfileContext | None,
) -> tuple[dict[str, object] | None, dict[str, object]]:
    runtime = get_llm_runtime()
    request = build_guide_generation_request(
        provider=provider,
        model=model,
        summary=summary,
        attractions=attractions,
        profile=profile,
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

    parsed = _parse_json_payload(response.text)
    structured = _parse_guide_bundle(parsed)
    if structured is None:
        metadata["llm"]["structured_output_valid"] = False
        metadata["llm"]["structured_output_type"] = "guide_bundle"
        return None, metadata
    metadata["llm"]["structured_output_valid"] = True
    metadata["llm"]["structured_output_type"] = "guide_bundle"
    metadata["llm"]["structured_output"] = structured.model_dump()
    return structured.model_dump(), metadata



def _parse_guide_bundle(payload: dict[str, object] | None) -> GuideBundleStructured | None:
    if payload is None:
        return None
    try:
        structured = GuideBundleStructured.model_validate(payload)
    except Exception:
        return None
    if not structured.intro.strip() or not structured.outro.strip():
        return None
    if any(not stop.stop_name.strip() or not stop.narration.strip() for stop in structured.stop_scripts):
        return None
    return structured



def _parse_json_payload(text: str) -> dict[str, object] | None:
    try:
        payload = json.loads(text)
    except Exception:
        payload = extract_fenced_json_object(text)
        if payload is None:
            return None
    if not isinstance(payload, dict):
        return None
    return payload

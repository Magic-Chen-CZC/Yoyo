from __future__ import annotations

import json

from yoyo.modules.guide.prompts import build_guide_generation_request
from yoyo.modules.knowledge.schemas import AttractionContext, ProfileContext
from yoyo.modules.llm.factory import get_llm_runtime
from yoyo.modules.llm.schemas import LLMResponse


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
    return parsed, metadata



def _parse_json_payload(text: str) -> dict[str, object] | None:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None

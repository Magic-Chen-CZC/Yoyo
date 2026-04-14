from __future__ import annotations

from yoyo.modules.knowledge.schemas import HybridContext
from yoyo.modules.llm.factory import get_llm_runtime
from yoyo.modules.qa.prompts import build_qa_generation_request


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
    return response.text.strip(), metadata

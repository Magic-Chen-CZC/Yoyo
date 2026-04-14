from __future__ import annotations

import time

from yoyo.modules.llm.providers import get_provider
from yoyo.modules.llm.schemas import LLMError, LLMRequest, LLMResponse


class LLMRuntime:
    async def generate(self, request: LLMRequest) -> LLMResponse:
        provider = get_provider(request.provider)
        started = time.perf_counter()
        try:
            response = await provider.generate(request)
            response.latency_ms = (time.perf_counter() - started) * 1000
            return response
        except Exception as error:
            return LLMResponse(
                text="",
                provider=request.provider,
                model=request.model,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=LLMError(
                    error_type=error.__class__.__name__,
                    message=str(error),
                    retryable=False,
                ),
            )

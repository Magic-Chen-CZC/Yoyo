from __future__ import annotations

import time

import httpx

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
                error=_classify_error(error),
            )


def _classify_error(error: Exception) -> LLMError:
    message = str(error)
    retryable = False
    status_code = None
    provider_error_code = None

    if isinstance(error, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.NetworkError)):
        retryable = True
    elif isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        retryable = 500 <= status_code < 600
    else:
        lowered = message.lower()
        if "timeout" in lowered or "temporar" in lowered or "try again" in lowered:
            retryable = True
        if "code=" in message:
            provider_error_code = message.split("code=", 1)[1].split(":", 1)[0].strip()

    return LLMError(
        error_type=error.__class__.__name__,
        message=message,
        retryable=retryable,
        status_code=status_code,
        provider_error_code=provider_error_code,
    )

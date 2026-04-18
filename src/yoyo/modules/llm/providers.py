from __future__ import annotations

from typing import Any, Protocol

import httpx

from yoyo.core.config import get_settings
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, LLMResponse, LLMUsage, PromptMessage


class RuntimeProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...



def _messages_to_anthropic(messages: list[PromptMessage]) -> tuple[str | None, list[dict[str, Any]]]:
    system_prompt = None
    converted: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            system_prompt = message.content if system_prompt is None else f"{system_prompt}\n\n{message.content}"
            continue
        converted.append({"role": message.role, "content": message.content})
    return system_prompt, converted


class AnthropicRuntimeProvider:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("missing llm_api_key for anthropic runtime provider")

        system_prompt, messages = _messages_to_anthropic(request.messages)
        async with httpx.AsyncClient(timeout=request.options.timeout_seconds) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": request.model,
                    "max_tokens": request.options.max_tokens,
                    "temperature": request.options.temperature,
                    "system": system_prompt,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            text = payload["content"][0]["text"] if payload.get("content") else ""
            return LLMResponse(
                text=text,
                provider=request.provider,
                model=request.model,
                usage=LLMUsage(
                    prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"),
                    total_tokens=(usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
                ),
                raw_response=payload,
            )


class OpenRouterRuntimeProvider:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key or settings.eval_openrouter_api_key
        self.base_url = settings.openrouter_base_url.rstrip("/")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("missing openrouter_api_key for runtime provider")

        async with httpx.AsyncClient(timeout=request.options.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Yoyo Runtime",
                },
                json={
                    "model": request.model,
                    "messages": [message.model_dump() for message in request.messages],
                    "max_tokens": request.options.max_tokens,
                    "temperature": request.options.temperature,
                },
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            text = payload["choices"][0]["message"]["content"]
            return LLMResponse(
                text=text,
                provider=request.provider,
                model=request.model,
                usage=LLMUsage(
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    cost=usage.get("cost"),
                ),
                raw_response=payload,
            )


class GeminiRuntimeProvider:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.eval_google_api_key

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("missing eval_google_api_key for gemini runtime provider")

        prompt = "\n\n".join(message.content for message in request.messages)
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{request.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=request.options.timeout_seconds) as client:
            response = await client.post(
                endpoint,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": request.options.temperature,
                        "maxOutputTokens": request.options.max_tokens,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
            candidates = payload.get("candidates", [])
            text = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = " ".join(str(part.get("text", "")) for part in parts).strip()
            usage = payload.get("usageMetadata", {})
            return LLMResponse(
                text=text,
                provider=request.provider,
                model=request.model,
                usage=LLMUsage(
                    prompt_tokens=usage.get("promptTokenCount"),
                    completion_tokens=usage.get("candidatesTokenCount"),
                    total_tokens=usage.get("totalTokenCount"),
                ),
                raw_response=payload,
            )


_PROVIDER_REGISTRY = {
    "anthropic": lambda: AnthropicRuntimeProvider(),
    "openrouter": lambda: OpenRouterRuntimeProvider(),
    "google": lambda: GeminiRuntimeProvider(),
    "gemini": lambda: GeminiRuntimeProvider(),
}



def get_provider(provider: str) -> RuntimeProvider:
    factory = _PROVIDER_REGISTRY.get(provider)
    if factory is None:
        raise ValueError(f"unsupported runtime llm provider: {provider}")
    return factory()

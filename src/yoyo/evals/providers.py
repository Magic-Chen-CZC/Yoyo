from __future__ import annotations

from typing import Any, Protocol

import httpx

from yoyo.core.config import get_settings


class EvalProvider(Protocol):
    async def generate(self, prompt: str) -> dict[str, Any]: ...


class AnthropicEvalProvider:
    def __init__(self, model: str, api_key: str | None = None) -> None:
        settings = get_settings()
        self.model = model
        self.api_key = api_key or settings.llm_api_key

    async def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return {"text": f"[mock anthropic response] {prompt}", "usage": None}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            return {
                "text": payload["content"][0]["text"],
                "usage": {
                    "prompt_tokens": usage.get("input_tokens"),
                    "completion_tokens": usage.get("output_tokens"),
                    "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
                },
            }


class OpenRouterEvalProvider:
    def __init__(self, model: str, api_key: str | None = None) -> None:
        settings = get_settings()
        self.model = model
        self.api_key = api_key or settings.eval_openrouter_api_key or settings.openrouter_api_key

    async def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return {"text": f"[mock openrouter response] {prompt}", "usage": None}

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Yoyo Eval",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                },
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            return {
                "text": payload["choices"][0]["message"]["content"],
                "usage": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "cost": usage.get("cost"),
                },
            }


def get_provider(provider: str, model: str) -> EvalProvider:
    if provider == "anthropic":
        return AnthropicEvalProvider(model)
    if provider == "openrouter":
        return OpenRouterEvalProvider(model)

    raise ValueError(f"unsupported eval provider: {provider}")

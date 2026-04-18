from __future__ import annotations

# providers.py 封装不同模型供应商的调用方式。
# 当前阶段把 provider 扩展为注册表模式，便于后续继续补模型来源。
from typing import Any, Protocol

import httpx

from yoyo.core.config import get_settings


class EvalProvider(Protocol):
    async def generate(self, prompt: str) -> dict[str, Any]: ...


class MissingEvalAPIKeyError(RuntimeError):
    pass


class AnthropicEvalProvider:
    def __init__(self, model: str, api_key: str | None = None) -> None:
        settings = get_settings()
        self.model = model
        self.api_key = api_key or settings.llm_api_key

    async def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise MissingEvalAPIKeyError("missing anthropic eval api key")

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
            raise MissingEvalAPIKeyError("missing openrouter eval api key")

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


class GeminiEvalProvider:
    def __init__(self, model: str, api_key: str | None = None) -> None:
        settings = get_settings()
        self.model = model
        self.api_key = api_key or settings.eval_google_api_key

    async def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise MissingEvalAPIKeyError("missing google eval api key")

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                endpoint,
                json={
                    "contents": [
                        {
                            "parts": [{"text": prompt}],
                        }
                    ]
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
            return {
                "text": text or "[empty gemini response]",
                "usage": {
                    "prompt_tokens": usage.get("promptTokenCount"),
                    "completion_tokens": usage.get("candidatesTokenCount"),
                    "total_tokens": usage.get("totalTokenCount"),
                },
            }


class OpenAICompatibleEvalProvider:
    def __init__(self, model: str, api_key: str | None, base_url: str, label: str) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.label = label

    async def generate(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise MissingEvalAPIKeyError(f"missing {self.label} eval api key")

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
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
                },
            }


class QwenCompatibleEvalProvider(OpenAICompatibleEvalProvider):
    def __init__(self, model: str, api_key: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            model=model,
            api_key=api_key or settings.eval_dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            label="qwen-compatible",
        )


_PROVIDER_REGISTRY = {
    "anthropic": lambda model: AnthropicEvalProvider(model),
    "openrouter": lambda model: OpenRouterEvalProvider(model),
    "google": lambda model: GeminiEvalProvider(model),
    "gemini": lambda model: GeminiEvalProvider(model),
    "dashscope": lambda model: QwenCompatibleEvalProvider(model),
    "qwen-compatible": lambda model: QwenCompatibleEvalProvider(model),
}


def get_provider(provider: str, model: str) -> EvalProvider:
    factory = _PROVIDER_REGISTRY.get(provider)
    if factory is None:
        raise ValueError(f"unsupported eval provider: {provider}")
    return factory(model)

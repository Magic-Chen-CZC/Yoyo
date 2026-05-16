from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import json
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


class OpenAICompatibleRuntimeProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        missing_api_key_message: str,
        include_openrouter_headers: bool = False,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.missing_api_key_message = missing_api_key_message
        self.include_openrouter_headers = include_openrouter_headers

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError(self.missing_api_key_message)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.include_openrouter_headers:
            headers["HTTP-Referer"] = "http://localhost"
            headers["X-Title"] = "Yoyo Runtime"

        async with httpx.AsyncClient(timeout=request.options.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
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


class OpenRouterRuntimeProvider(OpenAICompatibleRuntimeProvider):
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            api_key=api_key or settings.openrouter_api_key or settings.eval_openrouter_api_key,
            base_url=settings.openrouter_base_url,
            missing_api_key_message="missing openrouter_api_key for runtime provider",
            include_openrouter_headers=True,
        )


class DashScopeRuntimeProvider(OpenAICompatibleRuntimeProvider):
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            api_key=api_key or settings.dashscope_api_key or settings.eval_dashscope_api_key,
            base_url=settings.dashscope_base_url,
            missing_api_key_message="missing dashscope_api_key for runtime provider",
        )


class VolcengineRuntimeProvider(OpenAICompatibleRuntimeProvider):
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        super().__init__(
            api_key=api_key or settings.volcengine_api_key or settings.eval_volcengine_api_key,
            base_url=settings.volcengine_base_url,
            missing_api_key_message="missing volcengine_api_key for runtime provider",
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


class HYMTRuntimeProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.hy_mt_api_key
        self.base_url = settings.hy_mt_base_url.rstrip("/")
        self.default_model = settings.hy_mt_model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        metadata = request.metadata or {}
        prompt = self._build_prompt(request.messages, metadata)
        async with httpx.AsyncClient(timeout=request.options.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": request.model or self.default_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": request.options.max_tokens,
                    "temperature": request.options.temperature,
                    "top_p": 0.6,
                },
            )
            response.raise_for_status()
            payload = response.json()
            usage = payload.get("usage", {})
            text = payload["choices"][0]["message"]["content"]
            return LLMResponse(
                text=text,
                provider=request.provider,
                model=request.model or self.default_model,
                usage=LLMUsage(
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                ),
                raw_response=payload,
            )

    def _build_prompt(self, messages: list[PromptMessage], metadata: dict[str, Any]) -> str:
        plain_text = str(metadata.get("plain_text") or "").strip()
        if not plain_text:
            return "\n\n".join(message.content for message in messages)
        source_language = str(metadata.get("source_language") or "auto")
        target_language = str(metadata.get("target_language") or "zh")
        return (
            "Translate the following text. Return only the translation with no explanation, no notes, and no extra sentences.\n\n"
            f"Source language: {source_language}\n"
            f"Target language: {target_language}\n\n"
            f"Text:\n{plain_text}"
        )


class XFYunITSRuntimeProvider:
    REQUEST_URI = "/v2/its"
    HTTP_METHOD = "POST"
    HTTP_PROTO = "HTTP/1.1"
    ALGORITHM = "hmac-sha256"

    def __init__(self) -> None:
        settings = get_settings()
        self.app_id = settings.xfyun_its_app_id
        self.api_key = settings.xfyun_its_api_key
        self.api_secret = settings.xfyun_its_api_secret
        self.host = settings.xfyun_its_host
        self.verify_ssl = settings.xfyun_its_verify_ssl

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.app_id or not self.api_key or not self.api_secret:
            raise RuntimeError("missing xfyun ITS credentials")

        metadata = request.metadata or {}
        source_language = str(metadata.get("source_language") or "auto")
        target_language = str(metadata.get("target_language") or "cn")
        text = str(metadata.get("plain_text") or self._extract_plain_text(request.messages))
        body = self._build_body(text, source_language, target_language)
        date_header = self._httpdate(datetime.datetime.utcnow())
        digest = self._digest(body)
        authorization = self._authorization(date_header, digest)
        url = f"https://{self.host}{self.REQUEST_URI}"

        async with httpx.AsyncClient(timeout=request.options.timeout_seconds, verify=self.verify_ssl) as client:
            response = await client.post(
                url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Method": self.HTTP_METHOD,
                    "Host": self.host,
                    "Date": date_header,
                    "Digest": digest,
                    "Authorization": authorization,
                },
            )
            response.raise_for_status()
            payload = response.json()
            code = str(payload.get("code", ""))
            if code not in {"", "0"}:
                raise RuntimeError(f"xfyun ITS error code={code}: {payload.get('message') or payload.get('desc') or 'unknown_error'}")
            translated_text = self._extract_translation_text(payload)
            return LLMResponse(
                text=translated_text,
                provider=request.provider,
                model=request.model,
                raw_response=payload,
            )

    def _build_body(self, text: str, source_language: str, target_language: str) -> str:
        content = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return json.dumps(
            {
                "common": {"app_id": self.app_id},
                "business": {
                    "from": self._normalize_language_code(source_language),
                    "to": self._normalize_language_code(target_language),
                },
                "data": {"text": content},
            },
            ensure_ascii=False,
        )

    def _authorization(self, date_header: str, digest: str) -> str:
        signature_origin = (
            f"host: {self.host}\n"
            f"date: {date_header}\n"
            f"{self.HTTP_METHOD} {self.REQUEST_URI} {self.HTTP_PROTO}\n"
            f"digest: {digest}"
        )
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_base64 = base64.b64encode(signature).decode("utf-8")
        return (
            f'api_key="{self.api_key}", algorithm="{self.ALGORITHM}", '
            f'headers="host date request-line digest", signature="{signature_base64}"'
        )

    def _digest(self, body: str) -> str:
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        return "SHA-256=" + base64.b64encode(digest).decode("utf-8")

    def _httpdate(self, dt: datetime.datetime) -> str:
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
        month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month - 1]
        return f"{weekday}, {dt.day:02d} {month} {dt.year:04d} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} GMT"

    def _extract_plain_text(self, messages: list[PromptMessage]) -> str:
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message.content.strip()
        return "\n\n".join(message.content for message in messages).strip()

    def _extract_translation_text(self, payload: dict[str, Any]) -> str:
        data = payload.get("data")
        if isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, dict):
                nested = result.get("trans_result")
                if isinstance(nested, dict):
                    text = nested.get("dst") or nested.get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
                text = result.get("trans_result") or result.get("dst") or result.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
        if isinstance(data, str) and data.strip():
            try:
                decoded = base64.b64decode(data).decode("utf-8")
            except Exception:
                decoded = data
            if decoded.strip():
                return decoded.strip()
        raise RuntimeError("xfyun ITS returned empty translation")

    def _normalize_language_code(self, language: str) -> str:
        lowered = language.lower().replace("_", "-")
        mapping = {
            "zh": "cn",
            "zh-cn": "cn",
            "zh-hans": "cn",
            "en": "en",
            "th": "th",
            "vi": "vi",
            "id": "id",
            "ms": "ms",
            "fil": "tl",
            "tl": "tl",
            "my": "my",
            "km": "km",
            "lo": "lo",
            "ja": "ja",
            "ko": "ko",
            "fr": "fr",
            "es": "es",
            "ru": "ru",
            "ar": "ar",
            "de": "de",
        }
        return mapping.get(lowered, lowered or "auto")


_PROVIDER_REGISTRY = {
    "anthropic": lambda: AnthropicRuntimeProvider(),
    "openrouter": lambda: OpenRouterRuntimeProvider(),
    "dashscope": lambda: DashScopeRuntimeProvider(),
    "qwen-compatible": lambda: DashScopeRuntimeProvider(),
    "volcengine": lambda: VolcengineRuntimeProvider(),
    "doubao": lambda: VolcengineRuntimeProvider(),
    "google": lambda: GeminiRuntimeProvider(),
    "gemini": lambda: GeminiRuntimeProvider(),
    "hy_mt": lambda: HYMTRuntimeProvider(),
    "xfyun_its": lambda: XFYunITSRuntimeProvider(),
}



def get_provider(provider: str) -> RuntimeProvider:
    factory = _PROVIDER_REGISTRY.get(provider)
    if factory is None:
        raise ValueError(f"unsupported runtime llm provider: {provider}")
    return factory()

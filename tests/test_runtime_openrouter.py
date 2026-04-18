import pytest

from yoyo.modules.llm.providers import OpenRouterRuntimeProvider
from yoyo.modules.llm.schemas import GenerationOptions, LLMRequest, PromptMessage


@pytest.mark.asyncio
async def test_openrouter_runtime_provider_uses_configured_base_url(monkeypatch) -> None:
    class FakeSettings:
        openrouter_api_key = "test-key"
        eval_openrouter_api_key = ""
        openrouter_base_url = "https://openrouter.example/api/v1"

    requests: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            requests.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.llm.providers.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("yoyo.modules.llm.providers.httpx.AsyncClient", FakeClient)

    provider = OpenRouterRuntimeProvider()
    response = await provider.generate(
        LLMRequest(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            messages=[PromptMessage(role="user", content="hello")],
            options=GenerationOptions(),
        )
    )

    assert response.text == "ok"
    assert requests[0]["url"] == "https://openrouter.example/api/v1/chat/completions"
    assert requests[0]["headers"]["Authorization"] == "Bearer test-key"

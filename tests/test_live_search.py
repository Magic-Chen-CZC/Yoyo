import pytest

from yoyo.modules.qa.live_info import build_live_info_payload
from yoyo.modules.qa.live_search import TavilyLiveSearchProvider


@pytest.mark.asyncio
async def test_tavily_provider_http_error_returns_structured_error(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            raise Exception("boom")

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, *args, **kwargs):
            raise Exception("boom")

    monkeypatch.setattr("httpx.AsyncClient", lambda timeout=60: FakeClient())

    provider = TavilyLiveSearchProvider(api_key="dummy")
    result = await provider.search("What should I verify before visiting the Forbidden City today?")

    assert "summary" in result
    assert "sources" in result
    assert result["sources"][0]["type"] == "error"


@pytest.mark.asyncio
async def test_live_info_payload_normalizes_placeholder_sources(monkeypatch) -> None:
    async def fake_search(self, query: str) -> dict[str, object]:
        return {
            "summary": "placeholder summary",
            "sources": [{"type": "placeholder", "name": "stub", "updated_at": None}],
        }

    monkeypatch.setattr(TavilyLiveSearchProvider, "search", fake_search)
    result = await build_live_info_payload("What should I verify today?", None)

    assert "summary" in result
    assert "sources" in result
    assert "updated_at" in result
    assert "not_confirmed" in result
    assert "confidence" in result

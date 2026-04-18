# 这份测试验证 live search / live info 在异常或占位场景下是否还能返回稳定结构。
import pytest

from yoyo.modules.qa.live_info import build_live_info_payload
from yoyo.modules.qa.live_search import TavilyLiveSearchProvider, get_live_search_provider


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


def test_get_live_search_provider_rejects_unsupported_provider(monkeypatch) -> None:
    class FakeSettings:
        live_search_provider = "unknown"

    monkeypatch.setattr("yoyo.modules.qa.live_search.get_settings", lambda: FakeSettings())

    with pytest.raises(ValueError, match="unsupported live search provider"):
        get_live_search_provider()


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

# 这份测试验证 live search / live info 在异常或占位场景下是否还能返回稳定结构。
import pytest

from yoyo.modules.qa.live_info import build_live_info_payload
from yoyo.modules.qa.live_info_cache import build_live_info_cache_key, classify_live_info_type
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
    monkeypatch.setattr("yoyo.modules.qa.live_info.get_cached_live_info", _empty_cache)
    monkeypatch.setattr("yoyo.modules.qa.live_info.set_cached_live_info", _noop_cache_set)

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


@pytest.mark.asyncio
async def test_live_info_payload_returns_cached_payload(monkeypatch) -> None:
    async def fake_get_cached_live_info(cache_key: str) -> dict[str, object]:
        return {
            "summary": "cached opening summary",
            "sources": [],
            "updated_at": "2026-05-15T00:00:00+00:00",
            "not_confirmed": False,
            "confidence": "medium",
            "status": "available",
            "reason": None,
            "cache_hit": True,
            "cache_key": cache_key,
            "cached_at": "2026-05-15T00:00:00+00:00",
            "cache_ttl_seconds": 900,
            "info_type": "opening",
        }

    async def fail_set_cache(*args, **kwargs) -> None:
        raise AssertionError("cache hit should not be written again")

    monkeypatch.setattr("yoyo.modules.qa.live_info.get_cached_live_info", fake_get_cached_live_info)
    monkeypatch.setattr("yoyo.modules.qa.live_info.set_cached_live_info", fail_set_cache)

    result = await build_live_info_payload("故宫今天开放吗？", "Forbidden City")

    assert result["summary"] == "cached opening summary"
    assert result["cache_hit"] is True
    assert result["info_type"] == "opening"


@pytest.mark.asyncio
async def test_live_info_payload_writes_cache_on_miss(monkeypatch) -> None:
    stored: dict[str, object] = {}

    class FakeProvider:
        async def search(self, query: str) -> dict[str, object]:
            return {
                "summary": "fresh opening summary",
                "sources": [{"type": "web", "name": "official", "url": "https://example.com"}],
                "status": "available",
                "reason": None,
            }

    async def fake_set_cached_live_info(
        cache_key: str,
        payload: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        stored["cache_key"] = cache_key
        stored["payload"] = dict(payload)
        stored["ttl_seconds"] = ttl_seconds

    monkeypatch.setattr("yoyo.modules.qa.live_info.get_cached_live_info", _empty_cache)
    monkeypatch.setattr("yoyo.modules.qa.live_info.set_cached_live_info", fake_set_cached_live_info)
    monkeypatch.setattr(
        "yoyo.modules.qa.live_info.get_live_search_provider",
        lambda: FakeProvider(),
    )

    result = await build_live_info_payload("故宫今天开放吗？", "Forbidden City")

    assert result["summary"] == "fresh opening summary"
    assert result["cache_hit"] is False
    assert result["info_type"] == "opening"
    assert stored["ttl_seconds"] == 900
    assert "forbidden-city:opening" in str(stored["cache_key"])


def test_live_info_cache_key_groups_opening_queries_by_subject() -> None:
    first = build_live_info_cache_key(
        query="故宫今天开放吗？",
        subject="Forbidden City",
        date_text="2026-05-15",
    )
    second = build_live_info_cache_key(
        query="今天故宫开门吗？",
        subject="Forbidden City",
        date_text="2026-05-15",
    )

    assert classify_live_info_type("故宫今天开放吗？") == "opening"
    assert first == second


async def _empty_cache(cache_key: str) -> None:
    return None


async def _noop_cache_set(
    cache_key: str,
    payload: dict[str, object],
    ttl_seconds: int,
) -> None:
    return None

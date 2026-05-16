import pytest

from yoyo.modules.integrations.amap.client import AmapRouteClient


@pytest.mark.asyncio
async def test_amap_weather_returns_unavailable_without_key() -> None:
    client = AmapRouteClient(api_key="")

    result = await client.get_weather("故宫")

    assert result["status"] == "unavailable"
    assert result["reason"] == "missing_provider_config"
    assert result["location_name"] == "故宫"


@pytest.mark.asyncio
async def test_amap_weather_returns_degraded_without_location() -> None:
    client = AmapRouteClient(api_key="dummy")

    result = await client.get_weather(None)

    assert result["status"] == "degraded"
    assert result["reason"] == "missing_location_name"


@pytest.mark.asyncio
async def test_amap_weather_returns_available_payload(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        assert address == "故宫"
        return {
            "status": "available",
            "reason": None,
            "formatted_address": "故宫博物院",
            "province": "北京市",
            "city": "北京市",
            "adcode": "110101",
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/weather/weatherInfo"
        assert params["city"] == "110101"
        return {
            "status": "1",
            "lives": [
                {
                    "weather": "晴",
                    "temperature": "25",
                    "winddirection": "东北",
                    "windpower": "3",
                    "humidity": "40",
                    "reporttime": "2026-05-09 10:00:00",
                }
            ],
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_weather("故宫")

    assert result["status"] == "available"
    assert result["reason"] is None
    assert result["location_name"] == "故宫博物院"
    assert result["adcode"] == "110101"
    assert result["weather"] == "晴"
    assert result["temperature_celsius"] == "25"


@pytest.mark.asyncio
async def test_amap_weather_prefers_known_chinese_alias_for_english_place_names(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")
    captured: list[str] = []

    async def fake_geocode(address: str) -> dict[str, object]:
        captured.append(address)
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "province": "北京市",
            "city": "北京市",
            "adcode": "110101",
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        return {"status": "1", "lives": [{"weather": "晴"}]}

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    await client.get_weather("Forbidden City")

    assert captured == ["故宫"]


@pytest.mark.asyncio
async def test_amap_weather_returns_degraded_when_provider_payload_is_empty(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "province": "北京市",
            "city": "北京市",
            "adcode": "110101",
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        return {"status": "1", "lives": []}

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_weather("故宫")

    assert result["status"] == "degraded"
    assert result["reason"] == "empty_weather_payload"

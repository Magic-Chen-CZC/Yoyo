import pytest

from yoyo.modules.integrations.amap.client import AmapRouteClient


@pytest.mark.asyncio
async def test_amap_navigation_returns_degraded_when_endpoint_missing() -> None:
    client = AmapRouteClient(api_key="dummy")

    result = await client.get_text_navigation(origin_name="天安门", destination_name=None)

    assert result["status"] == "degraded"
    assert result["reason"] == "missing_origin_or_destination"
    assert result["mode"] == "walking"
    assert result["steps"] == []


@pytest.mark.asyncio
async def test_amap_navigation_returns_unavailable_without_key() -> None:
    client = AmapRouteClient(api_key="")

    result = await client.get_text_navigation(origin_name="天安门", destination_name="故宫")

    assert result["status"] == "unavailable"
    assert result["reason"] == "missing_provider_config"
    assert result["steps"] == []


@pytest.mark.asyncio
async def test_amap_navigation_returns_available_payload(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        mapping = {
            "天安门": {
                "status": "available",
                "reason": None,
                "formatted_address": "北京市东城区天安门",
                "location": (116.397, 39.908),
            },
            "故宫": {
                "status": "available",
                "reason": None,
                "formatted_address": "故宫",
                "location": (116.397, 39.918),
            },
        }
        return mapping[address]

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        if path == "/v3/direction/walking":
            assert params["origin"] == "116.3976,39.905"
            assert params["destination"] == "116.3972,39.9163"
            return {
                "status": "1",
                "route": {
                    "paths": [
                        {
                            "distance": "1064",
                            "duration": "851",
                            "steps": [
                                {
                                    "instruction": "向北步行566米直行",
                                    "road": "南池子大街",
                                    "orientation": "北",
                                    "distance": "566",
                                    "duration": "450",
                                    "action": "直行",
                                    "assistant_action": "到达目的地",
                                    "polyline": "116.397,39.908;116.397,39.914",
                                },
                                {
                                    "instruction": "向西步行30米向右前方行走",
                                    "road": "东华门街",
                                    "orientation": "西",
                                    "distance": "30",
                                    "duration": "20",
                                    "polyline": "116.397,39.914;116.397,39.918",
                                },
                            ],
                        }
                    ]
                },
            }
        assert path == "/v3/geocode/regeo"
        assert params["batch"] == "true"
        assert params["location"] == "116.397,39.914|116.397,39.918"
        return {
            "status": "1",
            "regeocodes": [
                {
                    "roadinters": [
                        {
                            "first_name": "南池子大街",
                            "second_name": "东华门街",
                            "distance": "20",
                        }
                    ]
                },
                {"pois": [{"name": "故宫博物院东华门", "distance": "35"}]},
            ],
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="天安门", destination_name="故宫")

    assert result["status"] == "available"
    assert result["reason"] is None
    assert result["origin_name"] == "天安门广场"
    assert result["destination_name"] == "故宫"
    assert result["distance_meters"] == 1064
    assert result["duration_seconds"] == 851
    assert len(result["steps"]) == 2
    assert result["steps"][0]["instruction"] == "向北步行566米直行"
    assert result["steps"][0]["orientation"] == "北"
    assert result["steps"][0]["polyline"] == "116.397,39.908;116.397,39.914"
    assert result["steps"][0]["end_location"] == (116.397, 39.914)
    assert result["steps"][0]["turn_location_text"] == "南池子大街与东华门街交叉口附近"
    assert result["steps"][1]["turn_location_text"] == "故宫博物院东华门附近"


@pytest.mark.asyncio
async def test_amap_navigation_prefers_local_registered_coordinates(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        raise AssertionError(f"unexpected geocode call for {address}")

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/direction/walking"
        assert params["origin"] == "116.401304,39.905374"
        assert params["destination"] == "116.3977,39.8994"
        return {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "900",
                        "duration": "720",
                        "steps": [{"instruction": "沿广场步行900米到达目的地"}],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="国家博物馆", destination_name="正阳门")

    assert result["status"] == "available"
    assert result["origin_name"] == "中国国家博物馆"
    assert result["destination_name"] == "正阳门"


@pytest.mark.asyncio
async def test_amap_navigation_supports_transit_mode(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        mapping = {
            "故宫": {
                "status": "available",
                "reason": None,
                "formatted_address": "故宫",
                "location": (116.397, 39.918),
            },
            "颐和园": {
                "status": "available",
                "reason": None,
                "formatted_address": "颐和园",
                "location": (116.273, 39.999),
            },
        }
        return mapping[address]

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/direction/transit/integrated"
        assert params["origin"] == "116.3972,39.9163"
        assert params["destination"] == "116.2755,39.9996"
        assert params["city"] == "北京"
        return {
            "status": "1",
            "route": {
                "transits": [
                    {
                        "distance": "18200",
                        "duration": "3180",
                        "segments": [
                            {
                                "walking": {
                                    "steps": [
                                        {
                                            "instruction": "步行至天安门东站",
                                            "distance": "520",
                                            "duration": "420",
                                        }
                                    ]
                                },
                                "bus": {
                                    "buslines": [
                                        {
                                            "name": "地铁1号线(古城方向)",
                                            "departure_stop": {"name": "天安门东"},
                                            "arrival_stop": {"name": "西单"},
                                            "via_num": "2",
                                            "distance": "2300",
                                            "duration": "540",
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="故宫", destination_name="颐和园", mode="transit")

    assert result["status"] == "available"
    assert result["mode"] == "transit"
    assert result["distance_meters"] == 18200
    assert result["duration_seconds"] == 3180
    assert result["steps"][0]["instruction"] == "步行至天安门东站"
    assert result["steps"][1]["instruction"] == "从天安门东乘坐地铁1号线(古城方向)到西单，途经2站"


@pytest.mark.asyncio
async def test_amap_navigation_rejects_transit_payload_without_vehicle_step(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/direction/transit/integrated"
        return {
            "status": "1",
            "route": {
                "transits": [
                    {
                        "distance": "23000",
                        "duration": "9600",
                        "segments": [
                            {
                                "walking": {
                                    "steps": [
                                        {"instruction": "步行14米右转"},
                                        {"instruction": "步行401米向左前方行走"},
                                    ]
                                },
                                "bus": {"buslines": []},
                            }
                        ],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="颐和园", destination_name="北海公园", mode="transit")

    assert result["status"] == "degraded"
    assert result["reason"] == "empty_navigation_payload"
    assert result["steps"] == []


@pytest.mark.asyncio
async def test_amap_navigation_bus_preference_uses_no_subway_strategy(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/direction/transit/integrated"
        assert params["strategy"] == "5"
        return {
            "status": "1",
            "route": {
                "transits": [
                    {
                        "distance": "3600",
                        "duration": "1800",
                        "segments": [
                            {
                                "bus": {
                                    "buslines": [
                                        {
                                            "name": "103路(动物园枢纽站--北京站西)",
                                            "type": "无轨电车",
                                            "departure_stop": {"name": "西四路口东"},
                                            "arrival_stop": {"name": "西安门"},
                                        }
                                    ]
                                }
                            }
                        ],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(
        origin_name="故宫",
        destination_name="北海公园",
        mode="transit",
        transit_preference="bus",
    )

    assert result["status"] == "available"
    assert result["vehicle_types"] == ["bus"]
    assert "103路" in result["steps"][0]["instruction"]


@pytest.mark.asyncio
async def test_amap_navigation_subway_preference_filters_bus_only_route(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert params["strategy"] == "0"
        return {
            "status": "1",
            "route": {
                "transits": [
                    {
                        "distance": "3600",
                        "duration": "1800",
                        "segments": [
                            {
                                "bus": {
                                    "buslines": [
                                        {
                                            "name": "103路(动物园枢纽站--北京站西)",
                                            "type": "无轨电车",
                                            "departure_stop": {"name": "西四路口东"},
                                            "arrival_stop": {"name": "西安门"},
                                        }
                                    ]
                                }
                            }
                        ],
                    },
                    {
                        "distance": "6200",
                        "duration": "2100",
                        "segments": [
                            {
                                "bus": {
                                    "buslines": [
                                        {
                                            "name": "地铁4号线大兴线(安河桥北--天宫院)",
                                            "type": "地铁线路",
                                            "departure_stop": {"name": "北宫门"},
                                            "arrival_stop": {"name": "西四"},
                                        }
                                    ]
                                }
                            }
                        ],
                    },
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(
        origin_name="故宫",
        destination_name="北海公园",
        mode="transit",
        transit_preference="subway",
    )

    assert result["status"] == "available"
    assert result["vehicle_types"] == ["subway"]
    assert "地铁4号线" in result["steps"][0]["instruction"]


@pytest.mark.asyncio
async def test_amap_navigation_does_not_treat_bus_to_metro_station_as_subway(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "location": (116.397, 39.918),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert params["strategy"] == "0"
        return {
            "status": "1",
            "route": {
                "transits": [
                    {
                        "distance": "1800",
                        "duration": "1200",
                        "segments": [
                            {
                                "bus": {
                                    "buslines": [
                                        {
                                            "name": "332路(前门--地铁北宫门站)",
                                            "type": "普通公交线路",
                                            "departure_stop": {"name": "前门"},
                                            "arrival_stop": {"name": "前门西"},
                                        }
                                    ]
                                }
                            }
                        ],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(
        origin_name="正阳门",
        destination_name="天安门广场",
        mode="transit",
        transit_preference="subway",
    )

    assert result["status"] == "degraded"
    assert result["reason"] == "empty_navigation_payload"
    assert result["steps"] == []


@pytest.mark.asyncio
async def test_amap_navigation_normalizes_non_string_step_fields(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "location": (116.397, 39.908),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        return {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "1064",
                        "duration": "851",
                        "steps": [
                            {
                                "instruction": "向北步行566米直行",
                                "road": [],
                                "distance": "566",
                                "duration": "450",
                                "action": [],
                                "assistant_action": [],
                            }
                        ],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="天安门", destination_name="故宫")

    assert result["status"] == "available"
    assert result["steps"] == [
            {
                "instruction": "向北步行566米直行",
                "road": None,
                "orientation": None,
                "distance_meters": 566,
                "duration_seconds": 450,
                "action": None,
                "assistant_action": None,
                "polyline": None,
                "end_location": None,
            }
        ]


@pytest.mark.asyncio
async def test_amap_navigation_routes_known_english_place_names_with_local_coordinates(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        raise AssertionError(f"known English place should skip geocode: {address}")

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/direction/walking"
        assert params["origin"] == "116.3976,39.905"
        assert params["destination"] == "116.3972,39.9163"
        return {"status": "1", "route": {"paths": []}}

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    await client.get_text_navigation(origin_name="Tiananmen Square", destination_name="Forbidden City")


@pytest.mark.asyncio
async def test_amap_navigation_uses_known_coordinates_without_geocoding(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fail_geocode(address: str) -> dict[str, object]:
        raise AssertionError(f"known coordinates should skip geocode: {address}")

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        assert path == "/v3/direction/walking"
        assert params["origin"] == "116.3976,39.905"
        assert params["destination"] == "116.412,39.8837"
        return {
            "status": "1",
            "route": {
                "paths": [
                    {
                        "distance": "4200",
                        "duration": "3100",
                        "steps": [{"instruction": "沿中轴线附近道路步行"}],
                    }
                ]
            },
        }

    monkeypatch.setattr(client, "_geocode", fail_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(
        origin_name="当前位置",
        destination_name="Temple of Heaven",
        origin_location=(116.3976, 39.905),
        destination_location=(116.412, 39.8837),
    )

    assert result["status"] == "available"
    assert result["origin_name"] == "当前位置"
    assert result["destination_name"] == "天坛"
    assert result["distance_meters"] == 4200


@pytest.mark.asyncio
async def test_amap_navigation_rejects_geocode_outside_beijing(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        if path == "/v3/geocode/geo":
            return {
                "status": "1",
                "geocodes": [
                    {
                        "formatted_address": "广西壮族自治区某地天坛",
                        "province": "广西壮族自治区",
                        "city": "桂林市",
                        "adcode": "450300",
                        "location": "110.290,25.273",
                    }
                ],
            }
        raise AssertionError("routing should not be called after out-of-Beijing geocode")

    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="外地起点", destination_name="外地终点")

    assert result["status"] == "degraded"
    assert result["reason"] == "location_resolution_failed"


@pytest.mark.asyncio
async def test_amap_navigation_returns_degraded_when_route_payload_is_empty(monkeypatch) -> None:
    client = AmapRouteClient(api_key="dummy")

    async def fake_geocode(address: str) -> dict[str, object]:
        return {
            "status": "available",
            "reason": None,
            "formatted_address": address,
            "location": (116.397, 39.908),
        }

    async def fake_get_json(path: str, params: dict[str, object]) -> dict[str, object]:
        return {"status": "1", "route": {"paths": []}}

    monkeypatch.setattr(client, "_geocode", fake_geocode)
    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = await client.get_text_navigation(origin_name="天安门", destination_name="故宫")

    assert result["status"] == "degraded"
    assert result["reason"] == "empty_navigation_payload"

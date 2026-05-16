import pytest

from yoyo.modules.knowledge.hybrid_context_builder import _resolve_navigation_slots
from yoyo.modules.knowledge.navigation_retriever import get_navigation_context
from yoyo.modules.knowledge.schemas import NavigationLeg, NavigationSlotPayload, NavigationStep
from yoyo.modules.qa.formatters import format_navigation_text_answer
from yoyo.modules.qa.orchestrator import (
    _navigation_clarification_selection_from_fallback,
    _resolve_pending_navigation_clarification_selection,
    _should_try_pending_clarification_fallback,
)
from yoyo.modules.qa.schemas import IntentRouterFallbackResult


@pytest.mark.asyncio
async def test_navigation_retriever_aggregates_multi_leg_routes(monkeypatch) -> None:
    async def fake_get_text_navigation(self, *, origin_name: str | None, destination_name: str | None, mode: str | None = None):
        mapping = {
            ("Tiananmen Square", "Forbidden City"): {
                "origin_name": "Tiananmen Square",
                "destination_name": "Forbidden City",
                "mode": mode or "walking",
                "distance_meters": 1000,
                "duration_seconds": 800,
                "steps": [{"instruction": "Walk north to Forbidden City"}],
                "status": "available",
                "reason": None,
                "source": "amap",
            },
            ("Forbidden City", "Jingshan Park"): {
                "origin_name": "Forbidden City",
                "destination_name": "Jingshan Park",
                "mode": mode or "walking",
                "distance_meters": 600,
                "duration_seconds": 500,
                "steps": [{"instruction": "Continue north to Jingshan Park"}],
                "status": "available",
                "reason": None,
                "source": "amap",
            },
        }
        return mapping[(origin_name, destination_name)]

    monkeypatch.setattr(
        "yoyo.modules.integrations.amap.client.AmapRouteClient.get_text_navigation",
        fake_get_text_navigation,
    )

    context = await get_navigation_context(
        slot_result=NavigationSlotPayload(
            origin="Tiananmen Square",
            destinations=["Forbidden City", "Jingshan Park"],
            mode="walking",
            source="rule",
            request_kind="multi_leg",
            reason=None,
        )
    )

    assert context.status == "available"
    assert context.origin_name == "Tiananmen Square"
    assert context.destination_name == "Jingshan Park"
    assert context.distance_meters == 1600
    assert context.duration_seconds == 1300
    assert len(context.legs) == 2
    assert context.legs[0].destination_name == "Forbidden City"
    assert context.legs[1].destination_name == "Jingshan Park"
    assert len(context.steps) == 2


def test_navigation_formatter_keeps_transit_vehicle_step_after_station_walk() -> None:
    walking_steps = [NavigationStep(instruction=f"步行{i}米") for i in range(1, 13)]
    leg = NavigationLeg(
        origin_name="颐和园",
        destination_name="北海公园",
        requested_mode="transit",
        final_mode="transit",
        distance_meters=18111,
        duration_seconds=3892,
        steps=[
            *walking_steps,
            NavigationStep(
                instruction="从北宫门乘坐地铁4号线大兴线(安河桥北--天宫院)到西四，途经12站",
                action="乘车",
            ),
            NavigationStep(instruction="沿文津街北岔步行205米"),
        ],
    )

    answer = format_navigation_text_answer(
        "颐和园",
        "北海公园",
        leg.steps,
        18111,
        3892,
        legs=[leg],
    )

    assert "公共交通" in answer
    assert "从北宫门乘坐地铁4号线大兴线" in answer
    assert "全程约 18111 米，约 64 分钟" in answer


def test_navigation_formatter_outputs_walking_turn_points_without_truncation() -> None:
    steps = [
        NavigationStep(
            instruction="沿景山西街向北步行285米向左前方行走",
            road="景山西街",
            orientation="北",
            distance_meters=285,
            action="向左前方行走",
            turn_location_text="景山西街与地安门西大街交叉口附近",
        ),
        NavigationStep(
            instruction="沿地安门西大街向西步行410米右转",
            road="地安门西大街",
            orientation="西",
            distance_meters=410,
            action="右转",
            turn_location_text="北海北门附近",
        ),
        *[NavigationStep(instruction=f"继续步行{i}米", distance_meters=i) for i in range(1, 7)],
    ]

    answer = format_navigation_text_answer(
        "景山公园",
        "恭王府",
        steps,
        2323,
        1800,
        legs=[
            NavigationLeg(
                origin_name="景山公园",
                destination_name="恭王府",
                requested_mode="walking",
                final_mode="walking",
                distance_meters=2323,
                duration_seconds=1800,
                steps=steps,
            )
        ],
    )

    assert "沿景山西街向北步行约 285 米，到景山西街与地安门西大街交叉口附近，向左前方行走" in answer
    assert "沿地安门西大街向西步行约 410 米，到北海北门附近，右转" in answer
    assert "步行约 6 米" in answer
    assert "细分步骤" not in answer


@pytest.mark.asyncio
async def test_navigation_retriever_falls_back_to_walking_when_transit_is_empty(monkeypatch) -> None:
    calls = []

    async def fake_get_text_navigation(self, **kwargs):
        calls.append(kwargs["mode"])
        if kwargs["mode"] == "transit":
            return {
                "origin_name": "Tiananmen Square",
                "destination_name": "Forbidden City",
                "mode": "transit",
                "distance_meters": None,
                "duration_seconds": None,
                "steps": [],
                "status": "degraded",
                "reason": "empty_navigation_payload",
                "source": "amap",
            }
        return {
            "origin_name": "Tiananmen Square",
            "destination_name": "Forbidden City",
            "mode": "walking",
            "distance_meters": 980,
            "duration_seconds": 720,
            "steps": [{"instruction": "沿长安街向北步行"}],
            "status": "available",
            "reason": None,
            "source": "amap",
        }

    monkeypatch.setattr(
        "yoyo.modules.integrations.amap.client.AmapRouteClient.get_text_navigation",
        fake_get_text_navigation,
    )

    context = await get_navigation_context(
        slot_result=NavigationSlotPayload(
            origin="Tiananmen Square",
            destinations=["Forbidden City"],
            mode="transit",
            source="rule",
            request_kind="explicit_route",
            reason=None,
        )
    )
    answer = format_navigation_text_answer(
        context.origin_name,
        context.destination_name,
        context.steps,
        context.distance_meters,
        context.duration_seconds,
        legs=context.legs,
    )

    assert calls == ["transit", "walking"]
    assert context.status == "available"
    assert context.mode == "transit"
    assert context.final_mode == "walking"
    assert context.mode_fallback_used is True
    assert context.legs[0].provider_reason == "empty_navigation_payload"
    assert "当前没有合适的公共交通，返回给你步行方案。" in answer
    assert "高德" not in answer


@pytest.mark.asyncio
async def test_navigation_slot_keeps_commercial_alias_as_clarification_candidate() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "去正阳门餐厅怎么走？",
        attraction=None,
        session_context={"current_stop_name": "Tiananmen Square"},
    )

    assert slot_result.request_kind == "destination_only"
    assert slot_result.destinations == ["正阳门餐厅"]
    assert slot_result.destination_places[0].source == "geocode_candidate"
    assert slot_result.destination_places[0].reason == "registered_alias_with_ambiguity_signal"


@pytest.mark.asyncio
async def test_navigation_context_clarifies_commercial_or_address_ambiguity(monkeypatch) -> None:
    async def fake_search_place_candidates(self, keyword: str | None, *, limit: int = 5):
        assert keyword == "正阳门餐厅"
        return [
            {
                "name": "正阳门餐厅",
                "display_name": "正阳门餐厅",
                "address": "东城区前门附近",
                "district": "东城区",
                "poi_type": "餐饮服务;中餐厅",
                "longitude": 116.398,
                "latitude": 39.899,
                "adcode": "110101",
                "source": "amap_candidate",
                "confidence": 0.7,
            }
        ]

    async def fail_get_text_navigation(self, **kwargs):
        raise AssertionError("ambiguous place should clarify before route planning")

    monkeypatch.setattr(
        "yoyo.modules.integrations.amap.client.AmapRouteClient.search_place_candidates",
        fake_search_place_candidates,
    )
    monkeypatch.setattr(
        "yoyo.modules.integrations.amap.client.AmapRouteClient.get_text_navigation",
        fail_get_text_navigation,
    )

    context = await get_navigation_context(
        slot_result=NavigationSlotPayload(
            origin="Tiananmen Square",
            destinations=["正阳门餐厅"],
            destination_places=[
                {
                    "raw_text": "正阳门餐厅",
                    "name": "正阳门餐厅",
                    "display_name": "正阳门餐厅",
                    "source": "geocode_candidate",
                    "confidence": 0.46,
                    "reason": "registered_alias_with_ambiguity_signal",
                }
            ],
            mode="walking",
            source="rule",
            request_kind="destination_only",
        )
    )
    answer = format_navigation_text_answer(
        context.origin_name,
        context.destination_name,
        context.steps,
        context.distance_meters,
        context.duration_seconds,
        clarification=context.clarification,
    )

    assert context.status == "clarification"
    assert context.clarification is not None
    assert context.clarification.reason == "commercial_or_address_ambiguity"
    assert context.clarification.candidates[0].display_name == "正阳门"
    assert "正阳门餐厅" in answer
    assert "选第一个" in answer


@pytest.mark.asyncio
async def test_navigation_clarification_selection_rehydrates_selected_candidate() -> None:
    pending = _pending_navigation_clarification_history()
    selection = _resolve_pending_navigation_clarification_selection("选第2个", [pending])
    assert selection is not None

    slot_result, debug = await _resolve_navigation_slots(
        "选第2个",
        attraction=None,
        session_context={"navigation_clarification_selection": selection},
    )

    assert debug["source"] == "clarification_selection"
    assert slot_result.destinations == ["正阳门餐厅"]
    assert slot_result.destination_places[0].source == "amap_candidate"
    assert slot_result.destination_places[0].longitude == 116.398


@pytest.mark.asyncio
async def test_navigation_clarification_selection_supports_top_bottom_and_middle_words() -> None:
    pending = _pending_navigation_clarification_history(
        candidates=[
            {
                "index": 1,
                "name": "候选一",
                "display_name": "候选一",
                "latitude": 39.1,
                "longitude": 116.1,
                "adcode": "110101",
                "source": "amap_candidate",
                "confidence": 0.7,
            },
            {
                "index": 2,
                "name": "候选二",
                "display_name": "候选二",
                "latitude": 39.2,
                "longitude": 116.2,
                "adcode": "110101",
                "source": "amap_candidate",
                "confidence": 0.7,
            },
            {
                "index": 3,
                "name": "候选三",
                "display_name": "候选三",
                "latitude": 39.3,
                "longitude": 116.3,
                "adcode": "110101",
                "source": "amap_candidate",
                "confidence": 0.7,
            },
        ]
    )

    top = _resolve_pending_navigation_clarification_selection("选上面的", [pending])
    middle = _resolve_pending_navigation_clarification_selection("选中间的", [pending])
    bottom = _resolve_pending_navigation_clarification_selection("选下面的", [pending])

    assert top is not None and top["candidate"]["name"] == "候选一"
    assert middle is not None and middle["candidate"]["name"] == "候选二"
    assert bottom is not None and bottom["candidate"]["name"] == "候选三"


@pytest.mark.asyncio
async def test_navigation_clarification_selection_out_of_range_keeps_clarifying() -> None:
    pending = _pending_navigation_clarification_history()
    selection = _resolve_pending_navigation_clarification_selection("选第三个", [pending])
    assert selection is not None
    assert selection["selection_error"] == "selection_index_out_of_range"

    slot_result, _ = await _resolve_navigation_slots(
        "选第三个",
        attraction=None,
        session_context={"navigation_clarification_selection": selection},
    )
    context = await get_navigation_context(slot_result=NavigationSlotPayload(**slot_result.model_dump()))
    answer = format_navigation_text_answer(
        context.origin_name,
        context.destination_name,
        context.steps,
        context.distance_meters,
        context.duration_seconds,
        clarification=context.clarification,
    )

    assert context.status == "clarification"
    assert context.reason == "clarification_selection_error"
    assert "当前只有 2 个候选，没有第 3 个" in answer


@pytest.mark.asyncio
async def test_navigation_clarification_even_middle_selection_keeps_clarifying() -> None:
    pending = _pending_navigation_clarification_history()
    selection = _resolve_pending_navigation_clarification_selection("选中间的", [pending])
    assert selection is not None
    assert selection["selection_error"] == "ambiguous_middle_selection"

    slot_result, _ = await _resolve_navigation_slots(
        "选中间的",
        attraction=None,
        session_context={"navigation_clarification_selection": selection},
    )
    context = await get_navigation_context(slot_result=NavigationSlotPayload(**slot_result.model_dump()))
    answer = format_navigation_text_answer(
        context.origin_name,
        context.destination_name,
        context.steps,
        context.distance_meters,
        context.duration_seconds,
        clarification=context.clarification,
    )

    assert context.status == "clarification"
    assert "中间有两个候选" in answer


@pytest.mark.asyncio
async def test_navigation_clarification_fallback_selection_rehydrates_candidate() -> None:
    pending = _pending_navigation_clarification_history()["metadata"]["navigation"]["clarification"]
    fallback_result = IntentRouterFallbackResult(
        intent="navigation_text",
        confidence=0.86,
        clarification_action="selected",
        selected_index=2,
        reason="用户说的是餐厅那个",
    )

    selection = _navigation_clarification_selection_from_fallback(fallback_result, pending)
    assert selection is not None

    slot_result, debug = await _resolve_navigation_slots(
        "我说的是那个吃饭的地方，不是景点",
        attraction=None,
        session_context={"navigation_clarification_selection": selection},
    )

    assert debug["source"] == "clarification_selection"
    assert slot_result.destinations == ["正阳门餐厅"]
    assert slot_result.destination_places[0].source == "amap_candidate"


@pytest.mark.asyncio
async def test_navigation_clarification_fallback_low_confidence_keeps_clarifying() -> None:
    pending = _pending_navigation_clarification_history()["metadata"]["navigation"]["clarification"]
    fallback_result = IntentRouterFallbackResult(
        intent="navigation_text",
        confidence=0.62,
        clarification_action="selected",
        selected_index=2,
        reason="低置信选择",
    )

    selection = _navigation_clarification_selection_from_fallback(fallback_result, pending)
    assert selection is not None
    assert selection["selection_error"] == "clarification_fallback_needs_clarification"
    slot_result, _ = await _resolve_navigation_slots(
        "可能是餐厅那个",
        attraction=None,
        session_context={"navigation_clarification_selection": selection},
    )
    context = await get_navigation_context(slot_result=NavigationSlotPayload(**slot_result.model_dump()))
    answer = format_navigation_text_answer(
        context.origin_name,
        context.destination_name,
        context.steps,
        context.distance_meters,
        context.duration_seconds,
        clarification=context.clarification,
    )

    assert context.status == "clarification"
    assert "我还不能确定你要选哪一个地点" in answer


def test_pending_clarification_fallback_does_not_override_strong_new_weather_intent() -> None:
    pending = _pending_navigation_clarification_history()["metadata"]["navigation"]["clarification"]

    assert _should_try_pending_clarification_fallback(
        pending,
        None,
        {"intent": "smalltalk", "confidence": 0.4, "needs_fallback": False},
    )
    assert not _should_try_pending_clarification_fallback(
        pending,
        None,
        {"intent": "weather_info", "confidence": 0.92, "needs_fallback": False},
    )


def _pending_navigation_clarification_history(candidates=None) -> dict:
    return {
        "role": "assistant",
        "intent": "navigation_text",
        "metadata": {
            "navigation": {
                "status": "clarification",
                "clarification": {
                    "raw_text": "正阳门餐厅",
                    "target_role": "destination",
                    "target_index": 0,
                    "reason": "commercial_or_address_ambiguity",
                    "slot_result": {
                        "origin": "Tiananmen Square",
                        "destinations": ["正阳门餐厅"],
                        "mode": "walking",
                        "mode_source": "distance_default",
                        "source": "rule",
                        "request_kind": "destination_only",
                    },
                    "candidates": candidates or [
                        {
                            "index": 1,
                            "name": "正阳门",
                            "display_name": "正阳门",
                            "latitude": 39.8994,
                            "longitude": 116.3977,
                            "adcode": "110101",
                            "source": "registry",
                            "confidence": 0.9,
                        },
                        {
                            "index": 2,
                            "name": "正阳门餐厅",
                            "display_name": "正阳门餐厅",
                            "latitude": 39.899,
                            "longitude": 116.398,
                            "adcode": "110101",
                            "source": "amap_candidate",
                            "confidence": 0.7,
                        },
                    ],
                },
            }
        },
    }


@pytest.mark.asyncio
async def test_navigation_slot_extraction_supports_destination_only_multi_leg() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "去故宫再去景山怎么走？",
        attraction=None,
        session_context={"current_stop_name": "Tiananmen Square", "next_stop_name": "Forbidden City"},
    )

    assert slot_result.request_kind == "multi_leg"
    assert slot_result.origin == "Tiananmen Square"
    assert slot_result.destinations == ["Forbidden City", "Jingshan Park"]
    assert slot_result.source == "rule"


@pytest.mark.asyncio
async def test_navigation_slot_extraction_supports_explicit_route_without_polluting_origin() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "从天安门怎么走到故宫？",
        attraction=None,
        session_context={"current_stop_name": None, "next_stop_name": None},
    )

    assert slot_result.request_kind == "explicit_route"
    assert slot_result.origin == "Tiananmen Square"
    assert slot_result.destinations == ["Forbidden City"]
    assert slot_result.source == "rule"


@pytest.mark.asyncio
async def test_navigation_slot_extraction_prefers_gps_origin_for_destination_only() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "到天坛怎么走？",
        attraction=None,
        session_context={
            "current_stop_name": "Tiananmen Square",
            "current_position": {"latitude": 39.905, "longitude": 116.3976},
        },
    )

    assert slot_result.request_kind == "destination_only"
    assert slot_result.origin == "当前位置"
    assert slot_result.origin_place is not None
    assert slot_result.origin_place.place_id == "gps_current_position"
    assert slot_result.destinations == ["Temple of Heaven"]
    assert slot_result.destination_places[0].place_id == "temple_of_heaven"


@pytest.mark.asyncio
async def test_navigation_slot_extraction_supports_current_location_explicit_route() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "从这里到故宫怎么走？",
        attraction=None,
        session_context={"current_position": {"latitude": 39.905, "longitude": 116.3976}},
    )

    assert slot_result.request_kind == "explicit_route"
    assert slot_result.origin == "当前位置"
    assert slot_result.origin_place is not None
    assert slot_result.origin_place.source == "gps"
    assert slot_result.destinations == ["Forbidden City"]


@pytest.mark.asyncio
async def test_navigation_slot_defaults_to_transit_for_long_distance() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "到颐和园怎么走？",
        attraction=None,
        session_context={"current_stop_name": "Forbidden City"},
    )

    assert slot_result.destinations == ["Summer Palace"]
    assert slot_result.mode == "transit"
    assert slot_result.mode_source == "distance_default"


@pytest.mark.asyncio
async def test_navigation_slot_defaults_to_walking_for_short_distance() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "到景山怎么走？",
        attraction=None,
        session_context={"current_stop_name": "Forbidden City"},
    )

    assert slot_result.destinations == ["Jingshan Park"]
    assert slot_result.mode == "walking"
    assert slot_result.mode_source == "distance_default"


@pytest.mark.asyncio
async def test_navigation_slot_explicit_walking_overrides_distance_default() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "从故宫到颐和园步行怎么走？",
        attraction=None,
        session_context={},
    )

    assert slot_result.destinations == ["Summer Palace"]
    assert slot_result.mode == "walking"
    assert slot_result.mode_source == "explicit"


@pytest.mark.asyncio
async def test_navigation_slot_explicit_transit_mode_is_preserved() -> None:
    slot_result, _ = await _resolve_navigation_slots(
        "从故宫到颐和园坐地铁怎么走？",
        attraction=None,
        session_context={},
    )

    assert slot_result.destinations == ["Summer Palace"]
    assert slot_result.mode == "transit"
    assert slot_result.mode_source == "explicit"
    assert slot_result.transit_preference == "subway"


@pytest.mark.asyncio
async def test_navigation_slot_distinguishes_bus_and_public_transport() -> None:
    bus_result, _ = await _resolve_navigation_slots(
        "从故宫到颐和园坐公交怎么走？",
        attraction=None,
        session_context={},
    )
    public_transport_result, _ = await _resolve_navigation_slots(
        "从故宫到颐和园公共交通怎么走？",
        attraction=None,
        session_context={},
    )

    assert bus_result.mode == "transit"
    assert bus_result.transit_preference == "bus"
    assert public_transport_result.mode == "transit"
    assert public_transport_result.transit_preference == "public_transport"

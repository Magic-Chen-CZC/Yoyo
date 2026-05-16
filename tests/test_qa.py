# test_qa.py 是 QA 模块最重要的行为测试之一。
# 它覆盖了 QA 支持的几条主要路径，适合当成“QA 能做什么”的说明书来看。
from httpx import AsyncClient
import pytest

from yoyo.db.models.itinerary import Itinerary, ItineraryVersion
from yoyo.db.models.session import GuideSession
from yoyo.modules.knowledge.hybrid_context_builder import build_hybrid_context
from yoyo.modules.knowledge.schemas import RAGChunk, RAGContext, WeatherContext
from yoyo.modules.qa.schemas import IntentRouterFallbackResult
from yoyo.modules.shared.enums import GuidePlaybackState, GuideSessionStatus, ItineraryStatus, ItineraryVersionStatus
from yoyo.modules.translator.schemas import TranslatorResult


async def _preprocess_to_zh(text: str, source_language: str = "en") -> TranslatorResult:
    return TranslatorResult(
        text=text,
        status="ok",
        reason=None,
        source_language=source_language,
        target_language="zh",
        mode="routing_preprocess",
        degraded=False,
        execution_path="llm_structured",
    )


def _default_pivot_text(query: str) -> str | None:
    mappings = {
        "Write me a sorting algorithm": "给我写个排序算法",
        "Please translate: 请帮我拍张照片": "请翻译：请帮我拍张照片",
        "Please translate this Beijing phrase": "请把这句北京旅行短语翻译成中文",
        "What are today's opening hours in Beijing?": "北京今天的开放时间是什么？",
        "Translate this for local staff: where is the restroom?": "请翻译给当地工作人员看：where is the restroom?",
        "What is my next route stop in Beijing itinerary?": "我下一站要去哪里？",
        "Tell me about this Beijing attraction": "讲讲这个北京景点",
        "What is my current route stop in Beijing itinerary now?": "接下来去哪？",
        "Can you change route and remove the next stop?": "把下一站删掉，改路线。",
        "Tell me a deeper history and background story of this Beijing attraction": "讲讲这个北京景点更深入的历史背景。",
        "How do I get to the Forbidden City?": "去故宫怎么走？",
        "How do I get from Tiananmen to the Forbidden City and then Jingshan Park?": "从天安门到故宫再到景山怎么走？",
    }
    return mappings.get(query)


@pytest.fixture(autouse=True)
def _patch_default_preprocess_query(monkeypatch) -> None:
    async def fake_preprocess_query(*, query: str, source_language: str, **kwargs) -> TranslatorResult:
        pivot = _default_pivot_text(query)
        if pivot is None:
            return TranslatorResult(
                text=query,
                status="degraded",
                reason="test_default_no_mapping",
                source_language=source_language,
                target_language="zh",
                mode="routing_preprocess",
                degraded=True,
                execution_path="test_stub",
            )
        return await _preprocess_to_zh(pivot, source_language)

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)


async def _patch_planner_job_pool(monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)


@pytest.mark.asyncio
async def test_qa_smalltalk_greeting_returns_supported_answer(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "你好", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "smalltalk"
    assert "你好" in body["data"]["answer"] or "我在" in body["data"]["answer"]
    assert body["data"]["metadata"]["latency_ms"]["generation_ms"] == 0
    assert body["data"]["metadata"]["latency_ms"]["context_build_ms"] == 0


@pytest.mark.asyncio
async def test_qa_out_of_scope(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Write me a sorting algorithm", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is False
    assert body["data"]["intent"] == "out_of_scope"
    assert "北京旅游相关问题" in body["data"]["answer"]
    assert body["data"]["metadata"]["latency_ms"]["generation_ms"] == 0
    assert body["data"]["metadata"]["latency_ms"]["postprocess_ms"] == 0


@pytest.mark.asyncio
async def test_qa_router_fallback_keeps_deep_forbidden_city_explanation_in_attraction_explain(client: AsyncClient, monkeypatch) -> None:
    async def fake_preprocess_query(*, query: str, source_language: str, **kwargs) -> TranslatorResult:
        if query == "Please unpack the Forbidden City’s sequence of gates, courtyards, and axial planning as a system of political theater, not just architecture.":
            return await _preprocess_to_zh("请把紫禁城的大门、庭院和轴线规划当作一种政治戏剧系统来拆解，而不只是建筑。", source_language)
        return await _preprocess_to_zh(query, source_language)

    async def fake_resolve_router_fallback(**kwargs):
        return IntentRouterFallbackResult(
            intent="attraction_explain",
            confidence=0.93,
            reason="deep_explain_of_beijing_attraction",
        ), {"llm": {"provider": "openrouter", "model": "openai/gpt-5.4-nano", "latency_ms": 12, "structured_output_valid": True}}

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fake_resolve_router_fallback)

    class EmptyRag:
        chunks = []
        retrieval_mode = "not_used"
        fallback_used = False

        def model_dump(self) -> dict[str, object]:
            return {"chunks": [], "retrieval_mode": "not_used", "fallback_used": False}

    class HybridContextStub:
        attraction = None
        profile = None
        live_info = None
        weather = None
        navigation = None
        rag = EmptyRag()
        session_context = {}
        dialogue_history = []
        prompt_safe_attraction = {}
        prompt_safe_profile = {}

        def model_dump(self) -> dict[str, object]:
            return {
                "attraction": None,
                "profile": None,
                "live_info": None,
                "rag": self.rag.model_dump(),
                "session_context": {},
                "dialogue_history": [],
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
            }

    async def fake_build_hybrid_context(**kwargs):
        return HybridContextStub()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"The Forbidden City uses gates, courts, and axis planning to stage imperial order.","status":"ok","reason":null,"grounding":"limited","includes_history":true,"includes_tips":false}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "Please unpack the Forbidden City’s sequence of gates, courtyards, and axial planning as a system of political theater, not just architecture.",
            "language": "en",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "attraction_explain"
    fallback_result = body["data"]["metadata"]["intent_router"]["fallback_result"]
    if fallback_result is not None:
        assert fallback_result["intent"] == "attraction_explain"


@pytest.mark.asyncio
async def test_qa_smalltalk_with_extra_content_uses_router_fallback(client: AsyncClient, monkeypatch) -> None:
    captured = {}

    async def fake_resolve_router_fallback(**kwargs):
        captured.update(kwargs)
        return IntentRouterFallbackResult(intent="smalltalk", confidence=0.91, reason="friendly_greeting_with_extra_content"), {
            "llm": {"provider": "openrouter", "model": "openai/gpt-5.4-nano", "latency_ms": 12, "structured_output_valid": True}
        }

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fake_resolve_router_fallback)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "你好，请帮我介绍一下北京", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "smalltalk"
    assert body["data"]["metadata"]["intent_router"]["rule_result"]["needs_fallback"] is True
    assert body["data"]["metadata"]["intent_router"]["fallback_result"]["intent"] == "smalltalk"
    assert captured["raw_query"] == "你好，请帮我介绍一下北京"
    assert body["data"]["metadata"]["latency_ms"]["generation_ms"] == 0


@pytest.mark.asyncio
async def test_qa_weather_info_returns_supported_answer(client: AsyncClient, monkeypatch) -> None:
    class FakeWeatherContext:
        location_name = "故宫"
        weather = "晴"
        temperature_celsius = "25"
        wind_direction = "东北"
        wind_power = "3"
        humidity = "40"
        report_time = "2026-05-09 10:00:00"
        status = "available"
        reason = None

        def model_dump(self):
            return {
                "location_name": self.location_name,
                "weather": self.weather,
                "temperature_celsius": self.temperature_celsius,
                "wind_direction": self.wind_direction,
                "wind_power": self.wind_power,
                "humidity": self.humidity,
                "report_time": self.report_time,
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": FakeWeatherContext(),
                "navigation": None,
                "rag": None,
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
                "session_context": {},
                "dialogue_history": [],
                "model_dump": lambda self: {"weather": FakeWeatherContext().model_dump()},
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "北京今天会不会下雨？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "weather_info"
    assert body["data"]["metadata"]["degraded"] is False
    assert body["data"]["metadata"]["weather"]["weather"] == "晴"


@pytest.mark.asyncio
async def test_weather_target_uses_rule_then_fallback_then_default_city(monkeypatch) -> None:
    captured: list[str | None] = []

    async def fake_get_weather_context(location_name: str | None):
        captured.append(location_name)
        return WeatherContext(
            location_name=location_name,
            weather="晴",
            temperature_celsius="25",
            status="available",
            reason=None,
        )

    monkeypatch.setattr("yoyo.modules.knowledge.hybrid_context_builder.get_weather_context", fake_get_weather_context)

    rule_hybrid = await build_hybrid_context(
        intent="weather_info",
        query="故宫现在天气怎么样？",
        attraction_name="Forbidden City",
        user_id=None,
        session_context={"city_code": "beijing"},
        dialogue_history=[],
        session=None,
    )

    fallback_hybrid = await build_hybrid_context(
        intent="weather_info",
        query="北京今天会不会下雨？",
        attraction_name=None,
        user_id=None,
        session_context={"city_code": "beijing", "weather_location_name": "北京"},
        dialogue_history=[],
        session=None,
    )

    default_hybrid = await build_hybrid_context(
        intent="weather_info",
        query="今天会不会下雨？",
        attraction_name=None,
        user_id=None,
        session_context={"city_code": "beijing"},
        dialogue_history=[],
        session=None,
    )

    assert captured == ["Forbidden City", "北京", "Beijing"]
    rule_debug = rule_hybrid.build_debug["timings_ms"]
    fallback_debug = fallback_hybrid.build_debug["timings_ms"]
    default_debug = default_hybrid.build_debug["timings_ms"]
    assert rule_debug["weather_target_source"] == "rule"
    assert rule_debug["weather_target_location_name"] == "Forbidden City"
    assert fallback_debug["weather_target_source"] == "fallback"
    assert fallback_debug["weather_target_location_name"] == "北京"
    assert fallback_debug["weather_target_fallback_ms"] == 0
    assert isinstance(fallback_debug["weather_lookup_ms"], int)
    assert default_debug["weather_target_source"] == "default_city"
    assert default_debug["weather_target_location_name"] == "Beijing"
    assert isinstance(default_debug["weather_target_resolution_ms"], int)


@pytest.mark.asyncio
async def test_weather_queries_use_single_router_fallback_for_intent_and_location_when_rule_marks_fallback(client: AsyncClient, monkeypatch) -> None:
    calls = {"router": 0, "weather": 0}

    async def fake_resolve_router_fallback(**kwargs):
        calls["router"] += 1
        return IntentRouterFallbackResult(intent="weather_info", confidence=0.93, reason="weather_detected", weather_location_name="北京"), {
            "llm": {"provider": "dashscope", "model": "qwen-flash", "structured_output_valid": True}
        }

    async def fake_get_weather(self, location_name: str | None):
        calls["weather"] += 1
        assert location_name == "北京"
        return {
            "location_name": "北京市",
            "weather": "晴",
            "temperature_celsius": "25",
            "wind_direction": "东北",
            "wind_power": "3",
            "humidity": "40",
            "report_time": "2026-05-09 10:00:00",
            "status": "available",
            "reason": None,
            "source": "amap",
        }

    async def fail_weather_slot_fallback(**kwargs):
        raise AssertionError("weather slot fallback should not run after router fallback returns location")

    def fake_score_intent(*args, **kwargs):
        return {
            "intent": "live_info",
            "confidence": 0.52,
            "margin": 0.04,
            "needs_fallback": True,
            "fallback_reason": "live_vs_weather_conflict",
            "signals": ["same_day_signal"],
            "candidates": {"live_info": 0.52, "weather_info": 0.48},
            "runner_up_intent": "weather_info",
            "last_intent": None,
            "boundary_topic": None,
            "out_of_scope_subtype": None,
        }

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.score_intent", fake_score_intent)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fake_resolve_router_fallback)
    monkeypatch.setattr("yoyo.modules.integrations.amap.client.AmapRouteClient.get_weather", fake_get_weather)
    monkeypatch.setattr("yoyo.modules.qa.router_fallback.resolve_weather_slot_fallback", fail_weather_slot_fallback)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "北京今天什么情况？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["intent"] == "weather_info"
    assert body["metadata"]["intent_router"]["rule_result"]["needs_fallback"] is True
    assert body["metadata"]["intent_router"]["fallback_result"]["weather_location_name"] == "北京"
    assert body["metadata"]["latency_ms"]["context_build_breakdown_ms"]["weather_target_source"] == "fallback"
    assert calls == {"router": 1, "weather": 1}


@pytest.mark.asyncio
async def test_qa_weather_info_defaults_to_itinerary_city_when_query_has_no_location(client: AsyncClient, db_session, monkeypatch) -> None:
    itinerary = Itinerary(user_id="weather-user", city_code="beijing", title="Weather trip", status=ItineraryStatus.ACTIVE)
    db_session.add(itinerary)
    await db_session.flush()

    version = ItineraryVersion(
        itinerary_id=itinerary.id,
        version_no=1,
        planner_input_json={},
        plan_json={"summary": "Weather summary", "stops": []},
        status=ItineraryVersionStatus.DRAFT,
        created_by="test",
    )
    db_session.add(version)
    await db_session.flush()

    guide_session = GuideSession(
        itinerary_id=itinerary.id,
        itinerary_version_id=version.id,
        status=GuideSessionStatus.PENDING,
        playback_state=GuidePlaybackState.NOT_TRIGGERED,
        context_json={},
    )
    db_session.add(guide_session)
    await db_session.commit()

    async def fake_get_weather(self, location_name: str | None):
        assert location_name == "Beijing"
        return {
            "location_name": "北京市",
            "weather": "晴",
            "temperature_celsius": "25",
            "wind_direction": "东北",
            "wind_power": "3",
            "humidity": "40",
            "report_time": "2026-05-09 10:00:00",
            "status": "available",
            "reason": None,
            "source": "amap",
        }

    async def fake_resolve_router_fallback(**kwargs):
        return IntentRouterFallbackResult(intent="weather_info", confidence=0.91, reason="weather_without_location", weather_location_name=None), {
            "llm": {"provider": "dashscope", "model": "qwen-flash", "structured_output_valid": True}
        }

    monkeypatch.setattr("yoyo.modules.integrations.amap.client.AmapRouteClient.get_weather", fake_get_weather)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fake_resolve_router_fallback)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "今天会不会下雨？", "language": "zh", "guide_session_id": guide_session.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "weather_info"
    assert body["data"]["metadata"]["degraded"] is False
    assert body["data"]["metadata"]["weather"]["location_name"] == "北京市"
    assert body["data"]["metadata"]["resolved_query"]["user_language"] == "zh"


@pytest.mark.asyncio
async def test_qa_traffic_boundary_returns_specific_redirect(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "今天去故宫的交通会不会很堵？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is False
    assert body["data"]["intent"] == "out_of_scope"
    assert body["data"]["metadata"]["boundary_redirect"] is True
    assert body["data"]["metadata"]["boundary_topic"] == "traffic"
    assert body["data"]["metadata"]["out_of_scope_subtype"] == "traffic_boundary"
    assert "实时服务" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_qa_navigation_text_returns_supported_answer(client: AsyncClient, monkeypatch) -> None:
    class FakeNavigationContext:
        origin_name = "天安门"
        destination_name = "故宫"
        distance_meters = 1064
        duration_seconds = 851
        steps = [
            type("Step", (), {"instruction": "向北步行566米直行"})(),
            type("Step", (), {"instruction": "向西步行30米向右前方行走"})(),
        ]
        legs = []
        status = "available"
        reason = None

        def model_dump(self):
            return {
                "origin_name": self.origin_name,
                "destination_name": self.destination_name,
                "distance_meters": self.distance_meters,
                "duration_seconds": self.duration_seconds,
                "steps": [{"instruction": "向北步行566米直行"}, {"instruction": "向西步行30米向右前方行走"}],
                "legs": [],
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": None,
                "navigation": FakeNavigationContext(),
                "rag": None,
                "model_dump": lambda self: {"navigation": FakeNavigationContext().model_dump()},
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "从天安门怎么走到故宫？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "navigation_text"
    assert body["data"]["metadata"]["degraded"] is False
    assert body["data"]["metadata"]["navigation"]["origin_name"] == "天安门"
    assert "1." in body["data"]["answer"]


@pytest.mark.asyncio
async def test_qa_navigation_text_treats_cjk_query_as_zh_when_request_uses_default_en(client: AsyncClient, monkeypatch) -> None:
    class FakeNavigationContext:
        origin_name = "北京市东城区天安门"
        destination_name = "故宫"
        distance_meters = 1064
        duration_seconds = 851
        steps = [
            type("Step", (), {"instruction": "向北步行566米直行"})(),
            type("Step", (), {"instruction": "向北步行24米左转"})(),
        ]
        legs = []
        status = "available"
        reason = None

        def model_dump(self):
            return {
                "origin_name": self.origin_name,
                "destination_name": self.destination_name,
                "distance_meters": self.distance_meters,
                "duration_seconds": self.duration_seconds,
                "steps": [{"instruction": "向北步行566米直行"}, {"instruction": "向北步行24米左转"}],
                "legs": [],
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": None,
                "navigation": FakeNavigationContext(),
                "rag": None,
                "model_dump": lambda self: {"navigation": FakeNavigationContext().model_dump()},
            },
        )()

    async def fail_if_called(**kwargs):
        raise AssertionError("translate_answer should not run for CJK navigation queries")

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.translate_answer", fail_if_called)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "从天安门怎么走到故宫？"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "navigation_text"
    assert body["data"]["answer"].startswith("从 北京市东城区天安门 到 故宫")
    assert body["data"]["metadata"]["resolved_query"]["user_language"] == "zh"
    assert body["data"]["metadata"]["resolved_query"]["used_translation_pivot"] is False
    assert body["data"]["metadata"]["answer_translation"]["used_answer_translation"] is False


@pytest.mark.asyncio
async def test_qa_navigation_text_returns_degraded_answer_when_endpoint_missing(client: AsyncClient, monkeypatch) -> None:
    class FakeNavigationContext:
        origin_name = "天安门"
        destination_name = None
        distance_meters = None
        duration_seconds = None
        steps = []
        legs = []
        status = "degraded"
        reason = "missing_origin_or_destination"

        def model_dump(self):
            return {
                "origin_name": self.origin_name,
                "destination_name": self.destination_name,
                "distance_meters": self.distance_meters,
                "duration_seconds": self.duration_seconds,
                "steps": [],
                "legs": [],
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": None,
                "navigation": FakeNavigationContext(),
                "rag": None,
                "model_dump": lambda self: {"navigation": FakeNavigationContext().model_dump()},
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "怎么走？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "navigation_text"
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["metadata"]["degraded_reason"] == "missing_origin_or_destination"
    assert "出发点和目的地" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_qa_navigation_text_supports_multi_leg_answer(client: AsyncClient, monkeypatch) -> None:
    class FakeNavigationContext:
        origin_name = "天安门"
        destination_name = "Jingshan Park"
        distance_meters = 1800
        duration_seconds = 1500
        steps = [
            type("Step", (), {"instruction": "向北步行到故宫"})(),
            type("Step", (), {"instruction": "继续向北步行到景山公园"})(),
        ]
        legs = [
            type(
                "Leg",
                (),
                {
                    "origin_name": "天安门",
                    "destination_name": "Forbidden City",
                    "steps": [type("Step", (), {"instruction": "向北步行到故宫"})()],
                },
            )(),
            type(
                "Leg",
                (),
                {
                    "origin_name": "Forbidden City",
                    "destination_name": "Jingshan Park",
                    "steps": [type("Step", (), {"instruction": "继续向北步行到景山公园"})()],
                },
            )(),
        ]
        status = "available"
        reason = None

        def model_dump(self):
            return {
                "origin_name": self.origin_name,
                "destination_name": self.destination_name,
                "distance_meters": self.distance_meters,
                "duration_seconds": self.duration_seconds,
                "steps": [
                    {"instruction": "向北步行到故宫"},
                    {"instruction": "继续向北步行到景山公园"},
                ],
                "legs": [
                    {
                        "origin_name": "天安门",
                        "destination_name": "Forbidden City",
                        "steps": [{"instruction": "向北步行到故宫"}],
                    },
                    {
                        "origin_name": "Forbidden City",
                        "destination_name": "Jingshan Park",
                        "steps": [{"instruction": "继续向北步行到景山公园"}],
                    },
                ],
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": None,
                "navigation": FakeNavigationContext(),
                "rag": None,
                "model_dump": lambda self: {"navigation": FakeNavigationContext().model_dump()},
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "从天安门到故宫再到景山怎么走？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "navigation_text"
    assert "第 1 段：" in body["data"]["answer"]
    assert "第 2 段：" in body["data"]["answer"]
    assert len(body["data"]["metadata"]["navigation"]["legs"]) == 2


@pytest.mark.asyncio
async def test_qa_request_level_llm_override_is_forwarded_to_generator(client: AsyncClient, monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_generate_qa_answer(*, provider: str, model: str, **kwargs):
        captured["provider"] = provider
        captured["model"] = model
        return "这是一个测试回答。", {"llm": {"provider": provider, "model": model, "usage": {}, "structured_output_valid": True}}

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": None,
                "navigation": None,
                "rag": None,
                "model_dump": lambda self: {},
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.generate_qa_answer", fake_generate_qa_answer)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "给我简短介绍一下故宫。",
            "language": "zh",
            "llm_provider": "volcengine",
            "llm_model": "doubao-seed-2-0-mini-260428",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert captured["provider"] == "volcengine"
    assert captured["model"] == "doubao-seed-2-0-mini-260428"
    assert body["data"]["metadata"]["requested_llm_provider"] == "volcengine"
    assert body["data"]["metadata"]["requested_llm_model"] == "doubao-seed-2-0-mini-260428"


@pytest.mark.asyncio
async def test_qa_default_llm_settings_are_forwarded_to_generator(client: AsyncClient, monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_generate_qa_answer(*, provider: str, model: str, **kwargs):
        captured["provider"] = provider
        captured["model"] = model
        return "这是一个测试回答。", {"llm": {"provider": provider, "model": model, "usage": {}, "structured_output_valid": True}}

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": None,
                "navigation": None,
                "rag": None,
                "model_dump": lambda self: {},
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.generate_qa_answer", fake_generate_qa_answer)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "xfyun_its",
                "translator_model": "its",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "给我简短介绍一下故宫。",
            "language": "zh",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert captured["provider"] == "volcengine"
    assert captured["model"] == "doubao-seed-2-0-mini-260428"
    assert body["data"]["metadata"]["requested_llm_provider"] is None
    assert body["data"]["metadata"]["requested_llm_model"] is None
    assert body["data"]["metadata"]["llm"]["provider"] == "volcengine"
    assert body["data"]["metadata"]["llm"]["model"] == "doubao-seed-2-0-mini-260428"


@pytest.mark.asyncio
async def test_translation_structured_output_is_parsed_when_valid(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"请帮我拍张照片。","status":"ok","reason":null,"mode":"direct_translation"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "openrouter",
                "translator_model": "demo-translator",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate: 请帮我拍张照片", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["answer"] == "请帮我拍张照片。"
    assert body["data"]["metadata"]["structured"]["mode"] == "direct_translation"
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_qa_translation_intent_returns_explicit_degraded_response(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = type("Error", (), {"model_dump": lambda self: {"error_type": "provider_error", "message": "boom", "retryable": False}})()

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "openrouter",
                "translator_model": "demo-translator",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate this Beijing phrase", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "translation"
    assert "translate_text" in body["data"]["used_skills"]
    assert "guided mode" not in body["data"]["answer"]
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["metadata"]["degraded_reason"] == "runtime_translation_unavailable"
    assert body["data"]["answer"] == "我现在还不能稳定确认翻译内容，请把你要翻译的原句直接发给我。"


@pytest.mark.asyncio
async def test_translation_structured_output_with_wrapper_noise_falls_back(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"Answer: 请帮我拍张照片。","status":"ok","reason":null,"mode":"direct_translation"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "openrouter",
                "translator_model": "demo-translator",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate: 请帮我拍张照片", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "translation"
    assert body["data"]["metadata"]["llm"]["structured_output_valid"] is False
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["answer"] == "我现在还不能稳定确认这句话的翻译，请把要翻译的原句再完整发我一次，我会直接帮你翻。"


@pytest.mark.asyncio
async def test_trip_assistant_current_stop_status_query_uses_session_context(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-current-stop-status",
            "title": "QA current stop status",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "zh"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "我现在到哪一站了？",
            "language": "zh",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "trip_assistant"
    assert body["data"]["metadata"]["status"] == "ok"
    assert body["data"]["metadata"]["route_focus"] == "current_stop"
    assert body["data"]["metadata"]["references_current_stop"] is True
    assert body["data"]["metadata"]["degraded"] is False
    assert "Tiananmen Square" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_trip_assistant_structured_output_normalizes_string_bools_and_missing_reason(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"You are currently at Tiananmen Square. Your next stop is Forbidden City.","status":" ok ","route_focus":" next_stop ","references_current_stop":"true","references_next_stop":"false"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-trip-normalized",
            "title": "QA trip normalized",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "trip_assistant"
    assert body["data"]["metadata"]["structured"]["route_focus"] == "next_stop"
    assert body["data"]["metadata"]["references_current_stop"] is True
    assert body["data"]["metadata"]["references_next_stop"] is False
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_live_info_structured_output_is_parsed_when_valid(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"Please verify today\'s opening hours before you go.","status":"degraded","reason":"same_day_verification_needed","not_confirmed":true,"confidence":"medium"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="北京今天的开放时间是什么？",
            status="ok",
            reason=None,
            source_language="en",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="llm_structured",
        )

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "What are today's opening hours in Beijing?", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "live_info"
    assert body["data"]["metadata"]["structured"]["status"] == "degraded"
    assert body["data"]["metadata"]["confidence"] == "medium"
    assert body["data"]["metadata"]["degraded"] is True


@pytest.mark.asyncio
async def test_qa_live_info_includes_sources(client: AsyncClient, monkeypatch) -> None:
    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="北京今天的开放时间是什么？",
            status="ok",
            reason=None,
            source_language="en",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="llm_structured",
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "What are today's opening hours in Beijing?", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "live_info"
    assert len(body["data"]["metadata"]["sources"]) >= 1
    assert "updated_at" in body["data"]["metadata"]
    assert "confidence" in body["data"]["metadata"]
    assert "status" in body["data"]["metadata"]
    assert "reason" in body["data"]["metadata"]


@pytest.mark.asyncio
async def test_qa_temperature_question_routes_to_weather_info(client: AsyncClient, monkeypatch) -> None:
    class FakeWeatherContext:
        location_name = "北京"
        weather = "晴"
        temperature_celsius = "25"
        wind_direction = "东北"
        wind_power = "3"
        humidity = "40"
        report_time = "2026-05-09 10:00:00"
        status = "available"
        reason = None

        def model_dump(self):
            return {
                "location_name": self.location_name,
                "weather": self.weather,
                "temperature_celsius": self.temperature_celsius,
                "wind_direction": self.wind_direction,
                "wind_power": self.wind_power,
                "humidity": self.humidity,
                "report_time": self.report_time,
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": FakeWeatherContext(),
                "navigation": None,
                "rag": None,
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
                "session_context": {},
                "dialogue_history": [],
                "model_dump": lambda self: {"weather": FakeWeatherContext().model_dump()},
            },
        )()

    async def fake_generate_qa_answer(*, intent: str, **kwargs):
        assert intent == "weather_info"
        return "北京今天约25度。", {
            "llm": {
                "provider": "volcengine",
                "model": "doubao-seed-2-0-mini-260428",
                "latency_ms": 123,
                "usage": {},
                "prompt_version": "qa-zh-v4-weather_info",
                "fallback_used": False,
                "error": None,
                "structured_output_valid": True,
                "structured_output": {"answer": "北京今天约25度。", "status": "ok", "reason": None},
            }
        }

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.generate_qa_answer", fake_generate_qa_answer)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "北京今天大概多少度？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "weather_info"
    assert body["data"]["answer"] == "北京今天约25度。"
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_qa_weather_info_uses_llm_when_weather_available(client: AsyncClient, monkeypatch) -> None:
    class FakeWeatherContext:
        location_name = "北京市"
        weather = "晴"
        temperature_celsius = "25"
        wind_direction = "东北"
        wind_power = "3"
        humidity = "40"
        report_time = "2026-05-09 10:00:00"
        status = "available"
        reason = None

        def model_dump(self):
            return {
                "location_name": self.location_name,
                "weather": self.weather,
                "temperature_celsius": self.temperature_celsius,
                "wind_direction": self.wind_direction,
                "wind_power": self.wind_power,
                "humidity": self.humidity,
                "report_time": self.report_time,
                "status": self.status,
                "reason": self.reason,
            }

    async def fake_build_hybrid_context(**kwargs):
        return type(
            "Hybrid",
            (),
            {
                "profile": None,
                "attraction": None,
                "live_info": None,
                "weather": FakeWeatherContext(),
                "navigation": None,
                "rag": None,
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
                "session_context": {},
                "dialogue_history": [],
                "model_dump": lambda self: {"weather": FakeWeatherContext().model_dump()},
            },
        )()

    async def fake_generate_qa_answer(*, intent: str, **kwargs):
        assert intent == "weather_info"
        return "北京今天晴，约25度，暂时看起来没有下雨信号。", {
            "llm": {
                "provider": "volcengine",
                "model": "doubao-seed-2-0-mini-260428",
                "latency_ms": 321,
                "usage": {},
                "prompt_version": "qa-zh-v4-weather_info",
                "fallback_used": False,
                "error": None,
                "structured_output_valid": True,
                "structured_output": {"answer": "北京今天晴，约25度，暂时看起来没有下雨信号。", "status": "ok", "reason": None},
            }
        }

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.generate_qa_answer", fake_generate_qa_answer)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "北京今天会不会下雨？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "weather_info"
    assert body["data"]["answer"] == "北京今天晴，约25度，暂时看起来没有下雨信号。"
    assert body["data"]["metadata"]["llm"]["model"] == "doubao-seed-2-0-mini-260428"
    assert body["data"]["metadata"]["structured"]["status"] == "ok"
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_router_fallback_runs_only_when_rule_marks_needs_fallback(client: AsyncClient, monkeypatch) -> None:
    called = {"value": False}

    async def fake_resolve_router_fallback(**kwargs):
        called["value"] = True
        return None, {"llm": {"provider": "openrouter", "model": "openai/gpt-5.4-nano", "latency_ms": 11}}

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fake_resolve_router_fallback)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": True,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "北京今天会不会下雨？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "weather_info"
    assert called["value"] is False
    assert body["data"]["metadata"]["intent_router"]["fallback_result"] is None


@pytest.mark.asyncio
async def test_router_fallback_can_override_rule_intent_when_rule_marks_needs_fallback(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", _fake_router_fallback_result("live_info", 0.91, "live_vs_attraction_conflict"))
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": True,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "故宫今天开放吗，顺便讲讲值不值得去", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "live_info"
    assert body["data"]["metadata"]["intent_router"]["rule_result"]["needs_fallback"] is True
    assert body["data"]["metadata"]["intent_router"]["fallback_result"]["intent"] == "live_info"
    assert body["data"]["metadata"]["intent_router"]["final_result"]["intent"] == "live_info"


@pytest.mark.asyncio
async def test_router_fallback_is_skipped_when_disabled(client: AsyncClient, monkeypatch) -> None:
    async def fail_if_called(**kwargs):
        raise AssertionError("fallback should not be called")

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fail_if_called)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "故宫今天开放吗，顺便讲讲值不值得去", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["metadata"]["intent_router"]["fallback_result"] is None


@pytest.mark.asyncio
async def test_router_fallback_is_skipped_for_boundary_out_of_scope(client: AsyncClient, monkeypatch) -> None:
    async def fail_if_called(**kwargs):
        raise AssertionError("fallback should not be called for boundary out_of_scope")

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.resolve_router_fallback", fail_if_called)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": True,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "现在故宫排队大概要多久？", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "out_of_scope"
    assert body["data"]["metadata"]["boundary_redirect"] is True
    assert body["data"]["metadata"]["boundary_topic"] == "crowd"
    assert body["data"]["metadata"]["intent_router"]["fallback_result"] is None
    assert "实时服务" in body["data"]["answer"]


def _fake_router_fallback_result(intent: str, confidence: float, reason: str):
    async def fake_resolve_router_fallback(**kwargs):
        return IntentRouterFallbackResult(intent=intent, confidence=confidence, reason=reason, weather_location_name=None), {"llm": {"provider": "openrouter", "model": "openai/gpt-5.4-nano"}}

    return fake_resolve_router_fallback


@pytest.mark.asyncio
async def test_non_chinese_query_can_use_pivot_and_translate_back(client: AsyncClient, monkeypatch) -> None:
    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="故宫有什么特别？",
            status="ok",
            reason=None,
            source_language="th",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="llm_structured",
        )

    async def fake_translate_answer(**kwargs):
        return TranslatorResult(
            text="พระราชวังต้องห้ามมีความพิเศษตรงประวัติศาสตร์และสถาปัตยกรรม",
            status="ok",
            reason=None,
            source_language="zh",
            target_language="th",
            mode="answer_postprocess",
            degraded=False,
            execution_path="llm_structured",
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.translate_answer", fake_translate_answer)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "openrouter",
                "translator_model": "demo-translator",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "พระราชวังต้องห้ามมีอะไรพิเศษ", "language": "th"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["resolved_query"]["used_translation_pivot"] is True
    assert body["data"]["metadata"]["answer_translation"]["used_answer_translation"] is True
    assert body["data"]["metadata"]["answer_translation"]["language_alignment_fallback_used"] is False
    assert body["data"]["answer"] == "พระราชวังต้องห้ามมีความพิเศษตรงประวัติศาสตร์และสถาปัตยกรรม"


@pytest.mark.asyncio
async def test_answer_translation_degraded_uses_english_alignment_fallback(client: AsyncClient, monkeypatch) -> None:
    async def fake_translate_answer(**kwargs):
        return TranslatorResult(
            text="雍和宫体现了宗教与帝国秩序",
            status="degraded",
            reason="provider_timeout",
            source_language="zh",
            target_language="en",
            mode="answer_postprocess",
            degraded=True,
            execution_path="timeout",
            provider="xfyun_its",
            model="its",
            latency_ms=321,
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.translate_answer", fake_translate_answer)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Tell me about this Beijing attraction", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["answer_translation"]["used_answer_translation"] is False
    assert body["data"]["metadata"]["answer_translation"]["degraded"] is True
    assert body["data"]["metadata"]["answer_translation"]["language_alignment_fallback_used"] is True
    assert "Please retry once" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_translation_intent_returns_bilingual_blocks(client: AsyncClient, monkeypatch) -> None:
    async def fake_translate_for_qa(**kwargs):
        return TranslatorResult(
            text="Please show the following text to staff:\n你好，我想请问卫生间在哪？",
            status="ok",
            reason=None,
            source_language="en",
            target_language="zh",
            mode="bilingual_for_display",
            degraded=False,
            execution_path="llm_structured",
            user_visible_lines=[
                "Please show the following text to staff:",
                "你好，我想请问卫生间在哪？",
            ],
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.translate_for_qa", fake_translate_for_qa)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "openrouter",
                "translator_model": "demo-translator",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Translate this for local staff: where is the restroom?", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "translation"
    assert body["data"]["metadata"]["translation"]["mode"] == "bilingual_for_display"
    assert body["data"]["metadata"]["translation"]["user_visible_lines"][0].startswith("Please show")
    assert "你好，我想请问卫生间在哪？" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_translation_intent_uses_auto_source_for_show_to_local_when_ui_language_is_zh(client: AsyncClient, monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_translate_for_qa(**kwargs):
        captured.update(kwargs)
        return TranslatorResult(
            text="请向工作人员展示以下文字。\n洗手间在哪里？",
            status="ok",
            reason=None,
            source_language=None,
            target_language="zh",
            mode="bilingual_for_display",
            degraded=False,
            execution_path="plain_mt",
            user_visible_lines=[
                "请向工作人员展示以下文字。",
                "洗手间在哪里？",
            ],
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.translate_for_qa", fake_translate_for_qa)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "xfyun_its",
                "translator_model": "its",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "帮我把‘Where is the restroom?’翻给工作人员看", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "translation"
    assert captured["query"] == "帮我把‘Where is the restroom?’翻给工作人员看"
    assert captured["user_language"] == "zh"
    assert body["data"]["metadata"]["translation"]["mode"] == "bilingual_for_display"
    assert body["data"]["metadata"]["translation"]["source_language"] is None
    assert body["data"]["metadata"]["translation"]["target_language"] == "zh"
    assert "洗手间在哪里？" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_multilingual_pivot_query_preserves_translation_intent(client: AsyncClient, monkeypatch) -> None:
    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="请翻译：请帮我拍张照片",
            status="ok",
            reason=None,
            source_language="vi",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="plain_mt",
        )

    captured: dict[str, object] = {}

    async def fake_translate_for_qa(**kwargs):
        captured["query"] = kwargs["query"]
        return TranslatorResult(
            text="请帮我拍张照片",
            status="ok",
            reason=None,
            source_language="zh",
            target_language="zh",
            mode="direct_translation",
            degraded=False,
            execution_path="plain_mt",
            user_visible_lines=["请帮我拍张照片"],
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.translate_for_qa", fake_translate_for_qa)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "xfyun_its",
                "translator_model": "its",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Hãy dịch: 请帮我拍张照片", "language": "vi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "translation"
    assert captured["query"] == "Hãy dịch: 请帮我拍张照片"
    assert body["data"]["metadata"]["resolved_query"]["used_translation_pivot"] is True
    assert body["data"]["metadata"]["intent_router"]["rule_result"]["intent"] == "translation"
    assert body["data"]["metadata"]["intent_router"]["final_result"]["intent"] == "translation"


@pytest.mark.asyncio
async def test_multilingual_pivot_query_preserves_manual_route_edit_intent(client: AsyncClient, monkeypatch) -> None:
    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="你能把下一站换成更容易到达的吗？",
            status="ok",
            reason=None,
            source_language="fil",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="plain_mt",
        )

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "xfyun_its",
                "translator_model": "its",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Pwede mo bang palitan ang susunod na hintuan ng mas madaling puntahan?", "language": "fil"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "manual_route_edit_redirect"
    assert body["data"]["metadata"]["resolved_query"]["used_translation_pivot"] is True
    assert body["data"]["metadata"]["manual_route_edit_redirect"] is True


@pytest.mark.asyncio
async def test_translation_runtime_error_returns_explicit_degraded_response(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = type("Error", (), {"model_dump": lambda self: {"error_type": "provider_error", "message": "boom", "retryable": False}})()

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())
    monkeypatch.setattr(
        "yoyo.modules.qa.orchestrator.get_settings",
        lambda: type(
            "S",
            (),
            {
                "qa_router_fallback_enabled": False,
                "llm_provider": "volcengine",
                "llm_model": "doubao-seed-2-0-mini-260428",
                "translator_provider": "openrouter",
                "translator_model": "demo-translator",
                "translator_timeout_seconds": 20.0,
                "translator_enabled": True,
                "translator_fail_open": True,
                "translator_pivot_language": "zh",
                "translator_answer_enabled": True,
                "translator_bilingual_enabled": True,
            },
        )(),
    )

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate: 请帮我拍张照片", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "translation"
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["metadata"]["degraded_reason"] == "runtime_translation_unavailable"
    assert body["data"]["metadata"]["llm"]["fallback_used"] is True


@pytest.mark.asyncio
async def test_live_info_returns_explicit_degraded_response_when_provider_is_unavailable(client: AsyncClient, monkeypatch) -> None:
    class FakeProvider:
        async def search(self, query: str) -> dict[str, object]:
            return {
                "summary": "",
                "sources": [{"type": "error", "name": "missing_key", "updated_at": None}],
                "status": "unavailable",
                "reason": "missing_provider_config",
            }

    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="北京今天的开放时间是什么？",
            status="ok",
            reason=None,
            source_language="en",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="llm_structured",
        )

    monkeypatch.setattr("yoyo.modules.qa.live_info.get_live_search_provider", lambda: FakeProvider())
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "What are today's opening hours in Beijing?", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "live_info"
    assert body["data"]["metadata"]["status"] == "unavailable"
    assert isinstance(body["data"]["metadata"]["reason"], str)
    assert body["data"]["metadata"]["reason"]
    assert body["data"]["metadata"]["degraded"] is True
    assert "latest guidance" not in body["data"]["answer"].lower()
    assert any(
        phrase in body["data"]["answer"].lower()
        for phrase in ["official", "verify", "ticketing"]
    )


@pytest.mark.asyncio
async def test_trip_assistant_structured_output_is_parsed_when_valid(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"You are currently at Tiananmen Square. Your next stop is Forbidden City.","status":"ok","reason":null,"route_focus":"next_stop","references_current_stop":true,"references_next_stop":true}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa-structured",
            "title": "QA trip structured",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "trip_assistant"
    assert body["data"]["metadata"]["structured"]["route_focus"] == "next_stop"
    assert body["data"]["metadata"]["references_current_stop"] is True
    assert body["data"]["metadata"]["references_next_stop"] is True
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_trip_assistant_malformed_structured_output_falls_back_safely(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '```json\n{"answer":"broken"\n```'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa-malformed",
            "title": "QA trip malformed",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "trip_assistant"
    assert "```" not in body["data"]["answer"]
    assert body["data"]["metadata"]["llm"]["structured_output_valid"] is False
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["metadata"]["degraded_reason"] == "trip_assistant_structured_output_invalid"
    assert "temporarily degraded" not in body["data"]["answer"].lower()
    assert "current route context is incomplete" not in body["data"]["answer"].lower()
    assert "Tiananmen Square" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_trip_assistant_runtime_error_returns_route_aware_fallback(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    async def fake_preprocess_query(**kwargs):
        return TranslatorResult(
            text="我下一站要去哪里？",
            status="ok",
            reason=None,
            source_language="en",
            target_language="zh",
            mode="routing_preprocess",
            degraded=False,
            execution_path="llm_structured",
        )

    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = type("Error", (), {"model_dump": lambda self: {"error_type": "provider_error", "message": "boom", "retryable": False}})()

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.preprocess_query", fake_preprocess_query)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-trip-runtime-error",
            "title": "Trip runtime error",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "trip_assistant"
    assert body["data"]["metadata"]["degraded_reason"] == "trip_assistant_runtime_unavailable"
    assert body["data"]["metadata"]["llm"]["fallback_used"] is True
    assert "Tiananmen Square" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_session_aware_trip_assistant_answer(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa",
            "title": "QA trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["supported"] is True
    assert body["data"]["intent"] == "trip_assistant"
    assert "Forbidden City" in body["data"]["answer"]
    assert "next" in body["data"]["answer"].lower() or "head toward" in body["data"]["answer"].lower()
    assert body["data"]["metadata"]["context"]["session_context"]["current_stop_name"] == "Tiananmen Square"
    assert body["data"]["metadata"]["context"]["session_context"]["next_stop_name"] == "Forbidden City"
    assert body["data"]["metadata"]["context"]["session_context"]["stop_count"] == 2


@pytest.mark.asyncio
async def test_trip_assistant_fenced_json_is_parsed_when_clean(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '```json\n{"answer":"You are currently at Tiananmen Square. Your next stop is Forbidden City.","status":"ok","reason":null,"route_focus":"next_stop","references_current_stop":true,"references_next_stop":true}\n```'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa-fenced",
            "title": "QA fenced trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my next route stop in Beijing itinerary?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "trip_assistant"
    assert body["data"]["metadata"]["structured"]["route_focus"] == "next_stop"
    assert body["data"]["answer"] == "You are currently at Tiananmen Square. Your next stop is Forbidden City."


@pytest.mark.asyncio
async def test_attraction_explain_structured_output_is_parsed_when_valid(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"Tiananmen Square: It is a major ceremonial landmark with deep modern history. Visitor tip: arrive early.","status":"ok","reason":null,"grounding":"sql","includes_history":true,"includes_tips":true}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-attraction-structured",
            "title": "Attraction QA structured",
            "preferences": {"preferred_poi_count": 1},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "Tell me about this Beijing attraction",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["structured"]["grounding"] == "sql"
    assert body["data"]["metadata"]["includes_history"] is True
    assert body["data"]["metadata"]["includes_tips"] is True
    assert body["data"]["metadata"]["retrieval_strategy"] == "sql_only"
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_unknown_beijing_attraction_explain_can_use_model_knowledge(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"鸟巢是北京奥林匹克公园的标志性场馆，因钢结构外观像鸟巢而得名。它主要和2008年北京奥运会相关，适合从现代城市地标和大型公共建筑角度理解。","status":"ok","reason":null,"grounding":"model_knowledge","includes_history":true,"includes_tips":false}'
            self.provider = "volcengine"
            self.model = "doubao-seed-2-0-mini-260428"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "鸟巢有什么历史，简单介绍一下", "language": "zh"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["attraction"] is None
    assert body["data"]["metadata"]["retrieval_strategy"] == "model_knowledge"
    assert body["data"]["metadata"]["grounding"] == "model_knowledge"
    assert body["data"]["metadata"]["validation"]["valid"] is True


@pytest.mark.asyncio
async def test_attraction_explain_malformed_structured_output_falls_back_to_grounded_response(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"bad payload","status":"ok"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-attraction-malformed",
            "title": "Attraction QA malformed",
            "preferences": {"preferred_poi_count": 1},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "Tell me about this Beijing attraction",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["llm"]["structured_output_valid"] is False
    assert body["data"]["metadata"]["status"] == "ok"
    assert body["data"]["metadata"]["grounding"] == "sql"
    assert body["data"]["metadata"]["degraded"] is False
    assert body["data"]["metadata"]["retrieval"]["name"] == "Tiananmen Square"
    assert "Tiananmen Square" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_session_aware_attraction_explain_returns_retrieval(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = type("Error", (), {"model_dump": lambda self: {"error_type": "provider_error", "message": "boom", "retryable": False}})()

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-attraction",
            "title": "Attraction QA trip",
            "preferences": {"preferred_poi_count": 1},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "Tell me about this Beijing attraction",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert "Tiananmen Square" in body["data"]["answer"]
    assert len(body["data"]["answer"].strip()) > 40
    assert "historical landmark" in body["data"]["answer"].lower() or "history" in body["data"]["answer"].lower()
    assert body["data"]["metadata"]["retrieval"]["name"] == "Tiananmen Square"


@pytest.mark.asyncio
async def test_attraction_explain_returns_explicit_degraded_response_without_grounded_detail(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.get_attraction_explanation", lambda *args, **kwargs: None)

    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = type("Error", (), {"model_dump": lambda self: {"error_type": "provider_error", "message": "boom", "retryable": False}})()

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    class EmptyRag:
        chunks = []
        retrieval_mode = "sql_only"
        fallback_used = False

        def model_dump(self) -> dict[str, object]:
            return {"chunks": [], "retrieval_mode": "sql_only", "fallback_used": False}

    class HybridContextStub:
        attraction = None
        profile = None
        live_info = None
        weather = None
        navigation = None
        rag = EmptyRag()
        session_context = {}
        dialogue_history = []
        prompt_safe_attraction = {}
        prompt_safe_profile = {}

        def model_dump(self) -> dict[str, object]:
            return {
                "attraction": None,
                "profile": None,
                "live_info": None,
                "rag": self.rag.model_dump(),
                "session_context": {},
                "dialogue_history": [],
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
            }

    async def fake_build_hybrid_context(**kwargs):
        return HybridContextStub()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Tell me about this Beijing attraction", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["metadata"]["degraded_reason"] == "insufficient_grounded_attraction_detail"
    assert "route/context data" not in body["data"]["answer"].lower()
    assert "Please retry once" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_qa_reads_triggered_session_state_after_gps_arrival(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa-triggered",
            "title": "QA triggered trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"current_stop_index": 0},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    gps_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert gps_response.status_code == 200
    assert gps_response.json()["data"]["arrived"] is True

    session_current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert session_current_response.status_code == 200
    session_current = session_current_response.json()["data"]
    assert session_current["playback_state"] == "triggered"
    assert session_current["current_stop"]["id"] == "stop-tiananmen-square"
    assert session_current["next_stop"]["id"] == "stop-forbidden-city"

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my current route stop in Beijing itinerary now?",
            "language": "en",
        },
    )
    assert qa_response.status_code == 200
    qa_data = qa_response.json()["data"]
    session_context = qa_data["metadata"]["context"]["session_context"]
    assert session_context["playback_state"] == "triggered"
    assert session_context["current_stop_id"] == "stop-tiananmen-square"
    assert session_context["current_stop_name"] == "Tiananmen Square"
    assert session_context["next_stop_id"] == "stop-forbidden-city"
    assert session_context["next_stop_name"] == "Forbidden City"
    assert "Tiananmen Square" in qa_data["answer"]


@pytest.mark.asyncio
async def test_qa_reads_next_stop_after_playback_completion(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa-complete",
            "title": "QA complete trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"current_stop_index": 0},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    gps_response = await client.post(
        f"/api/v1/gps/update/{guide_session_id}",
        json={"latitude": 39.9050, "longitude": 116.3976},
    )
    assert gps_response.status_code == 200
    assert gps_response.json()["data"]["arrived"] is True

    play_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "play"},
    )
    assert play_response.status_code == 200
    complete_response = await client.post(
        f"/api/v1/guide/playback/{guide_session_id}",
        json={"action": "complete"},
    )
    assert complete_response.status_code == 200

    session_current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert session_current_response.status_code == 200
    session_current = session_current_response.json()["data"]
    assert session_current["current_stop_index"] == 1
    assert session_current["current_stop"]["id"] == "stop-forbidden-city"
    assert session_current["next_stop"] is None
    assert session_current["playback_state"] == "not_triggered"

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my current route stop in Beijing itinerary now?",
            "language": "en",
        },
    )
    assert qa_response.status_code == 200
    qa_data = qa_response.json()["data"]
    session_context = qa_data["metadata"]["context"]["session_context"]
    assert session_context["current_stop_index"] == 1
    assert session_context["current_stop_id"] == "stop-forbidden-city"
    assert session_context["current_stop_name"] == "Forbidden City"
    assert session_context["next_stop_id"] is None
    assert session_context["next_stop_name"] is None
    assert session_context["playback_state"] == "not_triggered"
    assert "Forbidden City" in qa_data["answer"]


@pytest.mark.asyncio
async def test_qa_uses_session_current_route_context_after_version_switch(client: AsyncClient, monkeypatch) -> None:
    await _patch_planner_job_pool(monkeypatch)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-qa-version-switch",
            "title": "QA version switch trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {
                "current_stop_index": 1,
                "playback_state": "playing",
            },
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    edit_response = await client.post(
        f"/api/v1/planning/itineraries/{itinerary_data['id']}/edits",
        json={
            "operation": "replace_stop",
            "target_stop_id": "stop-forbidden-city",
            "replacement_stop_name": "Jingshan Park",
        },
    )
    assert edit_response.status_code == 200

    session_current_response = await client.get(f"/api/v1/session/{guide_session_id}/current")
    assert session_current_response.status_code == 200
    session_current = session_current_response.json()["data"]
    assert session_current["current_stop"]["id"] == "stop-jingshan-park"
    assert session_current["next_stop"] is None
    assert session_current["playback_state"] == "not_triggered"

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "What is my current route stop in Beijing itinerary now?",
            "language": "en",
        },
    )
    assert qa_response.status_code == 200
    qa_data = qa_response.json()["data"]
    session_context = qa_data["metadata"]["context"]["session_context"]
    assert session_context["itinerary_version_id"] == session_current["itinerary_version_id"]
    assert session_context["current_stop_index"] == session_current["current_stop_index"]
    assert session_context["current_stop_id"] == session_current["current_stop"]["id"]
    assert session_context["current_stop_name"] == session_current["current_stop"]["name"]
    assert session_context["next_stop_id"] is None
    assert session_context["next_stop_name"] is None
    assert session_context["playback_state"] == session_current["playback_state"]
    assert "Jingshan Park" in qa_data["answer"]
    assert any(token in qa_data["answer"].lower() for token in ["current", "active stop", "route", "stop"])


@pytest.mark.asyncio
async def test_manual_route_edit_redirect_answer_is_productized(client: AsyncClient, monkeypatch) -> None:
    enqueued: dict[str, str] = {}

    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            enqueued["function_name"] = function_name
            enqueued["job_id"] = job_id

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-manual-redirect",
            "title": "Manual redirect trip",
            "preferences": {"preferred_poi_count": 2},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {"language": "en"},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "Can you change route and remove the next stop?",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "manual_route_edit_redirect"
    assert body["data"]["metadata"]["manual_route_edit_redirect"] is True
    assert body["data"]["metadata"]["status"] == "redirect"
    assert "current product phase" not in body["data"]["answer"].lower()
    assert "route editing ui" not in body["data"]["answer"].lower()
    assert "行程编辑器" in body["data"]["answer"]
    assert "继续帮你解释现有路线" in body["data"]["answer"]


@pytest.mark.asyncio
async def test_attraction_explain_can_attach_rag_fallback_metadata(client: AsyncClient, monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    async def fake_get_rag_context(**kwargs):
        return RAGContext(
            retrieval_mode="sql_then_rag",
            fallback_used=True,
            chunks=[
                RAGChunk(
                    chunk_id="doc-1",
                    text="Forbidden City has a layered imperial history and symbolic background.",
                    source="postgresql",
                    score=0.95,
                    metadata={
                        "backend_ready": True,
                        "backend_reason": "backend_ready",
                        "query_status": "ok",
                        "query_reason": "backend_query",
                    },
                )
            ],
        )

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)
    monkeypatch.setattr("yoyo.modules.knowledge.hybrid_context_builder.get_rag_context", fake_get_rag_context)

    itinerary_response = await client.post(
        "/api/v1/planning/itineraries",
        json={
            "user_id": "user-rag",
            "title": "RAG QA trip",
            "preferences": {"preferred_poi_count": 1},
        },
    )
    itinerary_data = itinerary_response.json()["data"]

    guide_session_response = await client.post(
        "/api/v1/session/guide",
        json={
            "itinerary_id": itinerary_data["id"],
            "itinerary_version_id": itinerary_data["version"]["id"],
            "context": {},
        },
    )
    guide_session_id = guide_session_response.json()["data"]["id"]

    qa_response = await client.post(
        "/api/v1/qa/ask",
        json={
            "guide_session_id": guide_session_id,
            "query": "Tell me a deeper history and background story of this Beijing attraction",
            "language": "en",
        },
    )

    assert qa_response.status_code == 200
    body = qa_response.json()
    assert body["data"]["intent"] == "attraction_explain"
    assert body["data"]["metadata"]["retrieval_strategy"] == "sql_then_rag"
    assert body["data"]["metadata"]["rag_retrieval_mode"] == "sql_then_rag"
    assert body["data"]["metadata"]["rag_backend_ready"] is True
    assert body["data"]["metadata"]["rag_backend_reason"] == "backend_ready"
    assert body["data"]["metadata"]["rag_query_status"] == "ok"
    assert body["data"]["metadata"]["rag_query_reason"] == "backend_query"
    assert body["data"]["metadata"]["rag"] is not None
    assert len(body["data"]["metadata"]["rag"]["chunks"]) >= 1

# test_qa.py 是 QA 模块最重要的行为测试之一。
# 它覆盖了 QA 支持的几条主要路径，适合当成“QA 能做什么”的说明书来看。
from httpx import AsyncClient
import pytest

from yoyo.modules.knowledge.schemas import RAGChunk, RAGContext


async def _patch_planner_job_pool(monkeypatch) -> None:
    class FakeRedis:
        async def enqueue_job(self, function_name: str, job_id: str) -> None:
            return None

    async def fake_get_job_pool() -> FakeRedis:
        return FakeRedis()

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)


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


@pytest.mark.asyncio
async def test_translation_structured_output_is_parsed_when_valid(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"Could you please take a photo for me?","status":"ok","reason":null,"mode":"direct_translation"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate: 请帮我拍张照片", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["answer"] == "Could you please take a photo for me?"
    assert body["data"]["metadata"]["structured"]["mode"] == "direct_translation"
    assert body["data"]["metadata"]["degraded"] is False


@pytest.mark.asyncio
async def test_qa_translation_intent_returns_explicit_degraded_response(client: AsyncClient) -> None:
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
    assert "can't confirm a clean translation" in body["data"]["answer"].lower()


@pytest.mark.asyncio
async def test_translation_structured_output_with_wrapper_noise_falls_back(client: AsyncClient, monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"answer":"Answer: Could you please take a photo for me?","status":"ok","reason":null,"mode":"direct_translation"}'
            self.provider = "anthropic"
            self.model = "claude-sonnet-4-6"
            self.latency_ms = 12.0
            self.usage = type("Usage", (), {"model_dump": lambda self: {}})()
            self.error = None

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate: 请帮我拍张照片", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "translation"
    assert body["data"]["metadata"]["llm"]["structured_output_valid"] is False
    assert body["data"]["metadata"]["degraded"] is True
    assert body["data"]["answer"] == "I can't confirm a clean translation for that phrase right now. Please send the exact wording again and I'll translate it directly."


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

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

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
async def test_qa_live_info_includes_sources(client: AsyncClient) -> None:
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

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "Please translate this Beijing phrase", "language": "en"},
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

    monkeypatch.setattr("yoyo.modules.qa.live_info.get_live_search_provider", lambda: FakeProvider())

    response = await client.post(
        "/api/v1/qa/ask",
        json={"query": "What are today's opening hours in Beijing?", "language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "live_info"
    assert body["data"]["metadata"]["status"] == "unavailable"
    assert body["data"]["metadata"]["reason"] == "missing_provider_config"
    assert body["data"]["metadata"]["degraded"] is True
    assert "latest guidance" not in body["data"]["answer"].lower()
    assert "verify the latest same-day details" in body["data"]["answer"].lower()


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
    assert "Tiananmen Square" in body["data"]["answer"]
    assert "Forbidden City" in body["data"]["answer"]
    assert "next" in body["data"]["answer"].lower() or "head toward" in body["data"]["answer"].lower()
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

    monkeypatch.setattr("yoyo.modules.planner.service.get_job_pool", fake_get_job_pool)

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
    assert "Visitor tip" in body["data"]["answer"]
    assert "historical landmark" in body["data"]["answer"].lower() or "history" in body["data"]["answer"].lower()
    assert body["data"]["metadata"]["retrieval"]["name"] == "Tiananmen Square"


@pytest.mark.asyncio
async def test_attraction_explain_returns_explicit_degraded_response_without_grounded_detail(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.get_attraction_explanation", lambda *args, **kwargs: None)

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
    assert "try again shortly" in body["data"]["answer"].lower()


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
    assert "Forbidden City" not in qa_data["answer"]


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
    assert body["data"]["intent"] == "trip_assistant"
    assert body["data"]["metadata"]["manual_route_edit_redirect"] is True
    assert "current product phase" not in body["data"]["answer"].lower()
    assert "route editing ui" not in body["data"]["answer"].lower()
    assert "itinerary editor" in body["data"]["answer"].lower()


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

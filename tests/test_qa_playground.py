import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_qa_playground_page_renders(client: AsyncClient) -> None:
    response = await client.get("/api/v1/qa/playground")

    assert response.status_code == 200
    assert "Yoyo QA Playground" in response.text
    assert "POST /api/v1/qa/ask" in response.text
    assert "qa_playground" in response.text
    assert "await runAsk();" in response.text
    assert "await runPreview();\n          await runAsk();" not in response.text
    assert "默认：最小请求，不注入 override" in response.text


@pytest.mark.asyncio
async def test_qa_preview_exposes_prompt_and_playground_overrides(client: AsyncClient, monkeypatch) -> None:
    class FakeHybrid:
        def __init__(self) -> None:
            self.profile = None
            self.attraction = None
            self.live_info = None
            self.weather = None
            self.navigation = None
            self.rag = None
            self.prompt_safe_attraction = {}
            self.prompt_safe_profile = {}
            self.session_context = {}
            self.dialogue_history = []

        def model_copy(self, update=None):
            copied = FakeHybrid()
            copied.__dict__.update(self.__dict__)
            if update:
                copied.__dict__.update(update)
            return copied

        def model_dump(self):
            return {
                "profile": self.profile.model_dump() if self.profile else None,
                "attraction": self.attraction.model_dump() if self.attraction else None,
                "live_info": None,
                "weather": None,
                "navigation": None,
                "rag": None,
                "prompt_safe_attraction": self.prompt_safe_attraction,
                "prompt_safe_profile": self.prompt_safe_profile,
                "session_context": self.session_context,
                "dialogue_history": self.dialogue_history,
            }

    async def fake_build_hybrid_context(**kwargs):
        return FakeHybrid()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/preview",
        json={
            "query": "故宫适合带长辈慢慢逛吗？",
            "language": "zh",
            "user_id": "guest_demo",
            "context": {
                "qa_playground": {
                    "session_override": {
                        "current_stop_name": "天安门广场",
                        "next_stop_name": "故宫",
                        "remaining_stop_count": 3,
                        "plan_summary": "经典中轴线一日游",
                    },
                    "profile_override": {
                        "user_id": "guest_demo",
                        "travel_style": "relaxed",
                        "walking_preference": "low",
                        "guide_style_preference": "SJ",
                        "interests": ["history", "architecture"],
                    },
                    "attraction_override": {
                        "name": "故宫",
                        "category": "museum",
                        "short_intro": "故宫是皇家宫殿。",
                        "history": "它体现了中轴线礼制。",
                        "highlights": ["太和殿"],
                    },
                    "dialogue_history": [
                        {"role": "user", "content": "我们想慢慢逛。"},
                        {"role": "assistant", "content": "那我会按轻松节奏推荐。"},
                    ],
                }
            },
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["playground"]["enabled"] is True
    assert body["playground"]["session_override_applied"] is True
    assert body["playground"]["profile_override_applied"] is True
    assert body["playground"]["attraction_override_applied"] is True
    assert body["playground"]["dialogue_history_override_applied"] is True
    assert body["session_context"]["current_stop_name"] == "天安门广场"
    assert body["hybrid_context"]["profile"]["travel_style"] == "relaxed"
    assert body["hybrid_context"]["attraction"]["name"] == "故宫"
    assert body["dialogue_history"][0]["content"] == "我们想慢慢逛。"
    assert body["prompt_preview"] is not None
    prompt_messages = body["prompt_preview"]["messages"]
    user_prompt = next(item["content"] for item in prompt_messages if item["role"] == "user")
    assert "guide_style: guardian" in user_prompt
    assert "故宫" in user_prompt
    assert body["context"]["session_context"]["current_stop_name"] == "天安门广场"
    assert body["context"]["session_context"]["hybrid_context"]["session_context"]["current_stop_name"] == "天安门广场"


@pytest.mark.asyncio
async def test_qa_ask_reports_playground_metadata(client: AsyncClient, monkeypatch) -> None:
    async def fake_generate_qa_answer(*, provider: str, model: str, **kwargs):
        return "这是一个测试回答。", {
            "llm": {
                "provider": provider,
                "model": model,
                "usage": {},
                "structured_output_valid": True,
            },
            "status": "ok",
            "reason": None,
            "grounding": "sql",
            "includes_history": True,
            "includes_tips": True,
            "degraded": False,
            "degraded_reason": None,
            "structured": {
                "answer": "这是一个测试回答。",
                "status": "ok",
                "reason": None,
                "grounding": "sql",
                "includes_history": True,
                "includes_tips": True,
            },
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
                "navigation": None,
                "rag": None,
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
                "session_context": {},
                "dialogue_history": [],
                "model_dump": lambda self: {},
                "model_copy": lambda self, update=None: type(
                    "Hybrid",
                    (),
                    {
                        "profile": (update or {}).get("profile"),
                        "attraction": (update or {}).get("attraction"),
                        "live_info": None,
                        "weather": None,
                        "navigation": None,
                        "rag": None,
                        "prompt_safe_attraction": (update or {}).get("prompt_safe_attraction", {}),
                        "prompt_safe_profile": (update or {}).get("prompt_safe_profile", {}),
                        "session_context": (update or {}).get("session_context", {}),
                        "dialogue_history": (update or {}).get("dialogue_history", []),
                        "model_dump": lambda inner_self: {},
                        "model_copy": lambda inner_self, update=None: inner_self,
                    },
                )(),
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.generate_qa_answer", fake_generate_qa_answer)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "给我简短介绍一下故宫。",
            "language": "zh",
            "context": {
                "qa_playground": {
                    "profile_override": {
                        "user_id": "guest_demo",
                        "guide_style_preference": "SJ",
                    }
                }
            },
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["metadata"]["playground"]["enabled"] is True
    assert body["metadata"]["playground"]["profile_override_applied"] is True
    assert "latency_ms" in body["metadata"]
    assert set(body["metadata"]["latency_ms"]).issuperset(
        {
            "preprocess_ms",
            "routing_ms",
            "context_build_ms",
            "context_build_breakdown_ms",
            "generation_ms",
            "postprocess_ms",
            "total_ms",
        }
    )


@pytest.mark.asyncio
async def test_qa_ask_without_playground_override_keeps_playground_disabled(client: AsyncClient, monkeypatch) -> None:
    async def fake_generate_qa_answer(*, provider: str, model: str, **kwargs):
        return "这是一个测试回答。", {
            "llm": {
                "provider": provider,
                "model": model,
                "usage": {},
                "structured_output_valid": True,
            },
            "status": "ok",
            "reason": None,
            "grounding": "sql",
            "includes_history": False,
            "includes_tips": False,
            "degraded": False,
            "degraded_reason": None,
            "structured": {
                "answer": "这是一个测试回答。",
                "status": "ok",
                "reason": None,
                "grounding": "sql",
                "includes_history": False,
                "includes_tips": False,
            },
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
                "navigation": None,
                "rag": None,
                "prompt_safe_attraction": {},
                "prompt_safe_profile": {},
                "session_context": {},
                "dialogue_history": [],
                "model_dump": lambda self: {},
                "model_copy": lambda self, update=None: self,
            },
        )()

    monkeypatch.setattr("yoyo.modules.qa.orchestrator.generate_qa_answer", fake_generate_qa_answer)
    monkeypatch.setattr("yoyo.modules.qa.orchestrator.build_hybrid_context", fake_build_hybrid_context)

    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "给我简短介绍一下故宫。",
            "language": "zh",
            "context": {"market": "beijing"},
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["metadata"]["playground"]["enabled"] is False

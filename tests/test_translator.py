import pytest

from yoyo.modules.llm.schemas import LLMError, LLMUsage
from yoyo.modules.translator.prompts import build_routing_translation_request
from yoyo.modules.translator.service import (
    _build_display_instruction,
    _infer_target_language_from_query,
    _parse_explicit_translation_query,
    preprocess_query,
    translate_answer,
    translate_for_qa,
)


@pytest.mark.asyncio
async def test_preprocess_query_returns_degraded_when_disabled() -> None:
    result = await preprocess_query(
        query="Where is the restroom?",
        source_language="en",
        target_language="zh",
        provider="openrouter",
        model="demo-model",
        timeout_seconds=10,
        enabled=False,
    )

    assert result.degraded is True
    assert result.reason == "translator_disabled"
    assert result.text == "Where is the restroom?"


@pytest.mark.asyncio
async def test_translate_answer_returns_original_when_disabled() -> None:
    result = await translate_answer(
        answer="你好，我想问一下卫生间在哪。",
        source_language="zh",
        target_language="th",
        provider="openrouter",
        model="demo-model",
        timeout_seconds=10,
        enabled=False,
    )

    assert result.degraded is True
    assert result.text == "你好，我想问一下卫生间在哪。"
    assert result.reason == "translator_disabled"


@pytest.mark.asyncio
async def test_translate_for_qa_returns_formatter_fallback_when_disabled() -> None:
    result = await translate_for_qa(
        query="Please translate: 请帮我拍张照片",
        user_language="en",
        provider="openrouter",
        model="demo-model",
        timeout_seconds=10,
        enabled=False,
        bilingual_enabled=True,
    )

    assert result.degraded is True
    assert result.reason == "translator_disabled"
    assert len(result.user_visible_lines) == 1


@pytest.mark.asyncio
async def test_plain_mt_answer_translation_uses_raw_text(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = "Where is the restroom?"
            self.provider = "hy_mt"
            self.model = "HY-MT1.5-1.8B"
            self.latency_ms = 8.0
            self.error = None
            self.usage = LLMUsage(prompt_tokens=11, completion_tokens=7, total_tokens=18, cost=0.001)

    class FakeRuntime:
        async def generate(self, request):
            assert request.provider == "hy_mt"
            assert request.metadata["plain_text"] == "卫生间在哪里？"
            assert request.metadata["target_language"] == "en"
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_answer(
        answer="卫生间在哪里？",
        source_language="zh",
        target_language="en",
        provider="hy_mt",
        model="HY-MT1.5-1.8B",
        timeout_seconds=10,
        enabled=True,
    )

    assert result.degraded is False
    assert result.execution_path == "plain_mt"
    assert result.text == "Where is the restroom?"
    assert result.prompt_tokens == 11
    assert result.completion_tokens == 7
    assert result.total_tokens == 18
    assert result.estimated_total_cost == 0.001
    assert result.attempt_count == 1
    assert result.retry_performed is False
    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_plain_mt_qa_translation_can_build_bilingual_display(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = "你好，我想请问卫生间在哪？"
            self.provider = "hy_mt"
            self.model = "HY-MT1.5-1.8B"
            self.latency_ms = 8.0
            self.error = None
            self.usage = LLMUsage(prompt_tokens=10, completion_tokens=6, total_tokens=16, cost=0.0008)

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query="帮我问一下卫生间在哪",
        user_language="en",
        provider="hy_mt",
        model="HY-MT1.5-1.8B",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is False
    assert result.mode == "bilingual_for_display"
    assert result.execution_path == "plain_mt"
    assert result.target_language == "zh"
    assert len(result.user_visible_lines) == 2
    assert "staff" in result.user_visible_lines[0].lower()
    assert "卫生间" in result.user_visible_lines[1]
    assert result.total_tokens == 16
    assert result.attempt_count == 1
    assert result.retry_performed is False
    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_plain_mt_preprocess_query_returns_degraded_on_error(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = 8.0
            self.raw_response = {}
            self.usage = LLMUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5, cost=None)
            self.error = LLMError(error_type="RuntimeError", message="boom", retryable=False)

    class FakeRuntime:
        async def generate(self, request):
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await preprocess_query(
        query="เราควรไปที่ไหนต่อ",
        source_language="th",
        target_language="zh",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
    )

    assert result.degraded is True
    assert result.execution_path == "provider_error"
    assert result.text == "เราควรไปที่ไหนต่อ"
    assert result.prompt_tokens == 5
    assert result.attempt_count == 1
    assert result.retry_performed is False
    assert len(result.attempts) == 1


def test_infer_target_language_supports_sea_aliases() -> None:
    assert _infer_target_language_from_query("Translate this into Malay: 你好", "en") == "ms"
    assert _infer_target_language_from_query("Translate this into Filipino: 你好", "en") == "fil"
    assert _infer_target_language_from_query("Translate this into Tagalog: 你好", "en") == "fil"
    assert _infer_target_language_from_query("Translate this into Burmese: 你好", "en") == "my"
    assert _infer_target_language_from_query("Translate this into Khmer: 你好", "en") == "km"
    assert _infer_target_language_from_query("Translate this into Lao: 你好", "en") == "lo"


def test_build_display_instruction_supports_sea_languages() -> None:
    assert "kakitangan" in _build_display_instruction("ms")
    assert "Ipakita" in _build_display_instruction("fil")
    assert "ဝန်ထမ်း" in _build_display_instruction("my")
    assert "បុគ្គលិក" in _build_display_instruction("km")
    assert "ພະນັກງານ" in _build_display_instruction("lo")


def test_parse_explicit_translation_query_no_longer_infers_source_language() -> None:
    parsed = _parse_explicit_translation_query("Translate this into Chinese: Pwede ba akong magpahinga rito nang sampung minuto?")

    assert parsed is not None
    assert parsed["text"] == "Pwede ba akong magpahinga rito nang sampung minuto?"
    assert parsed["target_language"] == "zh"
    assert "source_language" not in parsed


def test_parse_explicit_translation_query_supports_zh_suffix_and_quotes() -> None:
    parsed = _parse_explicit_translation_query('把“Where is the restroom?”翻成中文')

    assert parsed is not None
    assert parsed["text"] == "Where is the restroom?"
    assert parsed["target_language"] == "zh"
    assert parsed["show_to_local"] is False


def test_parse_explicit_translation_query_supports_zh_colon_prompt() -> None:
    parsed = _parse_explicit_translation_query("这句话用中文怎么说：Where is the restroom?")

    assert parsed is not None
    assert parsed["text"] == "Where is the restroom?"
    assert parsed["target_language"] == "zh"
    assert parsed["show_to_local"] is False


def test_routing_translation_prompt_preserves_negation_and_mixed_intent() -> None:
    request = build_routing_translation_request(
        provider="xfyun_its",
        model="its",
        query="Don't change the route, just translate today's closure notice into English.",
        source_language="en",
        target_language="zh",
        timeout_seconds=10,
    )

    system_prompt = request.messages[0].content
    assert "Preserve intent, negation" in system_prompt
    assert "Do not simplify a mixed-intent query into a single intent" in system_prompt
    assert "don't change the route" in system_prompt
    assert request.metadata["prompt_version"] == "translator-routing-v1"


@pytest.mark.asyncio
async def test_plain_mt_qa_translation_english_wrapper_defaults_to_user_language(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = "我可以在这里休息十分钟吗？"
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = 8.0
            self.raw_response = {}
            self.error = None
            self.usage = LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, cost=None)

    class FakeRuntime:
        async def generate(self, request):
            assert request.metadata["plain_text"] == "Pwede ba akong magpahinga rito nang sampung minuto?"
            assert request.metadata["source_language"] == "en"
            assert request.metadata["target_language"] == "zh"
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query="Translate this into Chinese: Pwede ba akong magpahinga rito nang sampung minuto?",
        user_language="en",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is False
    assert result.text == "我可以在这里休息十分钟吗？"
    assert result.target_language == "zh"
    assert result.attempt_count == 1
    assert result.retry_performed is False
    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_plain_mt_retries_once_on_retryable_error(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, text: str, latency_ms: float, error: LLMError | None) -> None:
            self.text = text
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = latency_ms
            self.raw_response = {}
            self.error = error
            self.usage = LLMUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5, cost=None)

    calls = {"count": 0}

    class FakeRuntime:
        async def generate(self, request):
            calls["count"] += 1
            if calls["count"] == 1:
                return FakeResponse("", 1000.0, LLMError(error_type="ReadTimeout", message="timed out", retryable=True))
            return FakeResponse("厕所在哪里？", 120.0, None)

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query="Translate this into Chinese: Nhà vệ sinh ở đâu?",
        user_language="vi",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is False
    assert result.text == "厕所在哪里？"
    assert result.attempt_count == 2
    assert result.retry_performed is True
    assert len(result.attempts) == 2
    assert result.attempts[0]["error"]["retryable"] is True
    assert result.attempts[1]["error"] is None


@pytest.mark.asyncio
async def test_plain_mt_does_not_retry_non_retryable_error(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = ""
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = 50.0
            self.raw_response = {}
            self.error = LLMError(error_type="RuntimeError", message="bad credentials", retryable=False)
            self.usage = LLMUsage(prompt_tokens=5, completion_tokens=0, total_tokens=5, cost=None)

    calls = {"count": 0}

    class FakeRuntime:
        async def generate(self, request):
            calls["count"] += 1
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query="Translate this into Thai: 请帮我拍张照片",
        user_language="zh",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is True
    assert result.target_language == "th"
    assert calls["count"] == 1
    assert result.attempt_count == 1
    assert result.retry_performed is False
    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_plain_mt_qa_translation_supports_zh_suffix_prompt(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = "洗手间在哪里？"
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = 8.0
            self.raw_response = {}
            self.error = None
            self.usage = LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, cost=None)

    class FakeRuntime:
        async def generate(self, request):
            assert request.metadata["plain_text"] == "Where is the restroom?"
            assert request.metadata["target_language"] == "zh"
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query='把“Where is the restroom?”翻成中文',
        user_language="en",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is False
    assert result.text == "洗手间在哪里？"
    assert result.target_language == "zh"


@pytest.mark.asyncio
async def test_plain_mt_qa_translation_supports_show_to_local_quoted_prompt(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = "洗手间在哪里？"
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = 8.0
            self.raw_response = {}
            self.error = None
            self.usage = LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, cost=None)

    class FakeRuntime:
        async def generate(self, request):
            assert request.metadata["plain_text"] == "Where is the restroom?"
            assert request.metadata["source_language"] == "en"
            assert request.metadata["target_language"] == "zh"
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query='帮我把“Where is the restroom?”翻给工作人员看',
        user_language="en",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is False
    assert result.mode == "bilingual_for_display"
    assert result.target_language == "zh"
    assert result.user_visible_lines[1] == "洗手间在哪里？"
    assert result.attempt_count == 1
    assert result.retry_performed is False
    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_plain_mt_qa_translation_show_to_local_infers_source_from_quoted_text_when_ui_language_matches_target(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self) -> None:
            self.text = "洗手间在哪里？"
            self.provider = "xfyun_its"
            self.model = "its"
            self.latency_ms = 8.0
            self.raw_response = {}
            self.error = None
            self.usage = LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, cost=None)

    class FakeRuntime:
        async def generate(self, request):
            assert request.metadata["plain_text"] == "Where is the restroom?"
            assert request.metadata["source_language"] == "en"
            assert request.metadata["target_language"] == "zh"
            return FakeResponse()

    monkeypatch.setattr("yoyo.modules.qa.generator.get_llm_runtime", lambda: FakeRuntime())

    result = await translate_for_qa(
        query='帮我把“Where is the restroom?”翻给工作人员看',
        user_language="zh",
        provider="xfyun_its",
        model="its",
        timeout_seconds=10,
        enabled=True,
        bilingual_enabled=True,
    )

    assert result.degraded is False
    assert result.mode == "bilingual_for_display"
    assert result.target_language == "zh"
    assert result.user_visible_lines[1] == "洗手间在哪里？"

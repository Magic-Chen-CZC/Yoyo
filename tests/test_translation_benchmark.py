from pathlib import Path

from yoyo.evals.translation_runner import run_translation_benchmark_sync


def test_translation_benchmark_product_suite(monkeypatch, tmp_path: Path) -> None:
    class FakeBlock:
        def __init__(self, role: str, language: str, text: str) -> None:
            self.role = role
            self.language = language
            self.text = text

        def model_dump(self) -> dict[str, str]:
            return {"role": self.role, "language": self.language, "text": self.text}

    class FakeTranslatorResult:
        def __init__(self) -> None:
            self.text = "Could you please take a photo for me?"
            self.status = "ok"
            self.reason = None
            self.execution_path = "plain_mt"
            self.latency_ms = 5.0
            self.source_language = "zh"
            self.target_language = "en"
            self.mode = "direct_translation"
            self.prompt_tokens = 10
            self.completion_tokens = 8
            self.total_tokens = 18
            self.estimated_input_cost = None
            self.estimated_output_cost = None
            self.estimated_total_cost = 0.0012
            self.llm_error = None
            self.raw_text = self.text
            self.structured_output_valid = None
            self.attempt_count = 2
            self.retry_performed = True
            self.attempts = [
                {"attempt": 1, "latency_ms": 1000.0, "error": {"error_type": "ReadTimeout", "message": "timed out", "retryable": True}, "raw_text": None},
                {"attempt": 2, "latency_ms": 5.0, "error": None, "raw_text": self.text},
            ]
            self.user_visible_lines = [self.text]
            self.display_blocks = [FakeBlock("translation", "en", self.text)]

    async def fake_translate_for_qa(**kwargs):
        return FakeTranslatorResult()

    monkeypatch.setattr("yoyo.evals.translation_runner.translate_for_qa", fake_translate_for_qa)

    dataset = tmp_path / "product.yaml"
    dataset.write_text(
        """
dataset_name: translation_product_smoke
dataset_version: v1
cases:
  - id: c1
    question_type: ask_photo_help
    category: direct_translation
    direction: zh_to_en
    query: \"Please translate: 请帮我拍张照片\"
    user_language: zh
    source_language: zh
    target_language: en
    expected_phrases: [\"photo\"]
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "results.json"
    summary = tmp_path / "summary.json"

    results, summary_payload = run_translation_benchmark_sync(
        suite="product_translation",
        dataset_path=dataset,
        provider="hy_mt",
        model="HY-MT1.5-1.8B",
        timeout_seconds=10,
        output_path=output,
        summary_output_path=summary,
    )

    assert len(results) == 1
    assert results[0]["response_text"] == "Could you please take a photo for me?"
    assert results[0]["run_id"].startswith("translation-hy_mt-product_translation-")
    assert results[0]["question_type"] == "ask_photo_help"
    assert results[0]["direction"] == "zh_to_en"
    assert results[0]["total_tokens"] == 18
    assert results[0]["raw_text"] == "Could you please take a photo for me?"
    assert results[0]["attempt_count"] == 2
    assert results[0]["retry_performed"] is True
    assert len(results[0]["attempts"]) == 2
    assert results[0]["score"] > 0
    assert summary_payload["avg_score"] > 0
    assert summary_payload["dataset_name"] == "translation_product_smoke"
    assert summary_payload["sum_total_tokens"] == 18
    assert "zh_to_en" in summary_payload["by_direction"]
    assert output.exists()
    assert summary.exists()


def test_translation_benchmark_routing_suite(monkeypatch, tmp_path: Path) -> None:
    class FakeTranslatorResult:
        def __init__(self) -> None:
            self.text = "下一站去哪里"
            self.status = "ok"
            self.reason = None
            self.execution_path = "plain_mt"
            self.latency_ms = 5.0
            self.source_language = "en"
            self.target_language = "zh"
            self.mode = "routing_preprocess"
            self.prompt_tokens = 9
            self.completion_tokens = 4
            self.total_tokens = 13
            self.estimated_input_cost = None
            self.estimated_output_cost = None
            self.estimated_total_cost = 0.0007
            self.llm_error = None
            self.raw_text = self.text
            self.structured_output_valid = None
            self.attempt_count = 1
            self.retry_performed = False
            self.attempts = [{"attempt": 1, "latency_ms": 5.0, "error": None, "raw_text": self.text}]

    async def fake_preprocess_query(**kwargs):
        return FakeTranslatorResult()

    monkeypatch.setattr("yoyo.evals.translation_runner.preprocess_query", fake_preprocess_query)
    monkeypatch.setattr("yoyo.evals.translation_runner.score_intent", lambda query, raw_query=None: {"intent": "trip_assistant", "confidence": 0.9})

    dataset = tmp_path / "routing.yaml"
    dataset.write_text(
        """
dataset_name: translation_routing_smoke
dataset_version: v1
cases:
  - id: c1
    question_type: trip_assistant
    category: trip_assistant
    direction: en_to_zh
    query: \"Where should I go next?\"
    user_language: en
    source_language: en
    target_language: zh
    expected_intent: trip_assistant
    must_preserve_entities: []
    must_preserve_temporal_signal: [\"下一\"]
""".strip(),
        encoding="utf-8",
    )
    output = tmp_path / "results.json"
    summary = tmp_path / "summary.json"

    results, summary_payload = run_translation_benchmark_sync(
        suite="routing_preprocess",
        dataset_path=dataset,
        provider="hy_mt",
        model="HY-MT1.5-1.8B",
        timeout_seconds=10,
        output_path=output,
        summary_output_path=summary,
    )

    assert len(results) == 1
    assert results[0]["downstream_intent"] == "trip_assistant"
    assert results[0]["direction"] == "en_to_zh"
    assert results[0]["total_tokens"] == 13
    assert results[0]["raw_text"] == "下一站去哪里"
    assert results[0]["attempt_count"] == 1
    assert results[0]["retry_performed"] is False
    assert len(results[0]["attempts"]) == 1
    assert summary_payload["avg_score"] > 0
    assert summary_payload["dataset_name"] == "translation_routing_smoke"
    assert summary_payload["sum_total_tokens"] == 13
    assert "trip_assistant" in summary_payload["by_question_type"]


def test_translation_benchmark_product_suite_requires_explicit_user_language(monkeypatch, tmp_path: Path) -> None:
    async def fake_translate_for_qa(**kwargs):
        raise AssertionError("should not reach translator when dataset is invalid")

    monkeypatch.setattr("yoyo.evals.translation_runner.translate_for_qa", fake_translate_for_qa)

    dataset = tmp_path / "product_invalid.yaml"
    dataset.write_text(
        """
dataset_name: translation_product_invalid
dataset_version: v1
question_types: [ask_photo_help]
cases:
  - id: c1
    question_type: ask_photo_help
    category: direct_translation
    direction: zh_to_en
    query: \"Please translate: 请帮我拍张照片\"
    source_language: zh
    target_language: en
    expected_phrases: [\"photo\"]
""".strip(),
        encoding="utf-8",
    )

    try:
        run_translation_benchmark_sync(
            suite="product_translation",
            dataset_path=dataset,
            provider="hy_mt",
            model="HY-MT1.5-1.8B",
            timeout_seconds=10,
            output_path=tmp_path / "results.json",
            summary_output_path=tmp_path / "summary.json",
        )
    except ValueError as exc:
        assert "user_language" in str(exc)
        assert "c1" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing user_language")


def test_translation_benchmark_rejects_direction_language_mismatch(monkeypatch, tmp_path: Path) -> None:
    async def fake_translate_for_qa(**kwargs):
        raise AssertionError("should not reach translator when dataset is invalid")

    monkeypatch.setattr("yoyo.evals.translation_runner.translate_for_qa", fake_translate_for_qa)

    dataset = tmp_path / "product_bad_direction.yaml"
    dataset.write_text(
        """
dataset_name: translation_product_invalid
dataset_version: v1
question_types: [ask_photo_help]
cases:
  - id: c1
    question_type: ask_photo_help
    category: direct_translation
    direction: zh_to_th
    query: \"Please translate: 请帮我拍张照片\"
    user_language: zh
    source_language: zh
    target_language: en
    expected_phrases: [\"photo\"]
""".strip(),
        encoding="utf-8",
    )

    try:
        run_translation_benchmark_sync(
            suite="product_translation",
            dataset_path=dataset,
            provider="hy_mt",
            model="HY-MT1.5-1.8B",
            timeout_seconds=10,
            output_path=tmp_path / "results.json",
            summary_output_path=tmp_path / "summary.json",
        )
    except ValueError as exc:
        assert "invalid direction" in str(exc)
        assert "c1" in str(exc)
    else:
        raise AssertionError("expected ValueError for mismatched direction")


def test_translation_benchmark_routing_suite_requires_expected_intent(monkeypatch, tmp_path: Path) -> None:
    async def fake_preprocess_query(**kwargs):
        raise AssertionError("should not reach translator when dataset is invalid")

    monkeypatch.setattr("yoyo.evals.translation_runner.preprocess_query", fake_preprocess_query)

    dataset = tmp_path / "routing_invalid.yaml"
    dataset.write_text(
        """
dataset_name: translation_routing_invalid
dataset_version: v1
question_types: [trip_assistant]
cases:
  - id: c1
    question_type: trip_assistant
    category: trip_assistant
    direction: en_to_zh
    query: \"Where should I go next?\"
    user_language: en
    source_language: en
    target_language: zh
    must_preserve_entities: []
    must_preserve_temporal_signal: [\"下一\"]
""".strip(),
        encoding="utf-8",
    )

    try:
        run_translation_benchmark_sync(
            suite="routing_preprocess",
            dataset_path=dataset,
            provider="hy_mt",
            model="HY-MT1.5-1.8B",
            timeout_seconds=10,
            output_path=tmp_path / "results.json",
            summary_output_path=tmp_path / "summary.json",
        )
    except ValueError as exc:
        assert "expected_intent" in str(exc)
        assert "c1" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing expected_intent")


def test_translation_benchmark_rejects_extreme_multilingual_query(monkeypatch, tmp_path: Path) -> None:
    async def fake_translate_for_qa(**kwargs):
        raise AssertionError("should not reach translator when dataset is invalid")

    monkeypatch.setattr("yoyo.evals.translation_runner.translate_for_qa", fake_translate_for_qa)

    dataset = tmp_path / "product_extreme_multilingual.yaml"
    dataset.write_text(
        """
dataset_name: translation_product_invalid
dataset_version: v1
question_types: [ask_photo_help]
cases:
  - id: c1
    question_type: ask_photo_help
    category: direct_translation
    direction: zh_to_en
    query: \"Please translate: 请帮我拍张照片 สวัสดี Mingalaba\"
    user_language: zh
    source_language: zh
    target_language: en
    expected_phrases: [\"photo\"]
""".strip(),
        encoding="utf-8",
    )

    try:
        run_translation_benchmark_sync(
            suite="product_translation",
            dataset_path=dataset,
            provider="hy_mt",
            model="HY-MT1.5-1.8B",
            timeout_seconds=10,
            output_path=tmp_path / "results.json",
            summary_output_path=tmp_path / "summary.json",
        )
    except ValueError as exc:
        assert "too multilingual" in str(exc)
        assert "c1" in str(exc)
    else:
        raise AssertionError("expected ValueError for extreme multilingual query")

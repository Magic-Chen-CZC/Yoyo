from __future__ import annotations

import re


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[一-鿿]", text))


def _has_thai(text: str) -> bool:
    return bool(re.search(r"[฀-๿]", text))


def _has_vietnamese_markers(text: str) -> bool:
    return bool(re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", text.lower()))


def _has_burmese(text: str) -> bool:
    return bool(re.search(r"[က-႟]", text))


def _has_khmer(text: str) -> bool:
    return bool(re.search(r"[ក-៿]", text))


def _has_lao(text: str) -> bool:
    return bool(re.search(r"[ກ-໿]", text))


def _has_latin_words(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]", text))


def _normalize(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def _language_match(target_language: str, output_text: str) -> bool:
    target = (target_language or "").lower()
    if target.startswith("zh"):
        return _has_cjk(output_text)
    if target.startswith("en"):
        return _has_latin_words(output_text) and not _has_cjk(output_text)
    if target.startswith("th"):
        return _has_thai(output_text)
    if target.startswith("vi"):
        return _has_vietnamese_markers(output_text) or _has_latin_words(output_text)
    if target.startswith("id") or target.startswith("ms") or target.startswith("fil") or target.startswith("tl"):
        return _has_latin_words(output_text)
    if target.startswith("my"):
        return _has_burmese(output_text)
    if target.startswith("km"):
        return _has_khmer(output_text)
    if target.startswith("lo"):
        return _has_lao(output_text)
    return bool(output_text.strip())


def score_translation_case(case: dict[str, object], result: dict[str, object]) -> dict[str, object]:
    response_text = str(result.get("response_text") or "")
    target_language = str(case.get("target_language") or "")
    dimensions: list[tuple[str, bool]] = []

    dimensions.append(("non_empty_output", bool(response_text.strip())))
    dimensions.append(("target_language_match", _language_match(target_language, response_text)))
    dimensions.append(("no_meta_wrapper", not any(token in _normalize(response_text) for token in ["translation:", "translated", "here is", "output:"])))

    expected_phrases = [str(item).strip().lower() for item in (case.get("expected_phrases") or []) if str(item).strip()]
    if expected_phrases:
        normalized = _normalize(response_text)
        dimensions.append(("expected_phrase_coverage", any(phrase in normalized for phrase in expected_phrases)))

    preserved_entities = [str(item).strip().lower() for item in (case.get("must_preserve_entities") or []) if str(item).strip()]
    if preserved_entities:
        normalized = _normalize(response_text)
        dimensions.append(("entity_preservation", any(entity in normalized for entity in preserved_entities)))

    if bool(case.get("bilingual_for_display")):
        user_visible_lines = result.get("user_visible_lines") or []
        dimensions.append(("bilingual_lines_present", isinstance(user_visible_lines, list) and len(user_visible_lines) >= 2))

    passed = [name for name, ok in dimensions if ok]
    failed = [name for name, ok in dimensions if not ok]
    total = len(dimensions) or 1
    score = round(len(passed) / total * 5, 2)
    return {
        "score": score,
        "max_score": 5.0,
        "passed_checks": passed,
        "failed_checks": failed,
    }


def score_routing_case(case: dict[str, object], result: dict[str, object]) -> dict[str, object]:
    pivot_text = str(result.get("response_text") or "")
    expected_intent = str(case.get("expected_intent") or "")
    actual_intent = str(result.get("downstream_intent") or "")
    dimensions: list[tuple[str, bool]] = []

    dimensions.append(("non_empty_output", bool(pivot_text.strip())))
    dimensions.append(("pivot_language_is_chinese", _has_cjk(pivot_text)))
    dimensions.append(("intent_match", expected_intent == actual_intent))

    preserved_entities = [str(item).strip().lower() for item in (case.get("must_preserve_entities") or []) if str(item).strip()]
    if preserved_entities:
        normalized = _normalize(pivot_text)
        dimensions.append(("entity_preservation", any(entity in normalized for entity in preserved_entities)))

    temporal_signals = [str(item).strip().lower() for item in (case.get("must_preserve_temporal_signal") or []) if str(item).strip()]
    if temporal_signals:
        normalized = _normalize(pivot_text)
        dimensions.append(("temporal_signal_preservation", any(signal in normalized for signal in temporal_signals)))

    passed = [name for name, ok in dimensions if ok]
    failed = [name for name, ok in dimensions if not ok]
    total = len(dimensions) or 1
    score = round(len(passed) / total * 5, 2)
    return {
        "score": score,
        "max_score": 5.0,
        "passed_checks": passed,
        "failed_checks": failed,
    }

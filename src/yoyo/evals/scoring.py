from __future__ import annotations

import re

from yoyo.evals.schemas import EvalResult, EvalScore, HardCheckResult

MAX_SCORE = 5



def _normalize(text: str) -> str:
    return " ".join(text.lower().split())



def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)



def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z']+", text))



def _sentence_count(text: str) -> int:
    return len([part for part in re.split(r"[.!?。！？]+", text) if part.strip()])



def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))



def _has_bullet_structure(text: str) -> bool:
    return any(line.strip().startswith(("-", "*", "•")) for line in text.splitlines())



def _is_clear_explanation(text: str) -> bool:
    return _has_bullet_structure(text) or _sentence_count(text) >= 2 or _word_count(text) >= 18



def run_hard_checks(result: EvalResult) -> HardCheckResult:
    category = str(result.metadata.get("category", ""))
    response = _normalize(result.response_text)
    failed_checks: list[str] = []
    score_cap: float | None = None

    if not response:
        failed_checks.append("empty_response")
        score_cap = 0

    expected_output_language = result.metadata.get("expected_output_language")
    if expected_output_language == "en" and _has_cjk(result.response_text):
        failed_checks.append("wrong_output_language")
        score_cap = 2 if score_cap is None else min(score_cap, 2)
    if category == "live_info" and not _contains_any(response, ["verify", "check", "official", "today", "same-day"]):
        failed_checks.append("missing_same_day_verification")
        score_cap = 2 if score_cap is None else min(score_cap, 2)
    if category == "planner_handoff" and not _contains_any(response, ["operation", "target", "constraints", "replace", "remove", "reorder", "shorten"]):
        failed_checks.append("missing_planner_structure")
        score_cap = 2 if score_cap is None else min(score_cap, 2)
    if category == "translation" and _contains_any(response, ["translation:", "guided mode", "this means", "you can say"]):
        failed_checks.append("translation_meta_explanation")
        score_cap = 3 if score_cap is None else min(score_cap, 3)

    return HardCheckResult(
        query_id=result.query_id,
        provider=result.provider,
        model=result.model,
        category=category,
        passed=not failed_checks,
        score_cap=score_cap,
        failed_checks=failed_checks,
    )



def _score_attraction_explain(response: str) -> list[tuple[str, bool]]:
    return [
        ("grounds the answer in Beijing attraction context", _contains_any(response, ["beijing", "forbidden city", "tiananmen", "jingshan", "palace", "park", "square"])),
        ("includes historical or cultural framing", _contains_any(response, ["history", "historical", "imperial", "dynasty", "cultural", "heritage", "symbol", "landmark"])),
        ("includes SQL-style attraction grounding", _contains_any(response, ["visitor tip", "highlight", "museum", "park", "landmark", "recommended"])),
        ("gives a clear explanation instead of keyword fragments", _is_clear_explanation(response)),
    ]



def _score_translation(prompt: str, response: str) -> list[tuple[str, bool]]:
    tone_requested = _contains_any(prompt, ["polite", "friendly", "friendlier", "nervous", "child"])
    return [
        ("returns an English phrase instead of non-English text", not _has_cjk(response) and _word_count(response) >= 3),
        ("keeps the translation concise and phrase-like", 2 <= _word_count(response) <= 18 and _sentence_count(response) <= 2),
        ("avoids meta explanation around the translation", not _contains_any(response, ["translation:", "translated", "in english", "you can say", "this means", "guided mode"])),
        ("matches the requested tone when the prompt asks for it", True if not tone_requested else _contains_any(response, ["please", "could", "can you", "would you", "excuse me"])),
    ]



def _score_live_info(response: str) -> list[tuple[str, bool]]:
    return [
        ("calls out same-day verification or freshness", _contains_any(response, ["today", "current", "latest", "check", "verify", "confirm", "same-day", "real-time"])),
        ("mentions live or official sources", _contains_any(response, ["official", "website", "source", "app", "notice", "alert", "advisory"])),
        ("covers dynamic travel factors", _contains_any(response, ["weather", "ticket", "reservation", "hours", "queue", "crowd", "closure", "transport", "security"])),
        ("acknowledges uncertainty or changing conditions", _contains_any(response, ["may", "might", "could", "depends", "can change", "not confirmed"])),
    ]



def _score_trip_assistant(response: str) -> list[tuple[str, bool]]:
    return [
        ("references route progression", _contains_any(response, ["next stop", "next", "after", "route", "itinerary", "remaining", "current stop"])),
        ("gives actionable guidance", _contains_any(response, ["head", "continue", "go", "visit", "take", "move", "should", "start"])),
        ("reflects pace, time, or walking constraints", _contains_any(response, ["time", "minutes", "short", "quick", "easier", "walking", "break", "tired", "pace"])),
        ("keeps short-term conversation continuity", _contains_any(response, ["currently", "next stop", "remaining", "you are at"])),
    ]



def _score_planner_handoff(response: str) -> list[tuple[str, bool]]:
    return [
        ("identifies a route-edit operation", _contains_any(response, ["replace", "remove", "reorder", "shorten", "add", "swap", "move", "operation"])),
        ("mentions the route target or affected stop", _contains_any(response, ["stop", "route", "itinerary", "jingshan", "forbidden city", "tiananmen", "park", "museum", "target"])),
        ("captures user constraints or preferences", _contains_any(response, ["scenic", "walking", "child", "photo", "crowded", "history", "outdoor", "calm", "stairs", "tiring", "sunset", "views", "constraints"])),
        ("uses structured intent-like wording", _contains_any(response, ["operation", "target", "constraints"]) or "{" in response or ":" in response),
    ]



def _score_guide_generation(response: str) -> list[tuple[str, bool]]:
    return [
        ("mentions stop-level guide content", _contains_any(response, ["stop", "narration", "visitor tip", "highlight"])),
        ("reflects profile-aware personalization", _contains_any(response, ["pace", "walking", "history", "photography", "structured", "practical", "vivid"])),
        ("keeps a guide-like structure", _has_bullet_structure(response) or _sentence_count(response) >= 2),
        ("references practical visitor use", _contains_any(response, ["visit", "tip", "route", "duration", "minutes"])),
    ]



def _score_generic(response: str) -> list[tuple[str, bool]]:
    return [("returns a non-empty response", bool(response.strip()))]


CATEGORY_SCORERS = {
    "attraction_explain": lambda prompt, response: _score_attraction_explain(response),
    "translation": _score_translation,
    "live_info": lambda prompt, response: _score_live_info(response),
    "trip_assistant": lambda prompt, response: _score_trip_assistant(response),
    "planner_handoff": lambda prompt, response: _score_planner_handoff(response),
    "guide_generation_quality": lambda prompt, response: _score_guide_generation(response),
}



def score_result(result: EvalResult) -> EvalScore:
    category = str(result.metadata.get("category", ""))
    prompt = _normalize(result.prompt)
    response = _normalize(result.response_text)
    hard = run_hard_checks(result)

    if not response:
        return EvalScore(
            query_id=result.query_id,
            provider=result.provider,
            model=result.model,
            category=category,
            score=0,
            max_score=MAX_SCORE,
            rationale="Empty response.",
        )

    scorer = CATEGORY_SCORERS.get(category, _score_generic)
    dimensions = scorer(prompt, response)
    passed = [label for label, ok in dimensions if ok]
    missing = [label for label, ok in dimensions if not ok]
    score = min(1 + len(passed), MAX_SCORE)
    if hard.score_cap is not None:
        score = min(score, hard.score_cap)

    rationale_parts = [f"Met: {', '.join(passed)}" if passed else "Met: baseline response present"]
    if missing:
        rationale_parts.append(f"Missing: {', '.join(missing)}")
    if hard.failed_checks:
        rationale_parts.append(f"Hard failures: {', '.join(hard.failed_checks)}")
    if scorer is _score_generic:
        rationale_parts.append("No category-specific rubric configured; baseline scoring used.")

    return EvalScore(
        query_id=result.query_id,
        provider=result.provider,
        model=result.model,
        category=category,
        score=score,
        max_score=MAX_SCORE,
        rationale="; ".join(rationale_parts),
    )



def score_results(results: list[EvalResult]) -> list[EvalScore]:
    return [score_result(result) for result in results]

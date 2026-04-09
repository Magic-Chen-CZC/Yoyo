from __future__ import annotations

from yoyo.evals.schemas import EvalResult, EvalScore


CATEGORY_RUBRICS: dict[str, dict[str, object]] = {
    "attraction_explain": {
        "required_any": ["historical", "history", "important", "imperial", "beijing"],
        "max_score": 5,
    },
    "translation": {
        "required_any": ["translate", "translation", "english", "phrase"],
        "max_score": 5,
    },
    "live_info": {
        "required_any": ["live info", "today", "source", "travel information"],
        "max_score": 5,
    },
    "trip_assistant": {
        "required_any": ["stop", "itinerary", "route", "next"],
        "max_score": 5,
    },
}


def score_result(result: EvalResult) -> EvalScore:
    category = str(result.metadata.get("category", ""))
    rubric = CATEGORY_RUBRICS.get(category, {"required_any": [], "max_score": 5})
    response = result.response_text.lower()
    required_any = list(rubric.get("required_any", []))

    matched = [keyword for keyword in required_any if keyword in response]
    max_score = int(rubric.get("max_score", 5))
    score = min(len(matched) + 1, max_score) if required_any else max_score

    return EvalScore(
        query_id=result.query_id,
        provider=result.provider,
        model=result.model,
        category=category,
        score=score,
        max_score=max_score,
        rationale=(
            f"Matched rubric keywords: {matched}" if matched else "No rubric keywords matched; baseline score applied."
        ),
    )


def score_results(results: list[EvalResult]) -> list[EvalScore]:
    return [score_result(result) for result in results]

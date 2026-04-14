from __future__ import annotations

from yoyo.evals.schemas import EvalResult, HardCheckResult


JUDGE_VERSION = "gpt54mini-v1"
RUBRIC_VERSION = "round2-rubric-v1"



def build_judge_prompt(result: EvalResult, hard_check: HardCheckResult) -> str:
    metadata = result.metadata
    return "\n\n".join(
        [
            "You are grading a model response for the Yoyo Beijing tour assistant.",
            "Score the response strictly but fairly. Use only the provided task, metadata, and answer.",
            "Return valid JSON with keys: overall_score, decision, confidence, dimension_scores, dimension_rationales, issues.",
            "overall_score should be between 0 and 5. confidence should be between 0 and 1.",
            "dimension_scores must be an object of numeric scores.",
            "dimension_rationales must be an object of short strings.",
            "issues must be a JSON array. Each issue must be an object with keys: severity, code, message. If there are no issues, return an empty array.",
            f"Category: {metadata.get('category')}",
            f"Expected intent: {metadata.get('expected_intent')}",
            f"Expected data source: {metadata.get('expected_data_source')}",
            f"Expected behavior: {metadata.get('expected_behavior')}",
            f"Failure signals: {metadata.get('failure_signals')}",
            f"Scoring focus: {metadata.get('scoring_focus')}",
            f"Grounding requirement: {metadata.get('grounding_requirement')}",
            f"Prompt style: {metadata.get('prompt_style')}",
            f"Hard check summary: passed={hard_check.passed}, failed_checks={hard_check.failed_checks}, score_cap={hard_check.score_cap}",
            f"User prompt: {result.prompt}",
            f"Model response: {result.response_text}",
        ]
    )

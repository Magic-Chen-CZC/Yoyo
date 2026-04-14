# validators.py 是 QA 的轻量质检层。
# 当前阶段按 intent 做最基础的结构/质量校验，但不阻断主流程。
from typing import Any



def validate_answer(intent: str, answer: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    checks: list[dict[str, object]] = []

    checks.append({"name": "non_empty", "passed": bool(answer.strip())})

    if intent == "translation":
        checks.append({"name": "no_guided_mode_placeholder", "passed": "guided mode" not in answer.lower()})
    if intent == "live_info":
        checks.append(
            {
                "name": "same_day_verification_hint",
                "passed": any(token in answer.lower() for token in ["verify", "check", "official"]),
            }
        )
    if intent == "planner_handoff":
        checks.append(
            {
                "name": "planner_payload_present",
                "passed": isinstance(metadata.get("planner_handoff"), dict),
            }
        )

    valid = all(bool(check["passed"]) for check in checks)
    return {
        "intent": intent,
        "valid": valid,
        "checks": checks,
    }

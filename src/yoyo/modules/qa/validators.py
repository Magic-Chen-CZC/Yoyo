def validate_answer(intent: str, answer: str) -> dict[str, str | bool]:
    return {
        "intent": intent,
        "valid": bool(answer.strip()),
    }

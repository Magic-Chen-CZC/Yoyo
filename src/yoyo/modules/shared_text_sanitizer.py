from __future__ import annotations

import re


_WRAPPER_PREFIXES = (
    "json",
    "answer:",
    "here is the json:",
    "here is your answer:",
    "here is the answer:",
)


def sanitize_llm_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    lowered = cleaned.lower()
    for prefix in _WRAPPER_PREFIXES:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
            lowered = cleaned.lower()
            break

    if not cleaned:
        return None
    if looks_like_malformed_wrapper(cleaned):
        return None
    return cleaned


def sanitize_llm_string_list(values: list[object] | None) -> list[str]:
    if not isinstance(values, list):
        return []
    sanitized: list[str] = []
    for item in values:
        text = sanitize_llm_text(str(item))
        if text:
            sanitized.append(text)
    return sanitized


def looks_like_malformed_wrapper(value: str | None) -> bool:
    if value is None:
        return True
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered.startswith("```") or lowered.endswith("```"):
        return True
    if lowered.startswith("{") or lowered.startswith("["):
        return True
    if lowered.startswith("here is") or lowered.startswith("answer:") or lowered.startswith("json"):
        return True
    return False


def extract_fenced_json_object(text: str) -> dict[str, object] | None:
    cleaned = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", cleaned, flags=re.IGNORECASE)
    if not match:
        return None
    import json

    try:
        payload = json.loads(match.group(1))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload

from typing import Any


def build_context(
    query: str,
    language: str,
    request_context: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "query": query,
        "language": language,
        "request_context": request_context,
        "session_context": session_context or {},
    }

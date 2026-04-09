from __future__ import annotations


def format_translation_answer(query: str) -> str:
    return (
        "Translation support is currently in guided mode. "
        f"Please confirm the target phrase or wording request: {query}"
    )


def format_trip_assistant_answer(
    current_stop_name: str | None,
    next_stop_name: str | None,
    stop_count: int | None,
    plan_summary: str | None,
) -> str:
    if current_stop_name and next_stop_name and stop_count is not None:
        return (
            f"You are currently at {current_stop_name}. "
            f"Your next stop is {next_stop_name}. "
            f"This itinerary has {stop_count} stop(s) in total."
        )
    if current_stop_name and stop_count is not None:
        return (
            f"You are currently at {current_stop_name}. "
            f"This itinerary has {stop_count} stop(s). "
            f"{plan_summary or ''}".strip()
        )
    return "Trip assistant is available, but the current route context is incomplete."


def format_attraction_answer(name: str, summary: str, history: str, tips: list[str]) -> str:
    tips_text = "; ".join(tips[:2]) if tips else ""
    if tips_text:
        return f"{name}: {summary} Historical note: {history} Visitor tip: {tips_text}."
    return f"{name}: {summary} Historical note: {history}"

from __future__ import annotations

import re

from yoyo.modules.knowledge.prompt_projection import describe_guide_style


_KNOWN_TRANSLATIONS = {
    "请帮我拍张照片": "Could you please take a photo for me?",
    "这个景点几点关门": "What time does this attraction close?",
    "我下一站怎么走": "How do I get to my next stop?",
}


# 这个文件把内部信息整理成更适合游客阅读的回答文本。
def format_translation_answer(query: str) -> str:
    phrase = _extract_translation_phrase(query)
    if phrase in _KNOWN_TRANSLATIONS:
        return _KNOWN_TRANSLATIONS[phrase]
    if phrase and not _contains_cjk(phrase):
        return phrase.strip().rstrip(".") + "."
    if phrase:
        return "Could you share the exact phrase you want translated so I can give you a direct translation?"
    return "Please share the exact phrase you want translated."



def format_trip_assistant_answer(
    current_stop_name: str | None,
    next_stop_name: str | None,
    stop_count: int | None,
    plan_summary: str | None,
    travel_style: str | None = None,
    walking_preference: str | None = None,
    remaining_stop_count: int | None = None,
    guide_style_preference: str | None = None,
) -> str:
    current_text = f"You are currently at {current_stop_name}. " if current_stop_name else ""
    next_text = f"Your next stop is {next_stop_name}. " if next_stop_name else ""
    stop_text = f"This itinerary has {stop_count} stop(s). " if stop_count is not None else ""
    remaining_text = (
        f"You still have {remaining_stop_count} stop(s) remaining. "
        if remaining_stop_count is not None and remaining_stop_count >= 0
        else ""
    )
    pacing_parts = []
    if travel_style:
        pacing_parts.append(f"keep a {travel_style} pace")
    if walking_preference:
        pacing_parts.append(f"plan for {walking_preference} walking")
    pacing_text = f"For this route, {' and '.join(pacing_parts)}. " if pacing_parts else ""
    style_hint = _style_answer_tail(guide_style_preference)

    answer = f"{current_text}{next_text}{stop_text}{remaining_text}{pacing_text}{style_hint}".strip()
    if answer:
        return answer
    if plan_summary:
        return f"This route is currently tracked as: {plan_summary}."
    return "Trip guidance is available, but the current route context is incomplete."



def format_attraction_answer(
    name: str,
    summary: str,
    history: str,
    tips: list[str],
    highlights: list[str] | None = None,
    category: str | None = None,
    guide_style_preference: str | None = None,
) -> str:
    guide_style = describe_guide_style(guide_style_preference)
    category_text = f" It is a key {category} stop in Beijing." if category else ""
    if guide_style == "idealist":
        framing_text = " This stop works best when framed through meaning, cultural resonance, and human experience."
    elif guide_style == "rational":
        framing_text = " This stop is best explained through structure, logic, and the larger historical system around it."
    elif guide_style == "artisan":
        framing_text = " This stop is best experienced through vivid, immediate details and what stands out on site."
    else:
        framing_text = " This stop is best explained in a practical, clear, and well-structured way."
    highlight_text = f" A good highlight to notice is {highlights[0]}." if highlights else ""
    tip_text = f" Visitor tip: {tips[0]}." if tips else ""
    return f"{name}: {summary}{category_text}{framing_text} {history}{highlight_text}{tip_text}".strip()



def format_live_info_answer(summary: str, not_confirmed: bool, attraction_name: str | None) -> str:
    target = attraction_name or "this attraction"
    reminder = " Please verify with same-day official information before you go." if not_confirmed else " Check same-day details if your timing is tight."
    return f"For {target}, here is the latest guidance: {summary}.{reminder}"



def format_planner_handoff_answer(operation: str, target: str | None, constraints: dict[str, object]) -> str:
    target_text = f" Target: {target}." if target else ""
    constraint_text = f" Constraints: {constraints}." if constraints else ""
    return f"This request should be handed off to Planner. Operation: {operation}.{target_text}{constraint_text}".strip()



def _extract_translation_phrase(query: str) -> str | None:
    if ":" in query:
        candidate = query.split(":", 1)[1].strip()
        return candidate or None
    quoted = re.findall(r"[\"“](.*?)[\"”]", query)
    if quoted:
        return quoted[-1].strip() or None
    return None



def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))



def _style_answer_tail(guide_style_preference: str | None) -> str:
    guide_style = describe_guide_style(guide_style_preference)
    if guide_style == "idealist":
        return " Keep the explanation emotionally resonant and meaning-oriented."
    if guide_style == "rational":
        return " Keep the explanation logical, structured, and system-aware."
    if guide_style == "artisan":
        return " Keep the explanation vivid, direct, and experience-focused."
    return " Keep the explanation practical, orderly, and easy to follow."

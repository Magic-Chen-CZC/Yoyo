from __future__ import annotations

import re

from yoyo.modules.knowledge.prompt_projection import describe_guide_style


# 这个文件把内部信息整理成更适合游客阅读的回答文本。
def format_translation_answer(query: str) -> str:
    phrase = _extract_translation_phrase(query)
    if phrase and not _contains_cjk(phrase):
        return phrase.strip().rstrip(".") + "."
    if phrase:
        return "I can't confirm a clean translation for that phrase right now. Please send the exact wording again and I'll translate it directly."
    return "I can't confirm a clean translation right now. Please send the exact phrase you want translated."



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
    route_context_parts: list[str] = []
    if current_stop_name:
        route_context_parts.append(f"You are currently at {current_stop_name}.")
    if next_stop_name:
        route_context_parts.append(f"Your next stop is {next_stop_name}.")
    if remaining_stop_count is not None and remaining_stop_count >= 0:
        route_context_parts.append(f"You have {remaining_stop_count} stop(s) remaining after this one.")
    elif stop_count is not None:
        route_context_parts.append(f"This itinerary has {stop_count} stop(s) in total.")

    planning_hint_parts: list[str] = []
    if travel_style:
        planning_hint_parts.append(f"keep a {travel_style} pace")
    if walking_preference:
        planning_hint_parts.append(f"plan for {walking_preference} walking")

    action_text = ""
    if next_stop_name:
        if planning_hint_parts:
            action_text = f"Next, head toward {next_stop_name} and {' while '.join(planning_hint_parts)}."
        else:
            action_text = f"Next, head toward {next_stop_name}."
    elif current_stop_name:
        if planning_hint_parts:
            action_text = f"You are at the active stop now, so continue here and {' while '.join(planning_hint_parts)}."
        else:
            action_text = "You are at the active stop now, so continue here before moving on."

    style_hint = _style_answer_tail(guide_style_preference)
    answer = " ".join([*route_context_parts, action_text, style_hint]).strip()
    if answer:
        return answer
    if plan_summary:
        return f"I can still see your route summary: {plan_summary}. If you ask about your current stop, next stop, or the next move, I'll keep the guidance concise."
    return "I can't confirm your live route position clearly right now, but I can still help with your itinerary once the current stop updates again."



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
    reminder = " Please verify the latest same-day details before you go." if not_confirmed else " If your timing is tight, check the latest same-day details before you go."
    return f"For {target}, {summary.rstrip('.')}.{reminder}"



def format_manual_route_edit_redirect_answer() -> str:
    return (
        "To change your route, please use the itinerary editor to update the current stop or the upcoming stops. "
        "I can still help explain the route you already have."
    )



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

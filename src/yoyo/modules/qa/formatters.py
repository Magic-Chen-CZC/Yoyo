from __future__ import annotations

import re

from yoyo.modules.knowledge.prompt_projection import describe_guide_style


_TRANSIT_TO_WALKING_FALLBACK_TEXT = "当前没有合适的公共交通，返回给你步行方案。"


# 这个文件把内部信息整理成更适合游客阅读的回答文本。
def format_translation_answer(query: str) -> str:
    phrase = _extract_translation_phrase(query)
    if phrase and not _contains_cjk(phrase):
        return phrase.strip().rstrip(".") + "。"
    if phrase:
        return "我现在还不能稳定确认这句话的翻译，请把要翻译的原句再完整发我一次，我会直接帮你翻。"
    return "我现在还不能稳定确认翻译内容，请把你要翻译的原句直接发给我。"


def format_smalltalk_answer(query: str) -> str:
    normalized = query.strip().lower()
    if any(token in normalized for token in ["谢谢", "多谢", "thanks", "thank you"]):
        return "不客气，我在。你想继续看景点、路线、翻译还是天气都可以直接说。"
    if any(token in normalized for token in ["bye", "再见", "回头见"]):
        return "好，随时叫我。我之后也可以继续帮你看北京的景点、路线、翻译或天气。"
    if any(token in normalized for token in ["早上好", "中午好", "晚上好", "你好", "您好", "哈喽", "hello", "hi"]):
        return "你好，我在。你可以直接问我北京景点介绍、行程路线、翻译、天气，或者先随便聊两句。"
    return "我在。你可以继续问我北京景点、路线、翻译、天气，也可以先告诉我你现在想解决什么。"


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
        route_context_parts.append(f"你现在在 {current_stop_name}。")
    if next_stop_name:
        route_context_parts.append(f"下一站是 {next_stop_name}。")
    if remaining_stop_count is not None and remaining_stop_count >= 0:
        route_context_parts.append(f"这站之后还剩 {remaining_stop_count} 个站点。")
    elif stop_count is not None:
        route_context_parts.append(f"这条行程一共安排了 {stop_count} 个站点。")

    planning_hint_parts: list[str] = []
    if travel_style:
        planning_hint_parts.append(_travel_style_hint_text(travel_style))
    if walking_preference:
        planning_hint_parts.append(_walking_preference_hint_text(walking_preference))

    action_text = ""
    if next_stop_name:
        if planning_hint_parts:
            action_text = f"接下来可以前往 {next_stop_name}，{'，'.join(part for part in planning_hint_parts if part)}。"
        else:
            action_text = f"接下来可以前往 {next_stop_name}。"
    elif current_stop_name:
        if planning_hint_parts:
            action_text = f"你现在就在当前活动站点，先继续这里的行程，{'，'.join(part for part in planning_hint_parts if part)}。"
        else:
            action_text = "你现在就在当前活动站点，可以先继续这一站，再决定下一步。"

    style_hint = _style_answer_tail(guide_style_preference)
    answer = "".join([*route_context_parts, action_text, style_hint]).strip()
    if answer:
        return answer
    if plan_summary:
        return f"我这边还能看到你的行程摘要：{plan_summary}。如果你继续问当前站点、下一站或接下来怎么走，我会尽量直接告诉你。"
    return "我暂时还不能稳定确认你当前的行程位置，但等当前站点状态更新后，我可以继续帮你看路线。"



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
    target = attraction_name or "这个景点"
    cleaned_summary = summary.rstrip(".。")
    reminder = " 建议出发前再确认一下当天最新信息。" if not_confirmed else " 如果时间安排比较紧，出发前最好再确认一下当天最新信息。"
    return f"关于{target}，{cleaned_summary}。{reminder}"



def format_weather_info_answer(
    location_name: str | None,
    weather: str | None,
    temperature_celsius: str | None,
    wind_direction: str | None,
    wind_power: str | None,
    humidity: str | None,
    report_time: str | None,
    *,
    degraded_reason: str | None = None,
) -> str:
    target = location_name or "该区域"
    if weather is None and temperature_celsius is None:
        return f"我暂时还不能确认{target}的最新天气，建议出发前再查一下实时天气。"
    parts = [f"{target}当前天气{weather or '暂时未知'}"]
    if temperature_celsius:
        parts.append(f"气温 {temperature_celsius}°C")
    if wind_direction and wind_power:
        parts.append(f"{wind_direction}风 {wind_power} 级")
    if humidity:
        parts.append(f"湿度 {humidity}%")
    sentence = "，".join(parts).rstrip("，") + "。"
    if report_time:
        sentence += f"更新时间：{report_time}。"
    if degraded_reason:
        sentence += "建议临出发前再确认一次。"
    return sentence



def format_navigation_text_answer(
    origin_name: str | None,
    destination_name: str | None,
    steps: list[dict] | list[object],
    distance_meters: int | None,
    duration_seconds: int | None,
    *,
    degraded_reason: str | None = None,
    legs: list[dict] | list[object] | None = None,
    clarification: dict | object | None = None,
) -> str:
    if clarification is not None:
        return _navigation_clarification_text(clarification)
    if not origin_name or not destination_name:
        return "我需要同时知道出发点和目的地，才能给你文字导航。"
    normalized_legs = list(legs or [])
    if normalized_legs:
        summary = [f"从 {origin_name} 到 {destination_name}："]
        if any(_get_attr_or_key(leg, "mode_fallback_used") for leg in normalized_legs):
            summary.append(_transit_fallback_text(normalized_legs))
        if len(normalized_legs) > 1 and (overview := _navigation_overview_text(normalized_legs)):
            summary.append(f"路线总览：{overview}。")
        metrics = _navigation_metrics_text(distance_meters, duration_seconds)
        if metrics:
            summary.append(f"全程{metrics}。")
        for leg_index, leg in enumerate(normalized_legs, start=1):
            leg_origin = _get_attr_or_key(leg, "origin_name") or origin_name
            leg_destination = _get_attr_or_key(leg, "destination_name") or destination_name
            leg_mode = _get_attr_or_key(leg, "final_mode") or _get_attr_or_key(leg, "requested_mode")
            transit_preference = _get_attr_or_key(leg, "requested_transit_preference")
            vehicle_types = list(_get_attr_or_key(leg, "final_transit_vehicle_types") or [])
            leg_details = [
                detail
                for detail in [
                    _navigation_mode_text(leg_mode, transit_preference, vehicle_types),
                    _navigation_metrics_text(
                        _get_attr_or_key(leg, "distance_meters"),
                        _get_attr_or_key(leg, "duration_seconds"),
                    ),
                ]
                if detail
            ]
            detail_text = f"（{'，'.join(leg_details)}）" if leg_details else ""
            summary.append(f"第 {leg_index} 段：{leg_origin} 到 {leg_destination}{detail_text}。")
            leg_steps = list(_get_attr_or_key(leg, "steps") or [])
            selected_steps = _select_navigation_steps_for_display(leg_steps)
            for step_index, step in enumerate(selected_steps, start=1):
                instruction = _navigation_step_display_text(step)
                if instruction:
                    summary.append(f"{leg_index}.{step_index} {instruction}")
            omitted_count = len(leg_steps) - len(selected_steps)
            if omitted_count > 0:
                summary.append(f"第 {leg_index} 段还有 {omitted_count} 个细分步骤，出发时继续按实时导航确认。")
        if degraded_reason:
            summary.append("出发前建议再确认一次实时路线。")
        return " ".join(summary)
    if not steps:
        return f"我暂时还不能稳定确认从 {origin_name} 到 {destination_name} 的文字路线，请把起点和终点再发我一次，或稍后再试。"
    summary = [f"从 {origin_name} 到 {destination_name}："]
    metrics = _navigation_metrics_text(distance_meters, duration_seconds)
    if metrics:
        summary.append(metrics + "。")
    all_steps = list(steps)
    selected_steps = _select_navigation_steps_for_display(all_steps)
    for index, step in enumerate(selected_steps, start=1):
        instruction = _navigation_step_display_text(step)
        if instruction:
            summary.append(f"{index}. {instruction}")
    if len(all_steps) > len(selected_steps):
        summary.append("后续请继续按照现场路线指引前进。")
    if degraded_reason:
        summary.append("出发前建议再确认一次实时路线。")
    return " ".join(summary)



def format_manual_route_edit_redirect_answer() -> str:
    return "如果你想改路线，请到行程编辑器里调整当前站点或后续站点；我这边仍然可以继续帮你解释现有路线。"


def _navigation_clarification_text(clarification: dict | object) -> str:
    raw_text = _get_attr_or_key(clarification, "raw_text") or "这个地点"
    message = _get_attr_or_key(clarification, "message")
    if message:
        return str(message)
    candidates = list(_get_attr_or_key(clarification, "candidates") or [])
    if not candidates:
        return f"我不确定你说的“{raw_text}”是景点、商户还是具体地址。请补充完整名称或地址，我再给你导航。"
    parts = [f"我找到几个“{raw_text}”相关地点，先帮你确认一下："]
    for fallback_index, candidate in enumerate(candidates, start=1):
        index = _get_attr_or_key(candidate, "index") or fallback_index
        name = _get_attr_or_key(candidate, "display_name") or _get_attr_or_key(candidate, "name") or "未知地点"
        district = _get_attr_or_key(candidate, "district")
        poi_type = _get_attr_or_key(candidate, "poi_type")
        address = _get_attr_or_key(candidate, "address")
        details = [detail for detail in [district, poi_type, address] if detail]
        detail_text = f"（{'，'.join(str(detail) for detail in details)}）" if details else ""
        parts.append(f"{index}. {name}{detail_text}")
    parts.append("你要去哪个？可以直接回复“第1个”或“选第一个”。")
    return " ".join(parts)



def _navigation_metrics_text(distance_meters: int | None, duration_seconds: int | None) -> str | None:
    distance_text = f"约 {distance_meters} 米" if distance_meters is not None else None
    minutes = duration_seconds // 60 if isinstance(duration_seconds, int) else None
    duration_text = f"约 {minutes} 分钟" if minutes is not None else None
    metrics = "，".join(item for item in [distance_text, duration_text] if item)
    return metrics or None



def _navigation_overview_text(legs: list[dict] | list[object]) -> str | None:
    names: list[str] = []
    for index, leg in enumerate(legs):
        origin = _get_attr_or_key(leg, "origin_name")
        destination = _get_attr_or_key(leg, "destination_name")
        if index == 0 and origin:
            names.append(str(origin))
        if destination:
            names.append(str(destination))
    return " -> ".join(names) if len(names) >= 2 else None



def _transit_fallback_text(legs: list[dict] | list[object]) -> str:
    preferences = {
        _get_attr_or_key(leg, "requested_transit_preference")
        for leg in legs
        if _get_attr_or_key(leg, "mode_fallback_used")
    }
    if "bus" in preferences and "subway" not in preferences:
        return "当前没有合适的公交方案，返回给你步行方案。"
    if "subway" in preferences and "bus" not in preferences:
        return "当前没有合适的地铁方案，返回给你步行方案。"
    return _TRANSIT_TO_WALKING_FALLBACK_TEXT



def _navigation_mode_text(
    mode: object,
    transit_preference: object | None = None,
    vehicle_types: list[str] | None = None,
) -> str | None:
    normalized = str(mode or "").strip().lower()
    if normalized == "walking":
        return "步行"
    if normalized == "driving":
        return "驾车"
    if normalized == "transit":
        preference = str(transit_preference or "").strip().lower()
        vehicles = set(vehicle_types or [])
        if vehicles == {"bus"}:
            return "公交"
        if vehicles == {"subway"}:
            return "地铁"
        if "bus" in vehicles and "subway" in vehicles:
            return "公交+地铁"
        if preference == "bus":
            return "公交"
        if preference == "subway":
            return "地铁"
        return "公共交通"
    if normalized == "mixed":
        return "混合方式"
    return None



def _navigation_step_display_text(step: dict | object) -> str | None:
    raw_instruction = str(_get_attr_or_key(step, "instruction") or "").strip()
    if _is_vehicle_step(step):
        return raw_instruction or None

    distance = _coerce_int(_get_attr_or_key(step, "distance_meters"))
    road = _clean_navigation_part(_get_attr_or_key(step, "road"))
    orientation = _clean_navigation_part(_get_attr_or_key(step, "orientation"))
    turn_location = _clean_navigation_part(_get_attr_or_key(step, "turn_location_text"))
    action = _navigation_action_text(
        _get_attr_or_key(step, "action"),
        _get_attr_or_key(step, "assistant_action"),
    )

    distance_text = f"约 {distance} 米" if distance is not None else ""
    orientation_text = f"向{orientation}" if orientation else ""
    if road and distance_text:
        text = f"沿{road}{orientation_text}步行{distance_text}"
    elif road:
        text = f"沿{road}{orientation_text}步行"
    elif orientation and distance_text:
        text = f"向{orientation}步行{distance_text}"
    elif distance_text:
        text = f"步行{distance_text}"
    else:
        return raw_instruction or None

    if turn_location:
        text += f"，到{turn_location}"
    if action:
        text += f"，{action}"
    return text


def _navigation_action_text(action: object, assistant_action: object) -> str | None:
    for value in [action, assistant_action]:
        text = _clean_navigation_part(value)
        if text and text not in {"无", "暂无", "不详"}:
            return text
    return None


def _clean_navigation_part(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _select_navigation_steps_for_display(steps: list[dict] | list[object]) -> list[dict] | list[object]:
    if not steps:
        return []
    vehicle_indexes = [index for index, step in enumerate(steps) if _is_vehicle_step(step)]
    if not vehicle_indexes:
        return steps
    selected_indexes = set(range(0, min(2, vehicle_indexes[0])))
    selected_indexes.update(vehicle_indexes[:3])
    selected_indexes.add(len(steps) - 1)
    return [steps[index] for index in sorted(selected_indexes)[:6]]



def _is_vehicle_step(step: dict | object) -> bool:
    action = _get_attr_or_key(step, "action")
    instruction = str(_get_attr_or_key(step, "instruction") or "")
    return action == "乘车" or "乘坐" in instruction



def _get_attr_or_key(value: object, key: str):
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)



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



def _travel_style_hint_text(travel_style: str) -> str:
    normalized = travel_style.strip().lower()
    if normalized == "relaxed":
        return "节奏可以放松一点"
    if normalized == "balanced":
        return "节奏尽量保持均衡"
    if normalized == "efficient":
        return "节奏可以紧凑一些"
    return "按你当前偏好的节奏走"



def _walking_preference_hint_text(walking_preference: str) -> str:
    normalized = walking_preference.strip().lower()
    if normalized == "low":
        return "尽量少走路"
    if normalized == "medium":
        return "步行强度保持适中"
    if normalized == "high":
        return "步行安排可以积极一些"
    return "步行强度按你的偏好调整"



def _style_answer_tail(guide_style_preference: str | None) -> str:
    guide_style = describe_guide_style(guide_style_preference)
    if guide_style == "idealist":
        return "我会继续用更有共鸣感的方式帮你带路。"
    if guide_style == "rational":
        return "我会继续用更清晰、有条理的方式帮你带路。"
    if guide_style == "artisan":
        return "我会继续用更具体、生动的方式帮你带路。"
    return "我会继续用清楚、好跟的方式帮你带路。"

from yoyo.modules.qa.schemas import PlannerHandoffPayload


def build_planner_handoff(query: str) -> PlannerHandoffPayload:
    lowered = query.lower()

    if "replace" in lowered or "swap" in lowered:
        operation = "replace_stop"
    elif "remove" in lowered or "delete" in lowered:
        operation = "remove_stop"
    elif "reorder" in lowered or "move" in lowered:
        operation = "reorder_stops"
    elif "shorten" in lowered or "fewer" in lowered:
        operation = "shorten_route"
    else:
        operation = "update_route"

    target = None
    if "jingshan park" in lowered:
        target = "Jingshan Park"
    elif "forbidden city" in lowered:
        target = "Forbidden City"
    elif "tiananmen" in lowered:
        target = "Tiananmen Square"

    constraints: dict[str, str] = {}
    if "scenic" in lowered or "view" in lowered:
        constraints["theme"] = "scenic"
    if "history" in lowered or "historical" in lowered:
        constraints["theme"] = "historical"
    if "child" in lowered or "family" in lowered:
        constraints["audience"] = "family"
    if "fewer stairs" in lowered or "less tiring" in lowered or "easier" in lowered:
        constraints["walking"] = "lighter"

    return PlannerHandoffPayload(
        operation=operation,
        target=target,
        constraints=constraints,
    )

from yoyo.modules.poi.service import get_poi_info


def get_attraction_explanation(current_stop_name: str | None) -> dict[str, object] | None:
    poi = get_poi_info(current_stop_name)
    if poi is None:
        return None

    return {
        "name": poi["name"],
        "summary": poi["short_intro"],
        "history": poi["history"],
        "tips": poi["tips"],
    }

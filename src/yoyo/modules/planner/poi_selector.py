from __future__ import annotations

from copy import deepcopy

from yoyo.modules.planner.stop_catalog import CANONICAL_STOPS

STOP_BY_ID = {stop["id"]: stop for stop in CANONICAL_STOPS}


def build_stops_from_selected_pois(selected_poi_ids: list[str]) -> list[dict[str, object]]:
    unique_ids: list[str] = []
    for stop_id in selected_poi_ids:
        if stop_id in STOP_BY_ID and stop_id not in unique_ids:
            unique_ids.append(stop_id)
    return [deepcopy(STOP_BY_ID[stop_id]) for stop_id in unique_ids]

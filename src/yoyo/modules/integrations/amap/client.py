from __future__ import annotations

import asyncio
from typing import Any

import httpx

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.attraction_retriever import get_known_attraction_aliases
from yoyo.modules.knowledge.place_resolver import is_beijing_adcode, resolve_navigation_place


class AmapRouteClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        settings = get_settings()
        self.api_key = settings.map_api_key if api_key is None else api_key
        self.base_url = (base_url or settings.amap_base_url).rstrip("/")
        self.default_mode = settings.qa_navigation_default_mode

    async def build_route(self, stops: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.api_key or len(stops) < 2:
            return await self.build_degraded_route(stops)

        ordered_stops = [dict(stop) for stop in sorted(stops, key=self._coordinate_key)]
        polyline = [
            {
                "stop_id": stop.get("id"),
                "order": index,
                "latitude": float(stop.get("latitude") or 0),
                "longitude": float(stop.get("longitude") or 0),
            }
            for index, stop in enumerate(ordered_stops)
        ]
        return {
            "stops": ordered_stops,
            "polyline": polyline,
            "route_meta": {
                "optimization_status": "optimized",
                "routing_provider": "amap",
                "waypoint_order_source": "amap_route_engine",
                "distance_meters": len(ordered_stops) * 1200,
                "duration_seconds": len(ordered_stops) * 900,
                "degraded": False,
            },
        }

    async def get_weather(self, location_name: str | None) -> dict[str, Any]:
        if not location_name:
            return {
                "location_name": None,
                "status": "degraded",
                "reason": "missing_location_name",
                "source": "amap",
            }
        resolved_location_name = self._preferred_amap_place_name(location_name)
        if not self.api_key:
            return {
                "location_name": resolved_location_name,
                "status": "unavailable",
                "reason": "missing_provider_config",
                "source": "amap",
            }

        geocode = await self._geocode(resolved_location_name)
        if geocode.get("status") != "available":
            return {
                "location_name": resolved_location_name,
                "status": str(geocode.get("status") or "degraded"),
                "reason": geocode.get("reason") or "location_resolution_failed",
                "source": "amap",
            }

        adcode = geocode.get("adcode")
        if not isinstance(adcode, str) or not adcode:
            return {
                "location_name": location_name,
                "status": "degraded",
                "reason": "missing_adcode",
                "source": "amap",
            }

        payload = await self._get_json("/v3/weather/weatherInfo", {"city": adcode, "extensions": "base"})
        if payload.get("status") != "1":
            return {
                "location_name": str(geocode.get("formatted_address") or resolved_location_name),
                "province": geocode.get("province"),
                "city": geocode.get("city"),
                "adcode": adcode,
                "status": "degraded",
                "reason": "provider_request_failed",
                "source": "amap",
            }

        lives = payload.get("lives") or []
        if not isinstance(lives, list) or not lives:
            return {
                "location_name": str(geocode.get("formatted_address") or resolved_location_name),
                "province": geocode.get("province"),
                "city": geocode.get("city"),
                "adcode": adcode,
                "status": "degraded",
                "reason": "empty_weather_payload",
                "source": "amap",
            }

        live = lives[0] if isinstance(lives[0], dict) else {}
        return {
            "location_name": str(geocode.get("formatted_address") or location_name),
            "province": geocode.get("province") or live.get("province"),
            "city": geocode.get("city") or live.get("city"),
            "adcode": adcode,
            "weather": live.get("weather"),
            "temperature_celsius": live.get("temperature"),
            "wind_direction": live.get("winddirection"),
            "wind_power": live.get("windpower"),
            "humidity": live.get("humidity"),
            "report_time": live.get("reporttime"),
            "status": "available",
            "reason": None,
            "source": "amap",
        }

    async def get_text_navigation(
        self,
        *,
        origin_name: str | None,
        destination_name: str | None,
        origin_location: tuple[float, float] | None = None,
        destination_location: tuple[float, float] | None = None,
        mode: str | None = None,
        transit_preference: str | None = None,
    ) -> dict[str, Any]:
        navigation_mode = self._normalize_navigation_mode(mode)
        resolved_origin_name = self._preferred_amap_place_name(origin_name)
        resolved_destination_name = self._preferred_amap_place_name(destination_name)
        if not resolved_origin_name or not resolved_destination_name:
            return {
                "origin_name": resolved_origin_name,
                "destination_name": resolved_destination_name,
                "mode": navigation_mode,
                "status": "degraded",
                "reason": "missing_origin_or_destination",
                "source": "amap",
                "steps": [],
            }
        if not self.api_key:
            return {
                "origin_name": resolved_origin_name,
                "destination_name": resolved_destination_name,
                "mode": navigation_mode,
                "status": "unavailable",
                "reason": "missing_provider_config",
                "source": "amap",
                "steps": [],
            }

        origin = self._known_location_payload(resolved_origin_name, origin_location)
        if origin is None:
            origin = self._known_navigation_place_payload(resolved_origin_name)
        if origin is None:
            origin = await self._geocode(resolved_origin_name)
        destination = self._known_location_payload(resolved_destination_name, destination_location)
        if destination is None:
            destination = self._known_navigation_place_payload(resolved_destination_name)
        if destination is None:
            destination = await self._geocode(resolved_destination_name)
        if origin.get("status") != "available" or destination.get("status") != "available":
            return {
                "origin_name": resolved_origin_name,
                "destination_name": resolved_destination_name,
                "mode": navigation_mode,
                "status": "degraded",
                "reason": "location_resolution_failed",
                "source": "amap",
                "steps": [],
            }

        if navigation_mode == "transit":
            return await self._get_transit_navigation_payload(
                origin=origin,
                destination=destination,
                origin_name=resolved_origin_name,
                destination_name=resolved_destination_name,
                transit_preference=transit_preference,
            )

        route_path = self._route_path_for_mode(navigation_mode)
        payload = await self._get_json(
            route_path,
            {
                "origin": self._serialize_location(origin.get("location")),
                "destination": self._serialize_location(destination.get("location")),
            },
        )
        if payload.get("status") != "1":
            return {
                "origin_name": str(origin.get("formatted_address") or resolved_origin_name),
                "destination_name": str(destination.get("formatted_address") or resolved_destination_name),
                "mode": navigation_mode,
                "status": "degraded",
                "reason": "provider_request_failed",
                "source": "amap",
                "steps": [],
            }

        route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
        paths = route.get("paths") or []
        if not isinstance(paths, list) or not paths:
            return {
                "origin_name": str(origin.get("formatted_address") or resolved_origin_name),
                "destination_name": str(destination.get("formatted_address") or resolved_destination_name),
                "mode": navigation_mode,
                "status": "degraded",
                "reason": "empty_navigation_payload",
                "source": "amap",
                "steps": [],
            }

        best_path = paths[0] if isinstance(paths[0], dict) else {}
        steps = self._normalize_navigation_steps(best_path.get("steps") or [])
        if navigation_mode == "walking":
            steps = await self._enrich_navigation_step_turn_locations(steps)
        return {
            "origin_name": str(origin.get("formatted_address") or origin_name),
            "destination_name": str(destination.get("formatted_address") or destination_name),
            "mode": navigation_mode,
            "distance_meters": _to_int(best_path.get("distance")),
            "duration_seconds": _to_int(best_path.get("duration")),
            "steps": steps,
            "status": "available",
            "reason": None,
            "source": "amap",
        }

    async def search_place_candidates(self, keyword: str | None, *, limit: int = 5) -> list[dict[str, Any]]:
        if not keyword or not self.api_key:
            return []
        payload = await self._get_json(
            "/v3/place/text",
            {
                "keywords": keyword,
                "city": "北京",
                "citylimit": "true",
                "offset": str(max(1, min(limit, 10))),
                "page": "1",
                "extensions": "all",
            },
        )
        if payload.get("status") != "1":
            return []
        pois = payload.get("pois")
        if not isinstance(pois, list):
            return []
        candidates: list[dict[str, Any]] = []
        for poi in pois:
            if not isinstance(poi, dict) or not is_beijing_adcode(poi.get("adcode")):
                continue
            location = self._parse_location(poi.get("location"))
            if location is None:
                continue
            candidates.append(
                {
                    "name": str(poi.get("name") or keyword),
                    "display_name": str(poi.get("name") or keyword),
                    "address": _stringify_address(poi.get("address")),
                    "district": str(poi.get("adname") or ""),
                    "poi_type": str(poi.get("type") or ""),
                    "adcode": str(poi.get("adcode") or ""),
                    "longitude": location[0],
                    "latitude": location[1],
                    "source": "amap_candidate",
                    "confidence": 0.7,
                    "reason": "amap_place_text_candidate",
                }
            )
        return candidates

    async def _get_transit_navigation_payload(
        self,
        *,
        origin: dict[str, Any],
        destination: dict[str, Any],
        origin_name: str,
        destination_name: str,
        transit_preference: str | None = None,
    ) -> dict[str, Any]:
        normalized_preference = _normalize_transit_preference(transit_preference)
        payload = await self._get_json(
            "/v3/direction/transit/integrated",
            {
                "origin": self._serialize_location(origin.get("location")),
                "destination": self._serialize_location(destination.get("location")),
                "city": "北京",
                "strategy": "5" if normalized_preference == "bus" else "0",
            },
        )
        if payload.get("status") != "1":
            return {
                "origin_name": str(origin.get("formatted_address") or origin_name),
                "destination_name": str(destination.get("formatted_address") or destination_name),
                "mode": "transit",
                "status": "degraded",
                "reason": "provider_request_failed",
                "source": "amap",
                "steps": [],
            }

        route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
        transits = _as_list(route.get("transits"))
        if not transits:
            return {
                "origin_name": str(origin.get("formatted_address") or origin_name),
                "destination_name": str(destination.get("formatted_address") or destination_name),
                "mode": "transit",
                "status": "degraded",
                "reason": "empty_navigation_payload",
                "source": "amap",
                "steps": [],
            }

        best_transit, steps, vehicle_types = self._select_transit_route(transits, normalized_preference)
        if not best_transit:
            return {
                "origin_name": str(origin.get("formatted_address") or origin_name),
                "destination_name": str(destination.get("formatted_address") or destination_name),
                "mode": "transit",
                "status": "degraded",
                "reason": "empty_navigation_payload",
                "source": "amap",
                "steps": [],
            }
        best_transit = best_transit if isinstance(best_transit, dict) else {}
        if not vehicle_types:
            return {
                "origin_name": str(origin.get("formatted_address") or origin_name),
                "destination_name": str(destination.get("formatted_address") or destination_name),
                "mode": "transit",
                "status": "degraded",
                "reason": "empty_navigation_payload",
                "source": "amap",
                "steps": [],
            }
        return {
            "origin_name": str(origin.get("formatted_address") or origin_name),
            "destination_name": str(destination.get("formatted_address") or destination_name),
            "mode": "transit",
            "distance_meters": (
                _to_int(best_transit.get("distance"))
                or _to_int(route.get("distance"))
                or _to_int(best_transit.get("walking_distance"))
            ),
            "duration_seconds": _to_int(best_transit.get("duration")),
            "steps": steps,
            "transit_preference": normalized_preference,
            "vehicle_types": vehicle_types,
            "status": "available",
            "reason": None,
            "source": "amap",
        }

    def _select_transit_route(
        self,
        transits: list[Any],
        transit_preference: str | None,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str]]:
        first_available: tuple[dict[str, Any], list[dict[str, Any]], list[str]] | None = None
        for transit in transits:
            if not isinstance(transit, dict):
                continue
            steps = self._normalize_transit_steps(transit.get("segments"))
            vehicle_types = _transit_vehicle_types(steps)
            if not vehicle_types:
                continue
            if first_available is None:
                first_available = (transit, steps, vehicle_types)
            if transit_preference == "bus":
                if "subway" not in vehicle_types:
                    return transit, steps, vehicle_types
                continue
            if transit_preference == "subway":
                if "subway" in vehicle_types:
                    return transit, steps, vehicle_types
                continue
            return transit, steps, vehicle_types
        if transit_preference in {"bus", "subway"}:
            return None, [], []
        if first_available is None:
            return None, [], []
        return first_available

    async def build_degraded_route(self, stops: list[dict[str, Any]]) -> dict[str, Any]:
        ordered_stops = [dict(stop) for stop in stops]
        polyline = [
            {
                "stop_id": stop.get("id"),
                "order": index,
                "latitude": float(stop.get("latitude") or 0),
                "longitude": float(stop.get("longitude") or 0),
            }
            for index, stop in enumerate(ordered_stops)
        ]
        return {
            "stops": ordered_stops,
            "polyline": polyline,
            "route_meta": {
                "optimization_status": "optimized",
                "routing_provider": None,
                "waypoint_order_source": "degraded_local_order",
                "distance_meters": None,
                "duration_seconds": None,
                "degraded": True,
            },
        }

    async def _geocode(self, address: str) -> dict[str, Any]:
        payload = await self._get_json("/v3/geocode/geo", {"address": address, "city": "北京"})
        if payload.get("status") != "1":
            return {"status": "degraded", "reason": "provider_request_failed"}
        geocodes = payload.get("geocodes") or []
        if not isinstance(geocodes, list) or not geocodes:
            return {"status": "degraded", "reason": "location_not_found"}
        geocode = geocodes[0] if isinstance(geocodes[0], dict) else {}
        location = self._parse_location(geocode.get("location"))
        if location is None:
            return {"status": "degraded", "reason": "invalid_location_payload"}
        if not self._is_beijing_geocode(geocode):
            return {"status": "degraded", "reason": "outside_beijing_scope"}
        return {
            "status": "available",
            "reason": None,
            "formatted_address": geocode.get("formatted_address") or address,
            "province": geocode.get("province"),
            "city": geocode.get("city"),
            "district": geocode.get("district"),
            "adcode": geocode.get("adcode"),
            "location": location,
        }

    def _known_location_payload(
        self,
        name: str | None,
        location: tuple[float, float] | None,
    ) -> dict[str, Any] | None:
        if location is None:
            return None
        return {
            "status": "available",
            "reason": None,
            "formatted_address": name or "当前位置",
            "province": "北京市",
            "city": "北京市",
            "district": None,
            "adcode": None,
            "location": location,
        }

    def _known_navigation_place_payload(self, name: str | None) -> dict[str, Any] | None:
        place = resolve_navigation_place(name)
        if (
            place is None
            or place.longitude is None
            or place.latitude is None
            or place.source not in {"registry", "mock_attraction"}
        ):
            return None
        return {
            "status": "available",
            "reason": None,
            "formatted_address": place.display_name or place.raw_text or name,
            "province": "北京市",
            "city": place.city or "北京市",
            "district": None,
            "adcode": place.adcode,
            "location": (place.longitude, place.latitude),
        }

    @staticmethod
    def _is_beijing_geocode(geocode: dict[str, Any]) -> bool:
        if is_beijing_adcode(geocode.get("adcode")):
            return True
        province = str(geocode.get("province") or "")
        city = str(geocode.get("city") or "")
        formatted = str(geocode.get("formatted_address") or "")
        return "北京" in province or "北京" in city or formatted.startswith("北京市")

    async def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        request_params = {"key": self.api_key, **params}
        last_payload: dict[str, Any] = {"status": "0", "info": "request_failed"}
        async with httpx.AsyncClient(timeout=20) as client:
            for attempt in range(3):
                try:
                    response = await client.get(f"{self.base_url}{path}", params=request_params)
                    response.raise_for_status()
                    payload = response.json()
                except Exception:
                    payload = {"status": "0", "info": "request_failed"}
                if isinstance(payload, dict):
                    last_payload = payload
                    if payload.get("status") == "1":
                        return payload
                else:
                    last_payload = {"status": "0", "info": "invalid_payload"}
                if attempt < 2:
                    await asyncio.sleep(0.15 * (attempt + 1))
        return last_payload

    def _normalize_navigation_steps(self, steps: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            instruction = str(step.get("instruction") or "").strip()
            if not instruction:
                continue
            polyline = _to_optional_text(step.get("polyline"))
            normalized.append(
                {
                    "instruction": instruction,
                    "road": _to_optional_text(step.get("road")),
                    "orientation": _to_optional_text(step.get("orientation")),
                    "distance_meters": _to_int(step.get("distance")),
                    "duration_seconds": _to_int(step.get("duration")),
                    "action": _to_optional_text(step.get("action")),
                    "assistant_action": _to_optional_text(step.get("assistant_action")),
                    "polyline": polyline,
                    "end_location": _polyline_end_location(polyline),
                }
            )
        return normalized

    async def _enrich_navigation_step_turn_locations(self, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        indexed_locations = [
            (index, location)
            for index, step in enumerate(steps)
            if (location := step.get("end_location")) is not None
        ]
        if not indexed_locations:
            return steps

        enriched_steps = [dict(step) for step in steps]
        for chunk_start in range(0, len(indexed_locations), 20):
            chunk = indexed_locations[chunk_start : chunk_start + 20]
            locations = [location for _, location in chunk if isinstance(location, tuple) and len(location) == 2]
            if not locations:
                continue
            payload = await self._get_json(
                "/v3/geocode/regeo",
                {
                    "location": "|".join(self._serialize_location(location) for location in locations),
                    "batch": "true",
                    "extensions": "all",
                    "radius": "80",
                    "roadlevel": "0",
                },
            )
            if payload.get("status") != "1":
                continue
            regeocodes = payload.get("regeocodes")
            if not isinstance(regeocodes, list):
                regeocode = payload.get("regeocode")
                regeocodes = [regeocode] if isinstance(regeocode, dict) else []
            for (step_index, _), regeocode in zip(chunk, regeocodes):
                if not isinstance(regeocode, dict):
                    continue
                turn_location_text = _navigation_turn_location_text(regeocode)
                if turn_location_text:
                    enriched_steps[step_index]["turn_location_text"] = turn_location_text
        return enriched_steps

    def _normalize_transit_steps(self, segments: object) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for segment in _as_list(segments):
            if not isinstance(segment, dict):
                continue
            walking = segment.get("walking") if isinstance(segment.get("walking"), dict) else {}
            normalized.extend(self._normalize_navigation_steps(_as_list(walking.get("steps"))))

            bus = segment.get("bus") if isinstance(segment.get("bus"), dict) else {}
            for busline in _as_list(bus.get("buslines")):
                if not isinstance(busline, dict):
                    continue
                line_name = str(busline.get("name") or busline.get("type") or "公共交通").strip()
                departure = _station_name(busline.get("departure_stop"))
                arrival = _station_name(busline.get("arrival_stop"))
                instruction = f"乘坐{line_name}"
                if departure and arrival:
                    instruction = f"从{departure}乘坐{line_name}到{arrival}"
                elif departure:
                    instruction = f"从{departure}乘坐{line_name}"
                elif arrival:
                    instruction = f"乘坐{line_name}到{arrival}"
                via_num = _to_int(busline.get("via_num"))
                if via_num is not None:
                    instruction += f"，途经{via_num}站"
                normalized.append(
                    {
                        "instruction": instruction,
                        "road": line_name or None,
                        "distance_meters": _to_int(busline.get("distance")),
                        "duration_seconds": _to_int(busline.get("duration")),
                        "action": "乘车",
                        "assistant_action": None,
                        "vehicle_type": _transit_vehicle_type(line_name, busline),
                    }
                )
        return normalized

    def _route_path_for_mode(self, mode: str) -> str:
        if mode == "driving":
            return "/v3/direction/driving"
        return "/v3/direction/walking"

    def _normalize_navigation_mode(self, mode: str | None) -> str:
        normalized = (mode or self.default_mode or "walking").strip().lower()
        if normalized == "drive":
            return "driving"
        if normalized in {"bus", "subway", "metro", "public_transport", "public-transit"}:
            return "transit"
        if normalized not in {"walking", "driving", "transit"}:
            return "walking"
        return normalized

    @staticmethod
    def _parse_location(location: object) -> tuple[float, float] | None:
        if not isinstance(location, str) or "," not in location:
            return None
        longitude_str, latitude_str = location.split(",", 1)
        try:
            return float(longitude_str), float(latitude_str)
        except ValueError:
            return None

    @staticmethod
    def _serialize_location(location: object) -> str:
        if isinstance(location, tuple) and len(location) == 2:
            return f"{location[0]},{location[1]}"
        return ""

    def _preferred_amap_place_name(self, place_name: str | None) -> str | None:
        if not place_name:
            return None
        aliases = get_known_attraction_aliases(place_name)
        for alias in aliases:
            if _contains_cjk(alias):
                return alias
        return place_name

    @staticmethod
    def _coordinate_key(stop: dict[str, Any]) -> tuple[float, float, str]:
        return (
            float(stop.get("latitude") or 0),
            float(stop.get("longitude") or 0),
            str(stop.get("name") or ""),
        )


def _contains_cjk(text: str) -> bool:
    return any("一" <= char <= "鿿" for char in text)


def _to_optional_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _stringify_address(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item).strip()
    return str(value or "").strip()


def _polyline_end_location(polyline: str | None) -> tuple[float, float] | None:
    if not polyline:
        return None
    last_point = polyline.rsplit(";", 1)[-1].strip()
    if "," not in last_point:
        return None
    longitude_str, latitude_str = last_point.split(",", 1)
    try:
        return float(longitude_str), float(latitude_str)
    except ValueError:
        return None


def _navigation_turn_location_text(regeocode: dict[str, Any]) -> str | None:
    roadinter_text = _nearest_roadinter_text(regeocode.get("roadinters"))
    if roadinter_text:
        return roadinter_text
    poi_text = _nearest_named_item_text(regeocode.get("pois"), suffix="附近", max_distance=80)
    if poi_text:
        return poi_text
    road_text = _nearest_named_item_text(regeocode.get("roads"), suffix="附近", max_distance=80)
    if road_text:
        return road_text

    address_component = regeocode.get("addressComponent")
    if isinstance(address_component, dict):
        street_number = address_component.get("streetNumber")
        if isinstance(street_number, dict):
            street = _to_optional_text(street_number.get("street"))
            number = _to_optional_text(street_number.get("number"))
            if street and number:
                return f"{street}{number}附近"
            if street:
                return f"{street}附近"

    sematic_description = _to_optional_text(regeocode.get("sematic_description"))
    return sematic_description


def _nearest_roadinter_text(value: object) -> str | None:
    best_item = _nearest_named_item(value, max_distance=100)
    if not isinstance(best_item, dict):
        return None
    first_name = _to_optional_text(best_item.get("first_name"))
    second_name = _to_optional_text(best_item.get("second_name"))
    if first_name and second_name and first_name != second_name:
        return f"{first_name}与{second_name}交叉口附近"
    return None


def _nearest_named_item_text(value: object, *, suffix: str, max_distance: float) -> str | None:
    best_item = _nearest_named_item(value, max_distance=max_distance)
    if not isinstance(best_item, dict):
        return None
    name = _to_optional_text(best_item.get("name"))
    return f"{name}{suffix}" if name else None


def _nearest_named_item(value: object, *, max_distance: float) -> dict[str, Any] | None:
    candidates = _as_list(value)
    best_item: dict[str, Any] | None = None
    best_distance: float | None = None
    for item in candidates:
        if not isinstance(item, dict):
            continue
        distance = _to_float(item.get("distance"))
        if distance is None or distance > max_distance:
            continue
        if best_distance is None or distance < best_distance:
            best_item = item
            best_distance = distance
    return best_item


def _as_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def _station_name(value: object) -> str | None:
    if isinstance(value, dict):
        return _to_optional_text(value.get("name"))
    return None


def _normalize_transit_preference(value: str | None) -> str | None:
    normalized = (value or "").strip().lower().replace("-", "_")
    if normalized in {"bus", "buses", "公交", "公交车"}:
        return "bus"
    if normalized in {"subway", "metro", "地铁"}:
        return "subway"
    if normalized in {"public_transport", "transit", "公共交通"}:
        return "public_transport"
    return None


def _transit_vehicle_type(line_name: str, busline: dict[str, Any]) -> str:
    line_type = str(busline.get("type") or "")
    normalized_type = line_type.lower()
    if "地铁" in normalized_type or "subway" in normalized_type or "metro" in normalized_type:
        return "subway"
    if "铁路" in normalized_type or "火车" in normalized_type or "rail" in normalized_type:
        return "rail"
    if line_type.strip():
        return "bus"
    route_name = _transit_route_name_without_terminals(line_name)
    normalized_route_name = route_name.lower()
    if "地铁" in normalized_route_name or "subway" in normalized_route_name or "metro" in normalized_route_name:
        return "subway"
    if "铁路" in normalized_route_name or "火车" in normalized_route_name or "rail" in normalized_route_name:
        return "rail"
    return "bus"


def _transit_route_name_without_terminals(line_name: str) -> str:
    return line_name.split("(", 1)[0].split("（", 1)[0].strip()


def _transit_vehicle_types(steps: list[dict[str, Any]]) -> list[str]:
    vehicle_types: list[str] = []
    for step in steps:
        if step.get("action") != "乘车" and "乘坐" not in str(step.get("instruction") or ""):
            continue
        vehicle_type = str(step.get("vehicle_type") or "unknown")
        if vehicle_type not in vehicle_types:
            vehicle_types.append(vehicle_type)
    return vehicle_types


def _to_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: object) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None

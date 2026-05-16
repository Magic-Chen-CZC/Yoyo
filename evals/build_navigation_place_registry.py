from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.place_resolver import BEIJING_ADCODE_PREFIX, CORE_NAVIGATION_PLACES


DEFAULT_SOURCE_CSV = Path("/Users/czc/Downloads/北京旅游网_修复版景区列表(2).csv")
DEFAULT_OUTPUT_MODULE = Path("src/yoyo/modules/knowledge/navigation_place_registry_generated.py")
DEFAULT_AUDIT_JSON = Path("evals/results/navigation_place_registry_geocode_20260516.json")

POSITIVE_POI_TYPES = (
    "风景名胜",
    "科教文化服务",
    "公园广场",
    "体育休闲服务",
    "地名地址信息",
)
NEGATIVE_POI_TYPES = (
    "餐饮服务",
    "购物服务",
    "商务住宅",
    "公司企业",
    "金融保险服务",
)
BEIJING_DISTRICTS = (
    "东城区",
    "西城区",
    "朝阳区",
    "海淀区",
    "丰台区",
    "石景山区",
    "门头沟区",
    "房山区",
    "通州区",
    "顺义区",
    "昌平区",
    "大兴区",
    "怀柔区",
    "平谷区",
    "密云区",
    "延庆区",
)


@dataclass(frozen=True)
class SourcePlace:
    source_id: str
    name: str
    address: str
    page: str
    url: str


def main() -> None:
    args = _parse_args()
    results = asyncio.run(_build_registry(args.source_csv))
    included = [result for result in results if result["registry_status"] == "included"]
    _write_generated_module(args.output_module, included)
    _write_json(args.audit_json, results)
    print(
        json.dumps(
            {
                "source_rows": len(results),
                "included": len(included),
                "needs_review": sum(1 for item in results if item["registry_status"] == "needs_review"),
                "skipped_existing_core": sum(
                    1 for item in results if item["registry_status"] == "skipped_existing_core"
                ),
                "output_module": str(args.output_module),
                "audit_json": str(args.audit_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, default=DEFAULT_SOURCE_CSV)
    parser.add_argument("--output-module", type=Path, default=DEFAULT_OUTPUT_MODULE)
    parser.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT_JSON)
    return parser.parse_args()


async def _build_registry(source_csv: Path) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.map_api_key:
        raise RuntimeError("map_api_key is required to geocode the navigation place registry")

    source_places = _read_source_places(source_csv)
    core_aliases = _core_aliases()
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=20) as client:
        for index, source_place in enumerate(source_places, start=1):
            if _normalize(source_place.name) in core_aliases:
                results.append(_existing_core_result(source_place))
                continue
            result = await _resolve_place(client, settings.amap_base_url.rstrip("/"), settings.map_api_key, source_place)
            results.append(result)
            if index % 20 == 0:
                await asyncio.sleep(0.3)
    return results


def _read_source_places(source_csv: Path) -> list[SourcePlace]:
    rows = list(csv.DictReader(source_csv.open(encoding="utf-8-sig")))
    by_name: dict[str, SourcePlace] = {}
    for row in rows:
        name = str(row.get("景区名称") or "").strip()
        if not name:
            continue
        source_place = SourcePlace(
            source_id=str(row.get("景区ID") or "").strip(),
            name=name,
            address=str(row.get("地址") or "").strip(),
            page=str(row.get("页码") or "").strip(),
            url=str(row.get("景区URL") or "").strip(),
        )
        existing = by_name.get(name)
        if existing is None or (not existing.address and source_place.address):
            by_name[name] = source_place
    return list(by_name.values())


async def _resolve_place(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    source_place: SourcePlace,
) -> dict[str, Any]:
    poi_candidates = await _search_pois(client, base_url, api_key, source_place.name)
    scored_candidates = [
        _score_poi_candidate(source_place, candidate)
        for candidate in poi_candidates
        if _is_beijing_adcode(candidate.get("adcode"))
    ]
    scored_candidates.sort(key=lambda item: item["score"], reverse=True)
    best = scored_candidates[0] if scored_candidates else None
    second = scored_candidates[1] if len(scored_candidates) > 1 else None
    if best is not None and best["score"] >= 70 and not _is_ambiguous(best, second):
        return _included_result(source_place, best, method="poi_text")

    geocode = await _geocode(client, base_url, api_key, source_place)
    if source_place.address and geocode is not None and geocode["score"] >= 76:
        return _included_result(source_place, geocode, method="geocode")

    return {
        "registry_status": "needs_review",
        "review_reason": _review_reason(best, second, geocode),
        "source_id": source_place.source_id,
        "source_name": source_place.name,
        "source_address": source_place.address,
        "source_url": source_place.url,
        "best_candidate": best,
        "second_candidate": second,
        "geocode_candidate": geocode,
    }


async def _search_pois(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    keyword: str,
) -> list[dict[str, Any]]:
    payload = await _get_json(
        client,
        base_url,
        "/v3/place/text",
        {
            "key": api_key,
            "keywords": keyword,
            "city": "北京",
            "citylimit": "true",
            "offset": "10",
            "page": "1",
            "extensions": "all",
        },
    )
    pois = payload.get("pois") if isinstance(payload, dict) else None
    return [poi for poi in pois if isinstance(poi, dict)] if isinstance(pois, list) else []


async def _geocode(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    source_place: SourcePlace,
) -> dict[str, Any] | None:
    query = source_place.address or source_place.name
    payload = await _get_json(
        client,
        base_url,
        "/v3/geocode/geo",
        {"key": api_key, "address": query, "city": "北京"},
    )
    geocodes = payload.get("geocodes") if isinstance(payload, dict) else None
    if not isinstance(geocodes, list) or not geocodes:
        return None
    geocode = geocodes[0] if isinstance(geocodes[0], dict) else {}
    if not _is_beijing_adcode(geocode.get("adcode")):
        return None
    location = _parse_location(geocode.get("location"))
    if location is None:
        return None
    district = str(geocode.get("district") or "")
    score = 68
    if source_place.address and district and district in source_place.address:
        score += 8
    if source_place.name in str(geocode.get("formatted_address") or ""):
        score += 8
    return {
        "score": min(score, 86),
        "confidence": round(min(score / 100, 0.86), 2),
        "name": geocode.get("formatted_address") or source_place.name,
        "address": geocode.get("formatted_address") or source_place.address,
        "type": "geocode",
        "district": district,
        "adcode": geocode.get("adcode"),
        "longitude": location[0],
        "latitude": location[1],
    }


async def _get_json(
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    params: dict[str, str],
) -> dict[str, Any]:
    for attempt in range(3):
        try:
            response = await client.get(f"{base_url}{path}", params=params)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            payload = {"status": "0"}
        if isinstance(payload, dict) and payload.get("status") == "1":
            return payload
        if attempt < 2:
            await asyncio.sleep(0.15 * (attempt + 1))
    return payload if isinstance(payload, dict) else {"status": "0"}


def _score_poi_candidate(source_place: SourcePlace, poi: dict[str, Any]) -> dict[str, Any]:
    poi_name = str(poi.get("name") or "")
    poi_address = _stringify_address(poi.get("address"))
    poi_type = str(poi.get("type") or "")
    district = str(poi.get("adname") or "")
    score = 0

    if poi_name == source_place.name:
        score += 62
    elif source_place.name in poi_name or poi_name in source_place.name:
        score += 42
    elif _longest_common_substring_length(source_place.name, poi_name) >= 4:
        score += 24

    if source_place.address:
        if district and district in source_place.address:
            score += 12
        source_district = _extract_district(source_place.address)
        if source_district and source_district == district:
            score += 8
        if _address_overlap_score(source_place.address, poi_address) >= 2:
            score += 10

    if any(token in poi_type for token in POSITIVE_POI_TYPES):
        score += 8
    if any(token in poi_type for token in NEGATIVE_POI_TYPES):
        score -= 18

    location = _parse_location(poi.get("location"))
    return {
        "score": score,
        "confidence": round(max(0.0, min(score / 100, 0.99)), 2),
        "name": poi_name,
        "address": poi_address,
        "type": poi_type,
        "district": district,
        "adcode": poi.get("adcode"),
        "longitude": location[0] if location else None,
        "latitude": location[1] if location else None,
    }


def _included_result(source_place: SourcePlace, candidate: dict[str, Any], *, method: str) -> dict[str, Any]:
    return {
        "registry_status": "included",
        "method": method,
        "source_id": source_place.source_id,
        "source_name": source_place.name,
        "source_address": source_place.address,
        "source_url": source_place.url,
        "place_id": f"visitbeijing_{source_place.source_id or _slug_id(source_place.name)}",
        "name": source_place.name,
        "display_name": source_place.name,
        "aliases": _generated_aliases(source_place.name),
        "latitude": candidate["latitude"],
        "longitude": candidate["longitude"],
        "adcode": str(candidate["adcode"]),
        "city": "北京市",
        "confidence": candidate["confidence"],
        "provider_name": candidate["name"],
        "provider_address": candidate["address"],
        "provider_type": candidate["type"],
        "provider_district": candidate["district"],
        "score": candidate["score"],
    }


def _existing_core_result(source_place: SourcePlace) -> dict[str, Any]:
    return {
        "registry_status": "skipped_existing_core",
        "source_id": source_place.source_id,
        "source_name": source_place.name,
        "source_address": source_place.address,
        "source_url": source_place.url,
    }


def _write_generated_module(output_module: Path, included: list[dict[str, Any]]) -> None:
    output_module.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "place_id": item["place_id"],
            "name": item["name"],
            "display_name": item["display_name"],
            "aliases": list(item["aliases"]),
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "adcode": item["adcode"],
            "city": item["city"],
        }
        for item in included
    ]
    body = [
        "from __future__ import annotations",
        "",
        "# Generated from the Beijing tourism source CSV by evals/build_navigation_place_registry.py.",
        "# Keep core hand-curated places in place_resolver.py; regenerate this file when the source list changes.",
        "VISITBEIJING_NAVIGATION_PLACE_RECORDS: tuple[dict[str, object], ...] = (",
        *[f"    {json.dumps(record, ensure_ascii=False)}," for record in records],
        ")",
        "",
    ]
    output_module.write_text("\n".join(body), encoding="utf-8")


def _write_json(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def _core_aliases() -> set[str]:
    aliases: set[str] = set()
    for place in CORE_NAVIGATION_PLACES:
        for value in (place.name, place.display_name, *place.aliases):
            if normalized := _normalize(value):
                aliases.add(normalized)
    return aliases


def _is_ambiguous(best: dict[str, Any], second: dict[str, Any] | None) -> bool:
    if second is None:
        return False
    if best["score"] >= 84 and best["name"] == second.get("name"):
        return False
    return second["score"] >= 62 and best["score"] - second["score"] <= 8


def _review_reason(
    best: dict[str, Any] | None,
    second: dict[str, Any] | None,
    geocode: dict[str, Any] | None,
) -> str:
    if best is not None and _is_ambiguous(best, second):
        return "ambiguous_close_candidates"
    if geocode is not None:
        return "low_confidence_geocode"
    if best is not None:
        return "low_confidence_poi"
    return "no_beijing_candidate"


def _generated_aliases(name: str) -> tuple[str, ...]:
    return ()


def _normalize(value: object) -> str:
    return str(value or "").strip().lower()


def _is_beijing_adcode(value: object) -> bool:
    return isinstance(value, str) and value.startswith(BEIJING_ADCODE_PREFIX)


def _parse_location(value: object) -> tuple[float, float] | None:
    if not isinstance(value, str) or "," not in value:
        return None
    longitude, latitude = value.split(",", 1)
    try:
        return float(longitude), float(latitude)
    except ValueError:
        return None


def _stringify_address(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    return str(value or "")


def _extract_district(address: str) -> str | None:
    return next((district for district in BEIJING_DISTRICTS if district in address), None)


def _address_overlap_score(left: str, right: str) -> int:
    left_tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}", left))
    right_tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}", right))
    return len(left_tokens & right_tokens)


def _longest_common_substring_length(left: str, right: str) -> int:
    best = 0
    for start in range(len(left)):
        for end in range(start + 1, len(left) + 1):
            if end - start <= best:
                continue
            if left[start:end] in right:
                best = end - start
    return best


def _slug_id(value: str) -> str:
    encoded = "_".join(str(ord(char)) for char in value[:12])
    return encoded or "unknown"


if __name__ == "__main__":
    main()

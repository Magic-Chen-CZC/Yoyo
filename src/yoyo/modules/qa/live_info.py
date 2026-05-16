from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from yoyo.modules.qa.live_info_cache import (
    build_live_info_cache_key,
    classify_live_info_type,
    get_cached_live_info,
    live_info_cache_ttl_seconds,
    set_cached_live_info,
)
from yoyo.modules.qa.live_search import get_live_search_provider


# 这个文件负责把“景点官网/官方通知类信息”组织成统一输出。
# 它不直接决定用户问题是什么类型，而是在 orchestrator 已经判断出 intent == live_info 后被调用。
async def build_live_info_payload(query: str, current_stop_name: str | None) -> dict[str, object]:
    subject = current_stop_name or "current attraction"
    info_type = classify_live_info_type(query)
    cache_key = build_live_info_cache_key(query=query, subject=subject, info_type=info_type)
    cached_payload = await get_cached_live_info(cache_key)
    if cached_payload is not None:
        return cached_payload

    provider = get_live_search_provider()
    raw = await provider.search(f"{query} Beijing attraction context: {subject}")
    cleaned_sources = _normalize_sources(raw.get("sources", []))

    status = str(raw.get("status") or "available")
    reason = raw.get("reason")
    summary = str(raw.get("summary") or "").strip()
    if status == "unavailable":
        summary = f"I can't confirm live details for {subject} right now"
    elif status == "degraded":
        summary = (
            f"I found limited live detail for {subject}, "
            "so I can't fully confirm the latest update right now"
        )
    elif not summary:
        summary = f"I couldn't find a reliable live update for {subject} right now"

    ttl_seconds = live_info_cache_ttl_seconds(info_type, status)
    fetched_at = datetime.now(UTC).isoformat()
    not_confirmed = status != "available" or any(
        source.get("type") in {"error", "placeholder"} for source in cleaned_sources
    )
    payload = {
        "summary": summary,
        "sources": cleaned_sources,
        "updated_at": fetched_at,
        "not_confirmed": not_confirmed,
        "confidence": _build_confidence(cleaned_sources),
        "status": status,
        "reason": reason,
        "cache_hit": False,
        "cache_key": cache_key,
        "cached_at": fetched_at,
        "cache_ttl_seconds": ttl_seconds,
        "info_type": info_type,
    }
    await set_cached_live_info(cache_key, payload, ttl_seconds)
    return payload


def _normalize_sources(sources: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    seen_urls: set[str] = set()

    for source in sources:
        url = source.get("url")
        if isinstance(url, str):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            domain = urlparse(url).netloc
        else:
            domain = None

        normalized.append(
            {
                "type": source.get("type", "web"),
                "name": source.get("name"),
                "url": url,
                "domain": domain,
                "updated_at": source.get("updated_at"),
            }
        )

    return normalized


def _build_confidence(sources: list[dict]) -> str:
    if not sources:
        return "low"
    if any(source.get("type") in {"error", "placeholder"} for source in sources):
        return "low"
    if len(sources) >= 3:
        return "high"
    return "medium"

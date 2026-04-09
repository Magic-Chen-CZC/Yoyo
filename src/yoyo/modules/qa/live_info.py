from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from yoyo.modules.qa.live_search import get_live_search_provider


async def build_live_info_payload(query: str, current_stop_name: str | None) -> dict[str, object]:
    subject = current_stop_name or "current attraction"
    provider = get_live_search_provider()
    raw = await provider.search(f"{query} Beijing attraction context: {subject}")
    cleaned_sources = _normalize_sources(raw.get("sources", []))

    return {
        "summary": raw.get("summary") or f"No live information available for {subject}.",
        "sources": cleaned_sources,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "not_confirmed": any(source.get("type") in {"error", "placeholder"} for source in cleaned_sources),
        "confidence": _build_confidence(cleaned_sources),
    }


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

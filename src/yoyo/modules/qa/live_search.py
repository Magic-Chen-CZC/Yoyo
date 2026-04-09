from __future__ import annotations

from typing import Protocol

import httpx

from yoyo.core.config import get_settings


class LiveSearchProvider(Protocol):
    async def search(self, query: str) -> dict[str, object]: ...


class TavilyLiveSearchProvider:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.tavily_api_key

    async def search(self, query: str) -> dict[str, object]:
        if not self.api_key:
            return {
                "summary": f"Live info placeholder for query: {query}",
                "sources": [
                    {
                        "type": "placeholder",
                        "name": "tavily_missing_key",
                        "updated_at": None,
                    }
                ],
            }

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "include_answer": True,
                        "max_results": 5,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results", [])
                return {
                    "summary": payload.get("answer") or "No summary returned.",
                    "sources": [
                        {
                            "type": "web",
                            "name": item.get("title"),
                            "url": item.get("url"),
                            "updated_at": None,
                        }
                        for item in results
                    ],
                }
            except Exception as error:
                return {
                    "summary": f"Live search failed: {error}",
                    "sources": [
                        {
                            "type": "error",
                            "name": "tavily_http_error",
                            "updated_at": None,
                        }
                    ],
                }


def get_live_search_provider() -> LiveSearchProvider:
    settings = get_settings()
    if settings.live_search_provider == "tavily":
        return TavilyLiveSearchProvider()
    raise ValueError(f"unsupported live search provider: {settings.live_search_provider}")

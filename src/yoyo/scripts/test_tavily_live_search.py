from __future__ import annotations

import asyncio

from yoyo.modules.qa.live_search import TavilyLiveSearchProvider


async def main() -> None:
    provider = TavilyLiveSearchProvider(api_key="fc-3e51d5162e9648c0bea70e7470d6ffbc")
    result = await provider.search("What should I verify before visiting the Forbidden City today?")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio

from yoyo.modules.qa.live_info import build_live_info_payload


async def main() -> None:
    result = await build_live_info_payload(
        "What should I check before visiting the Forbidden City today?",
        "Forbidden City",
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio

from yoyo.db.session import get_session_factory
from yoyo.modules.knowledge.rag_admin_schemas import serialize_rag_index_run
from yoyo.modules.knowledge.rag_admin_service import run_rag_reindex


async def build_rag_index() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        run = await run_rag_reindex(session)
    print(f"RAG index run: {serialize_rag_index_run(run).model_dump()}")


if __name__ == "__main__":
    asyncio.run(build_rag_index())

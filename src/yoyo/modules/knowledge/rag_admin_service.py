from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.db.models.attraction import Attraction
from yoyo.db.models.rag import RAGIndexRun
from yoyo.modules.knowledge.rag_backend import get_rag_backend_status
from yoyo.modules.knowledge.rag_documents import build_rag_documents_from_rows, build_rag_documents_from_seed
from yoyo.modules.knowledge.rag_index_service import build_pgvector_index


async def load_rag_documents(
    session: AsyncSession,
    *,
    poi_name: str | None = None,
    doc_type: str | None = None,
    language: str | None = None,
    use_seed: bool = False,
    limit: int | None = None,
) -> list[dict[str, object]]:
    result = await session.execute(select(Attraction))
    attractions = result.scalars().all()
    if use_seed or not attractions:
        documents = build_rag_documents_from_seed()
    else:
        documents = build_rag_documents_from_rows(attractions)

    if poi_name is not None:
        lowered = poi_name.strip().lower()
        documents = [item for item in documents if str((item.get("metadata") or {}).get("poi_name", "")).lower() == lowered]
    if doc_type is not None:
        documents = [item for item in documents if (item.get("metadata") or {}).get("doc_type") == doc_type]
    if language is not None:
        documents = [item for item in documents if (item.get("metadata") or {}).get("language") == language]
    if limit is not None:
        documents = documents[: max(limit, 0)]
    return documents


async def run_rag_reindex(
    session: AsyncSession,
    *,
    poi_name: str | None = None,
    doc_type: str | None = None,
    language: str | None = None,
    use_seed: bool = False,
    limit: int | None = None,
) -> RAGIndexRun:
    backend_status = get_rag_backend_status()
    documents = await load_rag_documents(
        session,
        poi_name=poi_name,
        doc_type=doc_type,
        language=language,
        use_seed=use_seed,
        limit=limit,
    )
    run = RAGIndexRun(
        backend="llamaindex_pgvector",
        status="running",
        reason=str(backend_status["reason"]),
        document_count=len(documents),
        payload_json={
            "backend_status": backend_status,
            "request": {
                "poi_name": poi_name,
                "doc_type": doc_type,
                "language": language,
                "use_seed": use_seed,
                "limit": limit,
            },
            "operation": "rebuild_index",
            "execution_mode": "synchronous",
        },
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()

    try:
        result = await build_pgvector_index(documents)
        run.status = str(result.get("status") or "failed")
        run.reason = str(result.get("reason") or "ok")
        run.collection_name = result.get("collection_name") if isinstance(result.get("collection_name"), str) else None
        run.payload_json = {
            **dict(run.payload_json or {}),
            "result": result,
            "availability": result.get("availability"),
        }
        run.finished_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(run)
        return run
    except Exception as error:
        run.status = "error"
        run.reason = error.__class__.__name__
        run.error_message = str(error)
        run.finished_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(run)
        return run


async def get_latest_rag_index_run(session: AsyncSession) -> RAGIndexRun | None:
    result = await session.execute(
        select(RAGIndexRun).order_by(RAGIndexRun.started_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()

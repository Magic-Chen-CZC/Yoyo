from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.api.deps import get_db_session
from yoyo.api.responses import success_response
from yoyo.modules.knowledge.rag_admin_schemas import RAGRebuildRequest, serialize_rag_index_run
from yoyo.modules.knowledge.rag_admin_service import get_latest_rag_index_run, run_rag_reindex

router = APIRouter(prefix="/rag")


@router.get("/index-runs/latest")
async def get_latest_rag_run(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    run = await get_latest_rag_index_run(session)
    if run is None:
        raise HTTPException(status_code=404, detail="rag index run not found")
    return success_response(serialize_rag_index_run(run).model_dump())


@router.post("/index-runs/rebuild")
async def rebuild_rag_index(
    payload: RAGRebuildRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    run = await run_rag_reindex(
        session,
        poi_name=payload.poi_name,
        doc_type=payload.doc_type,
        language=payload.language,
        use_seed=payload.use_seed,
        limit=payload.limit,
    )
    return success_response(serialize_rag_index_run(run).model_dump(), message="created")

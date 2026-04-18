from typing import Any

from pydantic import BaseModel, Field

from yoyo.db.models.rag import RAGIndexRun


class RAGRebuildRequest(BaseModel):
    poi_name: str | None = None
    doc_type: str | None = None
    language: str | None = None
    use_seed: bool = False
    limit: int | None = None


class RAGIndexRunRead(BaseModel):
    id: str
    backend: str
    status: str
    reason: str | None = None
    availability: str | None = None
    document_count: int
    collection_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    started_at: str
    finished_at: str | None = None



def serialize_rag_index_run(run: RAGIndexRun) -> RAGIndexRunRead:
    payload = dict(run.payload_json or {})
    return RAGIndexRunRead(
        id=run.id,
        backend=run.backend,
        status=run.status,
        reason=run.reason,
        availability=payload.get("availability") if isinstance(payload.get("availability"), str) else None,
        document_count=run.document_count,
        collection_name=run.collection_name,
        payload=payload,
        error_message=run.error_message,
        started_at=run.started_at.isoformat(),
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
    )

import pytest

from yoyo.modules.knowledge.rag_retriever import get_rag_context
from yoyo.modules.knowledge.schemas import AttractionContext


@pytest.mark.asyncio
async def test_rag_context_falls_back_to_sql_only_when_query_returns_no_positive_chunks(monkeypatch) -> None:
    async def fake_query_pgvector_documents(**kwargs):
        return {
            "status": "degraded",
            "reason": "query_failed",
            "documents": [],
        }

    monkeypatch.setattr(
        "yoyo.modules.knowledge.rag_retriever.query_pgvector_documents",
        fake_query_pgvector_documents,
    )
    monkeypatch.setattr(
        "yoyo.modules.knowledge.rag_retriever.rank_documents_for_query",
        lambda documents, query: [],
    )

    attraction = AttractionContext(
        id="attr-empty-rag",
        name="Forbidden City",
        category="museum",
        history="Imperial history",
        practical_notes=["Large site"],
    )
    rag = await get_rag_context(
        query="Tell me the deeper history and background",
        attraction=attraction,
    )
    assert rag.retrieval_mode == "sql_only"
    assert rag.chunks == []


@pytest.mark.asyncio
async def test_rag_context_uses_pgvector_query_result_when_available(monkeypatch) -> None:
    async def fake_query_pgvector_documents(**kwargs):
        return {
            "status": "ok",
            "reason": "backend_query",
            "documents": [
                {
                    "id": "doc-1",
                    "text": "Forbidden City has a layered imperial history and symbolic background.",
                    "metadata": {"poi_name": "Forbidden City", "doc_type": "history"},
                    "score": 0.95,
                }
            ],
        }

    monkeypatch.setattr(
        "yoyo.modules.knowledge.rag_retriever.query_pgvector_documents",
        fake_query_pgvector_documents,
    )
    monkeypatch.setattr(
        "yoyo.modules.knowledge.rag_retriever.get_rag_backend_status",
        lambda: {"ready": True, "enabled": True, "availability": "ready", "reason": "backend_ready"},
    )

    attraction = AttractionContext(
        id="attr-forbidden-city",
        name="Forbidden City",
        category="museum",
        history="Imperial history",
        practical_notes=["Large site"],
    )
    rag = await get_rag_context(
        query="Tell me the deeper history and background",
        attraction=attraction,
    )
    assert rag.retrieval_mode == "sql_then_rag"
    assert len(rag.chunks) == 1
    assert rag.chunks[0].metadata["backend_ready"] is True
    assert rag.chunks[0].metadata["query_status"] == "ok"
    assert rag.chunks[0].text.startswith("Forbidden City has a layered imperial history")

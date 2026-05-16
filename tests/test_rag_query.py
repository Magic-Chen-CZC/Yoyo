import pytest

from yoyo.modules.knowledge.fallback_router import should_use_rag_fallback
from yoyo.modules.knowledge.rag_retriever import _build_metadata_filters, get_rag_context
from yoyo.modules.knowledge.schemas import AttractionContext


def test_rag_metadata_filters_do_not_include_nonexistent_alias_field() -> None:
    attraction = AttractionContext(
        id="attr-forbidden-city",
        name="Forbidden City",
        category="museum",
        history="Imperial history",
        practical_notes=["Large site"],
        aliases=["故宫", "紫禁城"],
    )
    filters = _build_metadata_filters(
        "Tell me the deeper history and background",
        attraction,
    )
    assert filters["poi_name"] == "Forbidden City"
    assert "poi_aliases" not in filters
    assert filters["doc_type"] == ["history", "symbolism", "architecture", "curation"]
    assert filters["language"] == ["zh", "en"]


def test_sql_direct_attraction_fields_do_not_trigger_rag_fallback() -> None:
    attraction = AttractionContext(
        id="attr-forbidden-city",
        name="Forbidden City",
        category="museum",
        short_intro="Imperial palace complex",
        history="Imperial history",
        practical_notes=["Large site"],
        aliases=["故宫", "紫禁城"],
    )

    assert should_use_rag_fallback(
        intent="attraction_explain",
        query="故宫有什么历史，简单介绍一下",
        attraction=attraction,
    ) is False


def test_deep_non_sql_attraction_question_triggers_rag_fallback() -> None:
    attraction = AttractionContext(
        id="attr-forbidden-city",
        name="Forbidden City",
        category="museum",
        short_intro="Imperial palace complex",
        history="Imperial history",
        practical_notes=["Large site"],
        aliases=["故宫", "紫禁城"],
    )

    assert should_use_rag_fallback(
        intent="attraction_explain",
        query="把故宫的中轴线、空间秩序和政治象征拆解一下",
        attraction=attraction,
    ) is True


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

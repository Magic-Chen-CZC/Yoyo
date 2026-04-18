from yoyo.modules.knowledge.rag_documents import build_rag_documents_from_seed
from yoyo.modules.knowledge.rag_index_service import rank_documents_for_query


def test_build_rag_documents_from_seed_returns_documents() -> None:
    documents = build_rag_documents_from_seed()
    assert len(documents) > 0
    assert all("text" in item for item in documents)
    assert all("metadata" in item for item in documents)
    assert any(item["metadata"]["doc_type"] == "history" for item in documents)



def test_rank_documents_for_query_prefers_history_like_chunks() -> None:
    documents = [
        {
            "id": "doc-1",
            "text": "Forbidden City history and imperial background details.",
            "metadata": {"doc_type": "history", "poi_name": "Forbidden City"},
        },
        {
            "id": "doc-2",
            "text": "Visitor tips for the route and where to take photos.",
            "metadata": {"doc_type": "practical_notes", "poi_name": "Forbidden City"},
        },
    ]
    ranked = rank_documents_for_query(documents, "Tell me the history and background")
    assert ranked[0]["id"] == "doc-1"
    assert ranked[0]["score"] >= ranked[1]["score"]

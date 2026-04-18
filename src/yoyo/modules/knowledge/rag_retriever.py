from __future__ import annotations

from typing import Any

from yoyo.modules.knowledge.rag_backend import get_rag_backend_status
from yoyo.modules.knowledge.rag_documents import build_rag_documents_from_attraction_contexts
from yoyo.modules.knowledge.rag_index_service import query_pgvector_documents, rank_documents_for_query
from yoyo.modules.knowledge.schemas import AttractionContext, RAGChunk, RAGContext


async def get_rag_context(
    *,
    query: str,
    attraction: AttractionContext | None,
) -> RAGContext:
    if attraction is None:
        return RAGContext(chunks=[], retrieval_mode="sql_only", fallback_used=False)

    backend_status = get_rag_backend_status()
    documents = build_rag_documents_from_attraction_contexts([attraction])
    query_result = await query_pgvector_documents(
        query=query,
        similarity_top_k=3,
        metadata_filters=_build_metadata_filters(query, attraction.name),
    )
    if query_result["status"] == "ok" and query_result["documents"]:
        ranked_documents = list(query_result["documents"])
    else:
        ranked_documents = rank_documents_for_query(documents, query)
    ranked_chunks: list[RAGChunk] = []
    for item in ranked_documents:
        metadata = dict(item.get("metadata") or {})
        metadata.update(
            {
                "retriever": "llamaindex_pgvector" if query_result["status"] == "ok" else "llamaindex_pgvector_scaffold",
                "backend_ready": backend_status["ready"],
                "backend_enabled": backend_status["enabled"],
                "backend_reason": backend_status["reason"],
                "query_status": query_result["status"],
                "query_reason": query_result["reason"],
            }
        )
        ranked_chunks.append(
            RAGChunk(
                chunk_id=str(item.get("id") or f"{attraction.id}-chunk"),
                text=str(item.get("text") or ""),
                source=attraction.source,
                score=float(item.get("score") or 0),
                metadata=metadata,
            )
        )

    top_chunks = [chunk for chunk in ranked_chunks if (chunk.score or 0) > 0][:3]
    if not top_chunks:
        return RAGContext(
            chunks=[],
            retrieval_mode="sql_only",
            fallback_used=query_result["status"] != "ok",
        )
    return RAGContext(chunks=top_chunks, retrieval_mode="sql_then_rag", fallback_used=True)



def _build_metadata_filters(query: str, poi_name: str) -> dict[str, object]:
    filters: dict[str, object] = {"poi_name": poi_name}
    lowered = query.lower()
    if any(token in lowered for token in ["history", "background", "story", "meaning", "背景", "意义"]):
        filters["doc_type"] = "history"
    filters["language"] = "en"
    return filters



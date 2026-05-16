from __future__ import annotations

from typing import Any

from yoyo.core.config import get_settings
from yoyo.modules.knowledge.rag_backend import Document, PGVectorStore, get_rag_backend_status

try:
    from llama_index.core import Settings, StorageContext, VectorStoreIndex  # type: ignore
    from llama_index.embeddings.openai import OpenAIEmbedding  # type: ignore
except Exception:  # pragma: no cover
    Settings = None  # type: ignore[assignment]
    StorageContext = None  # type: ignore[assignment]
    VectorStoreIndex = None  # type: ignore[assignment]
    OpenAIEmbedding = None  # type: ignore[assignment]


def _build_embedding_model() -> object:
    settings = get_settings()
    if OpenAIEmbedding is None:
        raise RuntimeError("llamaindex_openai_embedding_not_installed")
    kwargs: dict[str, object] = {
        "model": settings.rag_embedding_model,
        "api_key": settings.rag_embedding_api_key,
    }
    if settings.rag_embedding_base_url:
        kwargs["api_base"] = settings.rag_embedding_base_url.rstrip("/")
    return OpenAIEmbedding(**kwargs)


async def build_pgvector_index(documents: list[dict[str, object]]) -> dict[str, object]:
    backend_status = get_rag_backend_status()
    if not backend_status["ready"]:
        return {
            "status": "skipped",
            "reason": backend_status["reason"],
            "availability": backend_status["availability"],
            "document_count": len(documents),
        }

    settings = get_settings()
    if (
        Document is None
        or PGVectorStore is None
        or Settings is None
        or StorageContext is None
        or VectorStoreIndex is None
        or OpenAIEmbedding is None
    ):
        return {
            "status": "failed",
            "reason": "llamaindex_runtime_not_installed",
            "availability": "misconfigured",
            "document_count": len(documents),
        }

    vector_store = PGVectorStore.from_params(
        connection_string=settings.rag_pgvector_dsn,
            async_connection_string=settings.database_url,
        table_name=settings.rag_collection_name,
        embed_dim=settings.rag_embedding_dimension,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    Settings.embed_model = _build_embedding_model()
    llama_documents = [
        Document(text=str(item["text"]), metadata=dict(item["metadata"]))
        for item in documents
    ]
    VectorStoreIndex.from_documents(llama_documents, storage_context=storage_context)
    return {
        "status": "succeeded",
        "reason": "ok",
        "availability": "ready",
        "document_count": len(documents),
        "collection_name": settings.rag_collection_name,
    }


async def query_pgvector_documents(
    *,
    query: str,
    similarity_top_k: int = 3,
    metadata_filters: dict[str, object] | None = None,
) -> dict[str, object]:
    backend_status = get_rag_backend_status()
    if not backend_status["ready"]:
        return {
            "status": "skipped",
            "reason": backend_status["reason"],
            "availability": backend_status["availability"],
            "documents": [],
        }

    settings = get_settings()
    if (
        PGVectorStore is None
        or Settings is None
        or StorageContext is None
        or VectorStoreIndex is None
        or OpenAIEmbedding is None
    ):
        return {
            "status": "error",
            "reason": "llamaindex_runtime_not_installed",
            "availability": "misconfigured",
            "documents": [],
        }

    try:
        vector_store = PGVectorStore.from_params(
            connection_string=settings.rag_pgvector_dsn,
            async_connection_string=settings.database_url,
            table_name=settings.rag_collection_name,
            embed_dim=settings.rag_embedding_dimension,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        Settings.embed_model = _build_embedding_model()
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_context)
        retriever = index.as_retriever(similarity_top_k=similarity_top_k)
        nodes = retriever.retrieve(query)
    except Exception as error:
        return {
            "status": "error",
            "reason": error.__class__.__name__,
            "availability": "ready",
            "documents": [],
        }

    documents: list[dict[str, object]] = []
    filters = metadata_filters or {}
    for index_position, node in enumerate(nodes):
        metadata = dict(getattr(node, "metadata", {}) or {})
        if filters and any(not _metadata_matches_filter(metadata.get(key), value) for key, value in filters.items()):
            continue
        text = str(getattr(node, "text", "") or "")
        documents.append(
            {
                "id": str(metadata.get("id") or f"rag-node-{index_position}"),
                "text": text,
                "metadata": metadata,
                "score": float(getattr(node, "score", 0) or 0),
            }
        )
    return {
        "status": "ok",
        "reason": "backend_query",
        "availability": "ready",
        "documents": documents,
    }



def _metadata_matches_filter(metadata_value: object, filter_value: object) -> bool:
    if isinstance(filter_value, list):
        return any(_metadata_matches_filter(metadata_value, item) for item in filter_value)
    if isinstance(metadata_value, list):
        return any(_metadata_matches_filter(item, filter_value) for item in metadata_value)
    return metadata_value == filter_value



def rank_documents_for_query(documents: list[dict[str, object]], query: str) -> list[dict[str, object]]:
    lowered = query.lower()
    ranked = []
    for item in documents:
        text = str(item.get("text") or "")
        metadata = dict(item.get("metadata") or {})
        score = 0.1
        for token in ["history", "background", "story", "meaning", "重要", "背景", "详细"]:
            if token in lowered and token in text.lower():
                score += 1.0
        score += min(len(text) / 500, 0.5)
        ranked.append({**item, "score": round(score, 3), "metadata": metadata})
    ranked.sort(key=lambda item: float(item.get("score") or 0), reverse=True)
    return ranked

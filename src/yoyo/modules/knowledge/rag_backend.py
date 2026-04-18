from __future__ import annotations

from yoyo.core.config import get_settings

try:
    from llama_index.core import Document  # type: ignore
    from llama_index.vector_stores.postgres import PGVectorStore  # type: ignore
except Exception:  # pragma: no cover
    Document = None  # type: ignore[assignment]
    PGVectorStore = None  # type: ignore[assignment]



def get_rag_backend_status() -> dict[str, object]:
    settings = get_settings()
    if not settings.rag_enabled:
        return {
            "ready": False,
            "enabled": False,
            "availability": "disabled",
            "reason": "rag_disabled",
        }
    if Document is None or PGVectorStore is None:
        return {
            "ready": False,
            "enabled": True,
            "availability": "misconfigured",
            "reason": "llamaindex_pgvector_not_installed",
        }
    if not settings.rag_pgvector_dsn:
        return {
            "ready": False,
            "enabled": True,
            "availability": "misconfigured",
            "reason": "missing_rag_pgvector_dsn",
        }
    if not settings.rag_embedding_api_key:
        return {
            "ready": False,
            "enabled": True,
            "availability": "misconfigured",
            "reason": "missing_rag_embedding_api_key",
        }
    return {
        "ready": True,
        "enabled": True,
        "availability": "ready",
        "reason": "backend_ready",
    }

import pytest

from yoyo.modules.knowledge.rag_backend import get_rag_backend_status
from yoyo.modules.knowledge.rag_index_service import build_pgvector_index, query_pgvector_documents


def test_rag_backend_status_reports_missing_embedding_key(monkeypatch) -> None:
    class FakeSettings:
        rag_enabled = True
        rag_pgvector_dsn = "postgresql://demo"
        rag_embedding_api_key = ""

    monkeypatch.setattr("yoyo.modules.knowledge.rag_backend.get_settings", lambda: FakeSettings())
    monkeypatch.setattr("yoyo.modules.knowledge.rag_backend.Document", object)
    monkeypatch.setattr("yoyo.modules.knowledge.rag_backend.PGVectorStore", object)

    status = get_rag_backend_status()
    assert status["ready"] is False
    assert status["enabled"] is True
    assert status["availability"] == "misconfigured"
    assert status["reason"] == "missing_rag_embedding_api_key"


def test_rag_backend_status_defaults_to_disabled(monkeypatch) -> None:
    class FakeSettings:
        rag_enabled = False
        rag_pgvector_dsn = ""
        rag_embedding_api_key = ""

    monkeypatch.setattr("yoyo.modules.knowledge.rag_backend.get_settings", lambda: FakeSettings())

    status = get_rag_backend_status()
    assert status["ready"] is False
    assert status["enabled"] is False
    assert status["availability"] == "disabled"
    assert status["reason"] == "rag_disabled"


@pytest.mark.asyncio
async def test_build_pgvector_index_skips_when_backend_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "yoyo.modules.knowledge.rag_index_service.get_rag_backend_status",
        lambda: {"ready": False, "enabled": False, "availability": "disabled", "reason": "rag_disabled"},
    )

    result = await build_pgvector_index([
        {"id": "doc-1", "text": "hello", "metadata": {"poi_name": "demo"}}
    ])
    assert result["status"] == "skipped"
    assert result["availability"] == "disabled"
    assert result["reason"] == "rag_disabled"


@pytest.mark.asyncio
async def test_rag_index_service_uses_configured_embedding_base_url_and_dimension(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeSettings:
        database_url = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yoyo"
        rag_pgvector_dsn = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/yoyo"
        rag_collection_name = "demo_collection"
        rag_embedding_dimension = 1024
        rag_embedding_model = "openai/text-embedding-3-small"
        rag_embedding_api_key = "test-key"
        rag_embedding_base_url = "https://openrouter.example/api/v1"

    class FakePGVectorStore:
        @classmethod
        def from_params(cls, **kwargs):
            calls["pgvector"] = kwargs
            return object()

    class FakeStorageContext:
        @classmethod
        def from_defaults(cls, vector_store=None):
            calls["storage_vector_store"] = vector_store
            return object()

    class FakeOpenAIEmbedding:
        def __init__(self, **kwargs) -> None:
            calls["embedding"] = kwargs

    class FakeVectorStoreIndex:
        @classmethod
        def from_documents(cls, documents, storage_context=None):
            calls["documents_count"] = len(documents)
            return object()

        @classmethod
        def from_vector_store(cls, vector_store=None, storage_context=None):
            class FakeIndex:
                def as_retriever(self, similarity_top_k=3):
                    class FakeRetriever:
                        def retrieve(self, query):
                            return []

                    return FakeRetriever()

            calls["vector_store"] = vector_store
            return FakeIndex()

    class FakeSettingsHolder:
        embed_model = None

    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.get_settings", lambda: FakeSettings())
    monkeypatch.setattr(
        "yoyo.modules.knowledge.rag_index_service.get_rag_backend_status",
        lambda: {"ready": True, "enabled": True, "availability": "ready", "reason": "backend_ready"},
    )
    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.PGVectorStore", FakePGVectorStore)
    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.StorageContext", FakeStorageContext)
    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.OpenAIEmbedding", FakeOpenAIEmbedding)
    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.VectorStoreIndex", FakeVectorStoreIndex)
    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.Settings", FakeSettingsHolder)
    monkeypatch.setattr("yoyo.modules.knowledge.rag_index_service.Document", lambda text, metadata: {"text": text, "metadata": metadata})

    await build_pgvector_index([
        {"id": "doc-1", "text": "hello", "metadata": {"poi_name": "demo"}}
    ])
    await query_pgvector_documents(query="hello")

    assert calls["pgvector"]["embed_dim"] == 1024
    assert calls["embedding"]["api_key"] == "test-key"
    assert calls["embedding"]["api_base"] == "https://openrouter.example/api/v1"

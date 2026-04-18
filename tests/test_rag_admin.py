import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rebuild_rag_index_creates_run_record(client: AsyncClient) -> None:
    response = await client.post("/api/v1/rag/index-runs/rebuild", json={})
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["backend"] == "llamaindex_pgvector"
    assert body["status"] in {"running", "succeeded", "skipped", "failed", "error"}
    assert "backend_status" in body["payload"]
    assert body["payload"]["operation"] == "rebuild_index"
    assert body["payload"]["execution_mode"] == "synchronous"


@pytest.mark.asyncio
async def test_rebuild_rag_index_accepts_filtered_seed_request(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/rag/index-runs/rebuild",
        json={"use_seed": True, "poi_name": "Forbidden City", "doc_type": "history", "limit": 1},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["document_count"] <= 1
    assert body["payload"]["request"]["use_seed"] is True
    assert body["payload"]["request"]["poi_name"] == "Forbidden City"
    assert body["payload"]["request"]["doc_type"] == "history"


@pytest.mark.asyncio
async def test_get_latest_rag_index_run_returns_latest_record(client: AsyncClient) -> None:
    create_response = await client.post("/api/v1/rag/index-runs/rebuild", json={})
    assert create_response.status_code == 200

    latest_response = await client.get("/api/v1/rag/index-runs/latest")
    assert latest_response.status_code == 200
    latest = latest_response.json()["data"]
    assert latest["backend"] == "llamaindex_pgvector"
    assert latest["id"] == create_response.json()["data"]["id"]

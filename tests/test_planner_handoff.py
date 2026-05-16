from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_route_edit_query_redirects_to_manual_planning_flow(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "Replace Jingshan Park with another scenic stop and make the route easier.",
            "language": "en",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "manual_route_edit_redirect"
    assert body["data"]["metadata"]["manual_route_edit_redirect"] is True
    assert "itinerary editor" in body["data"]["answer"].lower()
    assert "planner_handoff" not in body["data"]["metadata"]

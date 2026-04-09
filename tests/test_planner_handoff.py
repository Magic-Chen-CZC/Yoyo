from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_planner_handoff_returns_structured_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/qa/ask",
        json={
            "query": "Replace Jingshan Park with another scenic stop and make the route easier.",
            "language": "en",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["intent"] == "planner_handoff"
    handoff = body["data"]["metadata"]["planner_handoff"]
    assert handoff["operation"] == "replace_stop"
    assert handoff["target"] == "Jingshan Park"
    assert handoff["constraints"]["theme"] == "scenic"
    assert handoff["constraints"]["walking"] == "lighter"

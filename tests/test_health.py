from fastapi.testclient import TestClient

from yoyo.app import app


client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 0,
        "message": "ok",
        "data": {"status": "ok"},
    }

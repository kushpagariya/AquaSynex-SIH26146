"""API tests for /api/health endpoint."""

from fastapi.testclient import TestClient


def test_get_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert json_data["data"]["status"] == "healthy"
    assert json_data["data"]["databaseStatus"] == "connected"
    assert "uptime" in json_data["data"]
    assert "modelsAvailable" in json_data["data"]
    assert "meta" in json_data
    assert "requestId" in json_data["meta"]

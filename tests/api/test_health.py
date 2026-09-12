"""Health API endpoint integration tests.

Tests boundary verification for GET /api/health against FastAPI backend.
"""

from fastapi.testclient import TestClient


def test_health_check_endpoint(client: TestClient):
    """Verify GET /api/health returns 200, valid envelope, and connected DB status."""
    response = client.get("/api/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Envelope validation
    body = response.json()
    assert body.get("success") is True
    assert "data" in body
    assert "meta" in body

    # Meta validation
    meta = body["meta"]
    assert "timestamp" in meta
    assert "requestId" in meta
    assert isinstance(meta["requestId"], str) and len(meta["requestId"]) > 0

    # Headers validation
    assert "x-request-id" in response.headers or "X-Request-ID" in response.headers

    # Payload validation
    data = body["data"]
    assert data["status"] == "healthy"
    assert data["databaseStatus"] == "connected"
    assert data["version"] == "1.0.0"
    assert isinstance(data["uptime"], (int, float)) and data["uptime"] >= 0
    assert isinstance(data["modelsAvailable"], list)
    assert len(data["modelsAvailable"]) > 0
    assert "isolation_forest_v1" in data["modelsAvailable"]

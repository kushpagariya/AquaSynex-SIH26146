"""Tests for /api/alerts endpoint."""

from fastapi.testclient import TestClient


def test_list_alerts_endpoint(client: TestClient):
    """Verify /api/alerts returns 200 with envelope."""
    response = client.get("/api/alerts?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    if body["data"]:
        alert = body["data"][0]
        assert "alertId" in alert
        assert "severity" in alert
        assert "status" in alert


def test_list_alerts_with_status_filter(client: TestClient):
    """Verify /api/alerts filtering by active status."""
    response = client.get("/api/alerts?status=active&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    for a in body["data"]:
        assert a["status"].upper() not in ("RESOLVED", "DISMISSED")

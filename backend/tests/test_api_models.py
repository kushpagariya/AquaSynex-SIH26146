"""API tests for models endpoint."""

from fastapi.testclient import TestClient


def test_list_models(client: TestClient):
    response = client.get("/api/models")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) >= 1
    model = res["data"][0]
    assert model["modelId"] == "isolation_forest_v1"
    assert model["modelType"] == "anomaly_detection"

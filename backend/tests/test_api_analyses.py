"""API tests for analysis orchestration endpoints."""

from fastapi.testclient import TestClient


def test_trigger_and_get_analysis(client: TestClient, seeded_db):
    # Trigger analysis
    response = client.post(
        "/api/datasets/test-dataset-1/analyses",
        json={"config": {"maxEntities": 100, "topExplanations": 5}},
    )
    assert response.status_code == 202
    res = response.json()
    assert res["success"] is True
    assert "analysisId" in res["data"]
    analysis_id = res["data"]["analysisId"]

    # Poll status
    status_res = client.get(f"/api/analyses/{analysis_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["analysisId"] == analysis_id
    assert status_data["status"] in ["pending", "running", "completed"]


def test_list_analyses_for_dataset(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/analyses")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) >= 1
    assert res["data"][0]["analysisId"] == "test-analysis-1"


def test_analysis_not_found(client: TestClient):
    response = client.get("/api/analyses/non-existent-analysis")
    assert response.status_code == 404
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"

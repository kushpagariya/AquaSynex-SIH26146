"""API tests for ML result endpoints."""

from fastapi.testclient import TestClient


def test_list_analysis_results(client: TestClient, seeded_db):
    response = client.get("/api/analyses/test-analysis-1/results")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) == 2
    assert "pagination" in res["meta"]


def test_get_entity_result_detail(client: TestClient, seeded_db):
    response = client.get("/api/analyses/test-analysis-1/results/addr-bob")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["entityId"] == "addr-bob"
    assert data["riskScore"] == 0.82
    assert len(data["explanations"]) == 1
    assert data["explanations"][0]["featureName"] == "graph_pagerank"


def test_entity_result_not_found(client: TestClient, seeded_db):
    response = client.get("/api/analyses/test-analysis-1/results/non-existent-entity")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESULT_NOT_FOUND"

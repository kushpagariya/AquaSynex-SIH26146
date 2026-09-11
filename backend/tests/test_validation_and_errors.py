"""Tests for validation rules, error handling, and API edge cases."""

import io
from fastapi.testclient import TestClient


def test_invalid_pagination_page_zero(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?page=0")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_pagination_page_size_exceeded(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?pageSize=9999")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_risk_score_filter(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?minRiskScore=1.5")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_risk_level_filter(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?riskLevel=extreme")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_FILTER_VALUE"


def test_invalid_sort_field(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?sortBy=non_existent_column")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_SORT_FIELD"


def test_delete_dataset_with_running_analysis_fails(client: TestClient, seeded_db):
    # Set an analysis run to running
    seeded_db.execute("UPDATE analysis_runs SET status = 'running' WHERE dataset_id = 'test-dataset-1'")
    response = client.delete("/api/datasets/test-dataset-1")
    assert response.status_code == 409
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "DATASET_ANALYSIS_RUNNING"


def test_openapi_schema(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "AquaSynex Bitcoin Analysis API"
    assert "/api/health" in schema["paths"]
    assert "/api/datasets" in schema["paths"]
    assert "/api/transactions/{transactionId}" in schema["paths"]
    assert "/api/analyses/{analysisId}/graph" in schema["paths"]

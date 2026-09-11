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


def test_invalid_btc_filter_negative(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?minValueBtc=-5.0")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_FILTER_VALUE"


def test_invalid_btc_filter_range(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?minValueBtc=10.0&maxValueBtc=2.0")
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_FILTER_VALUE"


def test_invalid_timestamp_range(client: TestClient, seeded_db):
    response = client.get(
        "/api/datasets/test-dataset-1/transactions?fromTimestamp=2026-09-11T15:00:00Z&toTimestamp=2026-09-11T10:00:00Z"
    )
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_FILTER_VALUE"


def test_invalid_ml_result_invariant_fails_analysis(client: TestClient, seeded_db):
    """If ML pipeline returns invalid results violating invariants, backend rejects them and marks run failed."""
    from backend.services.pipeline_service import reset_pipeline_runner, set_pipeline_runner

    def bad_ml_runner(**kwargs):
        return [
            {
                "entity_id": "tx-001",
                "entity_type": "transaction",
                "anomaly_score": 1.5,  # Invalid: > 1.0
                "risk_score": 1.5,     # Invalid: > 1.0
                "risk_level": "high",
            }
        ]

    set_pipeline_runner(bad_ml_runner)
    try:
        response = client.post("/api/datasets/test-dataset-1/analyses", json={})
        assert response.status_code == 202
        analysis_id = response.json()["data"]["analysisId"]

        status_res = client.get(f"/api/analyses/{analysis_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()["data"]
        assert status_data["status"] == "failed"
        assert "invariant violation" in status_data["errorMessage"]
    finally:
        reset_pipeline_runner()


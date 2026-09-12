"""API tests for analysis orchestration endpoints."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.services.pipeline_service import reset_pipeline_runner, set_pipeline_runner


def test_trigger_analysis_when_ml_pipeline_missing(client: TestClient, seeded_db):
    """When ML pipeline is not installed, analysis gracefully fails without fake predictions."""
    reset_pipeline_runner()
    response = client.post(
        "/api/datasets/test-dataset-1/analyses",
        json={"config": {"maxEntities": 100, "topExplanations": 5}},
    )
    assert response.status_code == 202
    res = response.json()
    assert res["success"] is True
    analysis_id = res["data"]["analysisId"]

    # In synchronous test run, analysis has finished and failed cleanly
    status_res = client.get(f"/api/analyses/{analysis_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()["data"]
    assert status_data["analysisId"] == analysis_id
    assert status_data["status"] == "failed"
    assert "not installed" in status_data["errorMessage"]


def test_trigger_analysis_with_injected_runner(client: TestClient, seeded_db):
    """When an ML pipeline runner is available, analysis completes and counts summary correctly."""
    def mock_runner(**kwargs):
        return [
            {
                "entity_id": "tx-001",
                "entity_type": "transaction",
                "anomaly_score": 0.85,
                "risk_score": 0.85,
                "risk_level": "high",
                "confidence": 0.9,
                "explanations": [],
                "features": [],
                "graph_evidence": [],
                "predicted_at": datetime.now(timezone.utc),
            },
            {
                "entity_id": "addr-bob",
                "entity_type": "address",
                "anomaly_score": 0.95,
                "risk_score": 0.95,
                "risk_level": "critical",
                "confidence": 0.95,
                "explanations": [],
                "features": [],
                "graph_evidence": [],
                "predicted_at": datetime.now(timezone.utc),
            },
        ]

    set_pipeline_runner(mock_runner)
    try:
        response = client.post(
            "/api/datasets/test-dataset-1/analyses",
            json={"modelId": "isolation_forest_v1", "config": {"maxEntities": 100}},
        )
        assert response.status_code == 202
        res = response.json()
        analysis_id = res["data"]["analysisId"]

        status_res = client.get(f"/api/analyses/{analysis_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()["data"]
        assert status_data["status"] == "completed"
        assert status_data["entityCount"] == 2
        assert status_data["highRiskCount"] == 1
        assert status_data["criticalRiskCount"] == 1
    finally:
        reset_pipeline_runner()


def test_trigger_analysis_conflict_when_running(client: TestClient, seeded_db):
    """Cannot trigger concurrent analysis if one is already running/pending on the dataset."""
    # Seed a running analysis
    seeded_db.execute(
        "INSERT INTO analysis_runs (analysis_id, dataset_id, status, started_at) VALUES ('running-1', 'test-dataset-1', 'running', current_timestamp)"
    )

    response = client.post(
        "/api/datasets/test-dataset-1/analyses",
        json={},
    )
    assert response.status_code == 409
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "DATASET_ANALYSIS_RUNNING"


def test_trigger_analysis_unknown_model_not_found(client: TestClient, seeded_db):
    """Unknown modelId returns 404 MODEL_NOT_FOUND per validation rules."""
    response = client.post(
        "/api/datasets/test-dataset-1/analyses",
        json={"modelId": "unknown_super_ai_model"},
    )
    assert response.status_code == 404
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "MODEL_NOT_FOUND"


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

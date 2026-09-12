"""Analysis Flow Integration Test.

Tests the asynchronous analysis triggering lifecycle:
POST trigger -> background worker execution -> ML dependency boundary check ->
controlled terminal failure transition -> polling inspection.
"""

from fastapi.testclient import TestClient
import duckdb


def test_analysis_controlled_ml_failure_flow(
    client: TestClient, db: duckdb.DuckDBPyConnection, uploaded_dataset: dict
):
    """Verify that triggering analysis without ML module reaches controlled 'failed' state without crashing."""
    dataset_id = uploaded_dataset["datasetId"]

    # 1. Trigger analysis via API
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "isolation_forest_v1", "modelVersion": "1.0.0"},
    )
    assert trigger_resp.status_code == 202
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    # 2. Poll the status via API
    status_resp = client.get(f"/api/analyses/{analysis_id}")
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["success"] is True

    analysis = status_body["data"]
    assert analysis["analysisId"] == analysis_id
    assert analysis["datasetId"] == dataset_id

    # CRITICAL INVARIANT: ML module (pipeline.ml.model_inference) is not implemented yet.
    # The system must record a controlled failure:
    assert analysis["status"] == "failed"
    assert analysis["errorMessage"] is not None
    assert len(analysis["errorMessage"]) > 0

    # 3. Direct DuckDB inspection to verify analysis_runs record
    row = db.execute(
        "SELECT status, error_message, entity_count, high_risk_count FROM analysis_runs WHERE analysis_id = ?",
        [analysis_id],
    ).fetchone()
    assert row is not None
    assert row[0] == "failed"
    assert row[1] is not None
    # Must NOT have fabricated high risk counts
    assert row[2] == 0 or row[2] is None
    assert row[3] == 0 or row[3] is None

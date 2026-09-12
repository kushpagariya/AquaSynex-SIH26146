"""Analysis API endpoint tests.

Verifies triggering analyses, background processing lifecycle, and controlled
ML-unavailable terminal state handling.
"""

from fastapi.testclient import TestClient


def test_trigger_and_inspect_analysis_flow(client: TestClient, uploaded_dataset: dict):
    """Verify triggering an analysis transitions cleanly to controlled 'failed' state when ML is unavailable."""
    dataset_id = uploaded_dataset["datasetId"]

    # 1. Trigger analysis
    response = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "isolation_forest_v1", "modelVersion": "1.0.0"},
    )
    assert response.status_code == 202, f"Failed to trigger analysis: {response.text}"
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert "analysisId" in data
    analysis_id = data["analysisId"]
    assert data["datasetId"] == dataset_id
    assert data["status"] in ("pending", "running", "failed")

    # 2. Inspect analysis status
    poll_resp = client.get(f"/api/analyses/{analysis_id}")
    assert poll_resp.status_code == 200
    poll_body = poll_resp.json()
    assert poll_body["success"] is True

    analysis_data = poll_body["data"]
    assert analysis_data["analysisId"] == analysis_id
    assert analysis_data["datasetId"] == dataset_id
    assert analysis_data["modelId"] == "isolation_forest_v1"

    # Because ML pipeline module is not yet finalized, backend MUST record controlled failure:
    # It must NOT crash, hang, invent fake predictions, or silently claim success.
    assert analysis_data["status"] == "failed", (
        f"Expected terminal status 'failed' due to missing ML module, got '{analysis_data['status']}'"
    )
    assert analysis_data.get("errorMessage") is not None
    assert "pipeline.ml.model_inference" in analysis_data["errorMessage"] or "ML" in analysis_data["errorMessage"]


def test_list_analyses_for_dataset(client: TestClient, uploaded_dataset: dict):
    """Verify GET /api/datasets/{datasetId}/analyses returns all runs for the dataset."""
    dataset_id = uploaded_dataset["datasetId"]

    # Trigger one run
    client.post(f"/api/datasets/{dataset_id}/analyses", json={})

    # List runs
    resp = client.get(f"/api/datasets/{dataset_id}/analyses")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 1
    for run in body["data"]:
        assert run["datasetId"] == dataset_id


def test_get_analysis_not_found(client: TestClient):
    """Verify requesting non-existent analysis ID returns controlled 404 ANALYSIS_NOT_FOUND."""
    resp = client.get("/api/analyses/nonexistent-analysis-0000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ANALYSIS_NOT_FOUND"

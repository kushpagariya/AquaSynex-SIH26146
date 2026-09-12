"""Results API endpoint tests.

Verifies querying ML prediction results, entity SHAP explanations, and enforces
that no fabricated results are produced when ML is unavailable.
"""

from fastapi.testclient import TestClient


def test_list_results_returns_empty_when_ml_incomplete(client: TestClient, uploaded_dataset: dict):
    """Verify GET /api/analyses/{analysisId}/results returns empty list without fabricated predictions."""
    dataset_id = uploaded_dataset["datasetId"]

    # Trigger analysis (which fails gracefully due to missing ML module)
    trig_resp = client.post(f"/api/datasets/{dataset_id}/analyses", json={})
    analysis_id = trig_resp.json()["data"]["analysisId"]

    # Request results
    resp = client.get(f"/api/analyses/{analysis_id}/results")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    # Critical invariant: must NOT return fake heuristic results when ML pipeline failed
    results = body["data"]
    assert isinstance(results, list)
    assert len(results) == 0, (
        f"Expected 0 ML results for incomplete/failed analysis, but found {len(results)} fabricated results!"
    )
    assert body["meta"]["pagination"]["totalItems"] == 0


def test_get_entity_result_detail_not_found(client: TestClient, uploaded_dataset: dict):
    """Verify querying an entity's prediction detail for incomplete analysis returns 404 RESULT_NOT_FOUND."""
    dataset_id = uploaded_dataset["datasetId"]
    trig_resp = client.post(f"/api/datasets/{dataset_id}/analyses", json={})
    analysis_id = trig_resp.json()["data"]["analysisId"]

    resp = client.get(f"/api/analyses/{analysis_id}/results/1BoatSLRHtKNngkdXEeobR76b53LETtpyT")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESULT_NOT_FOUND"


def test_list_results_unknown_analysis_returns_404(client: TestClient):
    """Verify non-existent analysisId returns 404 ANALYSIS_NOT_FOUND."""
    resp = client.get("/api/analyses/nonexistent-analysis-id-000/results")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ANALYSIS_NOT_FOUND"

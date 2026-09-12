"""Error Handling Integration Test.

Verifies canonical error response envelopes, validation error formats,
and 404 status codes for invalid IDs.
"""

from io import BytesIO
from fastapi.testclient import TestClient


def test_invalid_dataset_upload_errors(client: TestClient):
    """Verify backend returns canonical error envelopes for empty or unsupported files."""
    # 1. Empty file
    empty_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("empty.csv", BytesIO(b""), "text/csv")},
        data={"name": "Empty File Dataset"},
    )
    assert empty_resp.status_code == 400
    empty_body = empty_resp.json()
    assert empty_body["success"] is False
    assert empty_body["error"]["code"] == "VALIDATION_ERROR"
    assert "empty" in empty_body["error"]["message"].lower()

    # 2. Unsupported format (.exe) -> Backend returns 400 with UNSUPPORTED_FILE_FORMAT
    unsupported_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("malicious.exe", BytesIO(b"binary_junk"), "application/octet-stream")},
        data={"name": "Executable Dataset"},
    )
    assert unsupported_resp.status_code == 400
    unsupported_body = unsupported_resp.json()
    assert unsupported_body["success"] is False
    assert unsupported_body["error"]["code"] == "UNSUPPORTED_FILE_FORMAT"


def test_404_error_envelopes(client: TestClient):
    """Verify 404 responses conform to the canonical error envelope across all entity types."""
    endpoints_and_codes = [
        ("/api/datasets/nonexistent-dataset-id", "DATASET_NOT_FOUND"),
        ("/api/transactions/0000000000000000000000000000000000000000000000000000000000000000", "TRANSACTION_NOT_FOUND"),
        ("/api/addresses/1NonExistentAddress000000000000000", "ADDRESS_NOT_FOUND"),
        ("/api/analyses/nonexistent-analysis-id", "ANALYSIS_NOT_FOUND"),
    ]

    for ep, expected_code in endpoints_and_codes:
        resp = client.get(ep)
        assert resp.status_code == 404, f"Expected 404 for {ep}, got {resp.status_code}"
        body = resp.json()
        assert body["success"] is False
        assert "error" in body
        assert body["error"]["code"] == expected_code
        assert "meta" in body
        assert "requestId" in body["meta"]


def test_validation_error_envelope(client: TestClient, uploaded_dataset: dict):
    """Verify FastAPI Pydantic validation errors return structured 400 envelopes with field details."""
    dataset_id = uploaded_dataset["datasetId"]

    # Invalid query parameter: minRiskScore > 1.0 (must be between 0.0 and 1.0)
    resp = client.get(f"/api/datasets/{dataset_id}/transactions?minRiskScore=5.0")
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
    assert "errors" in body["error"]["details"]

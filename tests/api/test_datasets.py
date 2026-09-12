"""Dataset API endpoint tests.

Verifies upload, listing, detail inspection, and deletion endpoints.
"""

from pathlib import Path
from fastapi.testclient import TestClient


def test_upload_dataset_multipart(client: TestClient, sample_csv_path: Path):
    """Verify POST /api/datasets/upload accepts multipart CSV and returns 202 with dataset ID."""
    with open(sample_csv_path, "rb") as f:
        response = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_bitcoin_dataset.csv", f, "text/csv")},
            data={"name": "Bitcoin Live Integration Test"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert "datasetId" in data
    assert data["name"] == "Bitcoin Live Integration Test"
    assert data["status"] in ("ready", "processing")
    assert "uploadedAt" in data

    # Verify detail shows ready and canonical count
    dataset_id = data["datasetId"]
    detail_resp = client.get(f"/api/datasets/{dataset_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["datasetId"] == dataset_id
    assert detail["status"] == "ready"
    assert detail["canonicalTxCount"] == 5
    assert detail["rowCount"] == 5
    assert "transactionId" in detail["availableFields"]
    assert "outputAddress" in detail["availableFields"]
    assert "inputAddress" in detail["availableFields"]


def test_list_datasets(client: TestClient, uploaded_dataset: dict):
    """Verify GET /api/datasets returns paginated list containing the uploaded dataset."""
    response = client.get("/api/datasets?page=1&pageSize=10")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    assert "meta" in body and "pagination" in body["meta"]
    pag = body["meta"]["pagination"]
    assert pag["page"] == 1
    assert pag["pageSize"] == 10
    assert pag["totalItems"] >= 1

    dataset_ids = [d["datasetId"] for d in body["data"]]
    assert uploaded_dataset["datasetId"] in dataset_ids


def test_get_dataset_detail(client: TestClient, uploaded_dataset: dict):
    """Verify GET /api/datasets/{datasetId} returns full metadata and validation summary."""
    dataset_id = uploaded_dataset["datasetId"]
    response = client.get(f"/api/datasets/{dataset_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert data["datasetId"] == dataset_id
    assert data["canonicalTxCount"] == 5
    assert data["format"] == "csv"
    assert "validationSummary" in data
    val_summary = data["validationSummary"]
    assert val_summary["rejectedRows"] == 0
    assert "analysisCapability" in val_summary
    assert val_summary["analysisCapability"]["graphAnalysis"] is True


def test_delete_dataset(client: TestClient, sample_csv_path: Path):
    """Verify DELETE /api/datasets/{datasetId} removes dataset and cascades cleanly."""
    # Upload a dedicated dataset for deletion
    with open(sample_csv_path, "rb") as f:
        upload_resp = client.post(
            "/api/datasets/upload",
            files={"file": ("to_delete.csv", f, "text/csv")},
            data={"name": "Dataset For Deletion"},
        )
    assert upload_resp.status_code == 202
    dataset_id = upload_resp.json()["data"]["datasetId"]

    # Verify exists
    assert client.get(f"/api/datasets/{dataset_id}").status_code == 200

    # Delete
    del_resp = client.delete(f"/api/datasets/{dataset_id}")
    assert del_resp.status_code == 200
    del_body = del_resp.json()
    assert del_body["success"] is True
    assert del_body["data"]["deleted"] is True
    assert del_body["data"]["datasetId"] == dataset_id

    # Verify 404 on subsequent get
    get_resp = client.get(f"/api/datasets/{dataset_id}")
    assert get_resp.status_code == 404
    err_body = get_resp.json()
    assert err_body["success"] is False
    assert err_body["error"]["code"] == "DATASET_NOT_FOUND"

"""API tests for dataset endpoints."""

import io
from fastapi.testclient import TestClient


SAMPLE_CSV = """transaction_id,timestamp,total_output_value_satoshi,fee_satoshi,input_address,output_address
tx-100,2026-09-11T12:00:00Z,5000000000,10000,addr-1,addr-2
tx-101,2026-09-11T13:00:00Z,2000000000,10000,addr-2,addr-3
"""


def test_upload_dataset_csv(client: TestClient):
    file_bytes = SAMPLE_CSV.encode("utf-8")
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Upload Test CSV"},
        files={"file": ("test.csv", io.BytesIO(file_bytes), "text/csv")},
    )
    assert response.status_code == 202
    res = response.json()
    assert res["success"] is True
    assert "datasetId" in res["data"]
    assert res["data"]["name"] == "Upload Test CSV"
    dataset_id = res["data"]["datasetId"]

    # Verify detail endpoint
    get_res = client.get(f"/api/datasets/{dataset_id}")
    assert get_res.status_code == 200
    detail = get_res.json()["data"]
    assert detail["datasetId"] == dataset_id
    assert detail["status"] == "ready"
    assert detail["canonicalTxCount"] == 2


def test_upload_unsupported_format(client: TestClient):
    response = client.post(
        "/api/datasets/upload",
        data={"name": "Bad File"},
        files={"file": ("test.exe", io.BytesIO(b"binary"), "application/octet-stream")},
    )
    assert response.status_code == 400
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "UNSUPPORTED_FILE_FORMAT"


def test_list_datasets(client: TestClient, seeded_db):
    response = client.get("/api/datasets")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) >= 1
    assert "pagination" in res["meta"]


def test_get_dataset_not_found(client: TestClient):
    response = client.get("/api/datasets/non-existent-uuid")
    assert response.status_code == 404
    res = response.json()
    assert res["success"] is False
    assert res["error"]["code"] == "DATASET_NOT_FOUND"


def test_delete_dataset(client: TestClient, seeded_db):
    response = client.delete("/api/datasets/test-dataset-1")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["deleted"] is True

    # Ensure 404 now
    assert client.get("/api/datasets/test-dataset-1").status_code == 404

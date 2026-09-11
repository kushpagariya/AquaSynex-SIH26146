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


def test_upload_float_btc_preserves_satoshi_precision(client: TestClient, db):
    """Ensure floating-point BTC values in raw CSVs are ingested into exact integer satoshis without precision loss."""
    btc_csv = """txid,value,timestamp
tx-btc-1,0.5,2026-09-11T12:00:00Z
tx-btc-2,0.00000001,2026-09-11T12:00:00Z
tx-btc-3,1.23456789,2026-09-11T12:00:00Z
"""
    res = client.post(
        "/api/datasets/upload",
        data={"name": "Float BTC Precision Test"},
        files={"file": ("float_btc.csv", io.BytesIO(btc_csv.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 202
    dataset_id = res.json()["data"]["datasetId"]

    # Verify DuckDB records directly for satoshi values
    rows = db.execute(
        "SELECT transaction_id, total_output_value_satoshi FROM transactions WHERE dataset_id = ? ORDER BY transaction_id",
        [dataset_id],
    ).fetchall()
    assert len(rows) == 3
    tx_map = {r[0]: r[1] for r in rows}
    assert tx_map["tx-btc-1"] == 50_000_000       # 0.5 BTC = 50,000,000 satoshis
    assert tx_map["tx-btc-2"] == 1                # 0.00000001 BTC = 1 satoshi
    assert tx_map["tx-btc-3"] == 123_456_789      # 1.23456789 BTC = 123,456,789 satoshis

    # Verify API serializes to 8-decimal string
    tx_api_res = client.get(f"/api/datasets/{dataset_id}/transactions")
    assert tx_api_res.status_code == 200
    tx_items = tx_api_res.json()["data"]
    api_map = {t["transactionId"]: t["totalOutputValueBtc"] for t in tx_items}
    assert api_map["tx-btc-1"] == "0.50000000"
    assert api_map["tx-btc-2"] == "0.00000001"
    assert api_map["tx-btc-3"] == "1.23456789"


def test_upload_empty_file_rejected(client: TestClient):
    """Uploading an empty file must be rejected with 400 VALIDATION_ERROR."""
    res = client.post(
        "/api/datasets/upload",
        data={"name": "Empty File"},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert res.status_code == 400
    res_data = res.json()
    assert res_data["success"] is False
    assert res_data["error"]["code"] == "VALIDATION_ERROR"
    assert "empty" in res_data["error"]["message"]


def test_upload_path_traversal_sanitized(client: TestClient):
    """Uploading with path traversal in filename must be sanitized."""
    csv_bytes = b"txid,val\ntx1,1000\n"
    res = client.post(
        "/api/datasets/upload",
        data={"name": "Traversal Test"},
        files={"file": ("../../evil.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert res.status_code == 202
    dataset_id = res.json()["data"]["datasetId"]
    get_res = client.get(f"/api/datasets/{dataset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["fileName"] == "evil.csv"


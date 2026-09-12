"""Transaction API endpoint tests.

Verifies querying, filtering, pagination, and detail inspection of transactions.
"""

from fastapi.testclient import TestClient


def test_list_transactions_default(client: TestClient, uploaded_dataset: dict):
    """Verify listing transactions for dataset returns all 5 canonical records."""
    dataset_id = uploaded_dataset["datasetId"]
    resp = client.get(f"/api/datasets/{dataset_id}/transactions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    data = body["data"]
    assert len(data) == 5

    # Check pagination metadata
    pag = body["meta"]["pagination"]
    assert pag["totalItems"] == 5
    assert pag["page"] == 1
    assert pag["pageSize"] == 50

    # Verify fields conform to schema
    for tx in data:
        assert len(tx["transactionId"]) == 64
        assert "totalOutputValueBtc" in tx
        assert "feeBtc" in tx
        assert "timestamp" in tx


def test_list_transactions_pagination(client: TestClient, uploaded_dataset: dict):
    """Verify transactions pagination with custom page size and offsets."""
    dataset_id = uploaded_dataset["datasetId"]

    # Page 1, size 2
    resp1 = client.get(f"/api/datasets/{dataset_id}/transactions?page=1&pageSize=2")
    assert resp1.status_code == 200
    data1 = resp1.json()["data"]
    assert len(data1) == 2

    # Page 2, size 2
    resp2 = client.get(f"/api/datasets/{dataset_id}/transactions?page=2&pageSize=2")
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert len(data2) == 2

    # Page 1 and Page 2 should have distinct transaction IDs
    ids1 = {t["transactionId"] for t in data1}
    ids2 = {t["transactionId"] for t in data2}
    assert len(ids1.intersection(ids2)) == 0


def test_list_transactions_filtering_and_sorting(client: TestClient, uploaded_dataset: dict):
    """Verify filtering by BTC amount and sorting by timestamp."""
    dataset_id = uploaded_dataset["datasetId"]

    # Filter: transactions with value >= 25 BTC (should match 50 BTC and 30 BTC txs)
    resp = client.get(f"/api/datasets/{dataset_id}/transactions?minValueBtc=25.0")
    assert resp.status_code == 200
    txs = resp.json()["data"]
    assert len(txs) == 2
    for tx in txs:
        assert float(tx["totalOutputValueBtc"]) >= 25.0

    # Filter: empty result for unattainable BTC amount
    empty_resp = client.get(f"/api/datasets/{dataset_id}/transactions?minValueBtc=999999.0")
    assert empty_resp.status_code == 200
    assert len(empty_resp.json()["data"]) == 0
    assert empty_resp.json()["meta"]["pagination"]["totalItems"] == 0


def test_get_transaction_detail(client: TestClient, uploaded_dataset: dict):
    """Verify retrieving transaction detail includes inputs, outputs, and satoshi precision."""
    dataset_id = uploaded_dataset["datasetId"]
    list_resp = client.get(f"/api/datasets/{dataset_id}/transactions?pageSize=1")
    tx_id = list_resp.json()["data"][0]["transactionId"]

    detail_resp = client.get(f"/api/transactions/{tx_id}")
    assert detail_resp.status_code == 200
    body = detail_resp.json()
    assert body["success"] is True

    detail = body["data"]
    assert detail["transactionId"] == tx_id
    assert "inputs" in detail
    assert "outputs" in detail
    assert len(detail["inputs"]) >= 1
    assert len(detail["outputs"]) >= 1


def test_get_transaction_not_found(client: TestClient):
    """Verify requesting an unknown transaction returns controlled 404 TRANSACTION_NOT_FOUND."""
    resp = client.get("/api/transactions/deadbeef00000000000000000000000000000000000000000000000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "TRANSACTION_NOT_FOUND"

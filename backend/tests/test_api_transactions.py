"""API tests for transaction query endpoints."""

from fastapi.testclient import TestClient


def test_list_transactions(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/transactions?analysisId=test-analysis-1")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) == 2
    assert "pagination" in res["meta"]

    # Verify 8-decimal BTC string formatting
    tx = next(t for t in res["data"] if t["transactionId"] == "tx-001")
    assert tx["totalInputValueBtc"] == "50.00000000"
    assert tx["totalOutputValueBtc"] == "49.99900000"
    assert tx["feeBtc"] == "0.00100000"
    assert tx["riskScore"] == 0.75
    assert tx["riskLevel"] == "high"


def test_get_transaction_detail(client: TestClient, seeded_db):
    response = client.get("/api/transactions/tx-001?analysisId=test-analysis-1")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    tx = res["data"]
    assert tx["transactionId"] == "tx-001"
    assert len(tx["inputs"]) == 1
    assert tx["inputs"][0]["inputAddress"] == "addr-alice"
    assert tx["inputs"][0]["inputValueBtc"] == "50.00000000"
    assert len(tx["outputs"]) == 2
    assert tx["mlResult"] is not None
    assert tx["mlResult"]["riskScore"] == 0.75


def test_transaction_not_found(client: TestClient):
    response = client.get("/api/transactions/non-existent-tx")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"

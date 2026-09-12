"""Transaction Flow Integration Test.

Tests end-to-end querying of transactions, sorting, filtering, and cross-referencing
inputs and outputs.
"""

from fastapi.testclient import TestClient


def test_transaction_query_and_detail_flow(client: TestClient, uploaded_dataset: dict):
    """Verify transaction listing and detail endpoints preserve data fidelity."""
    dataset_id = uploaded_dataset["datasetId"]

    # 1. List transactions sorted by timestamp ascending
    resp = client.get(f"/api/datasets/{dataset_id}/transactions?sortBy=timestamp&sortDir=asc")
    assert resp.status_code == 200
    txs = resp.json()["data"]
    assert len(txs) == 5

    # Check ascending timestamp order
    timestamps = [t["timestamp"] for t in txs]
    assert timestamps == sorted(timestamps)

    # 2. Pick the first transaction (50 BTC) and inspect detail
    first_tx = txs[0]
    detail_resp = client.get(f"/api/transactions/{first_tx['transactionId']}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]

    assert detail["transactionId"] == first_tx["transactionId"]
    assert detail["totalOutputValueBtc"] == "50.00000000"
    assert detail["feeBtc"] == "0.00010000"

    # Inputs should show Satoshi's address
    inputs = detail["inputs"]
    assert len(inputs) == 1
    assert inputs[0]["inputAddress"] == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"

    # Outputs should show Alice's address
    outputs = detail["outputs"]
    assert len(outputs) == 1
    assert outputs[0]["outputAddress"] == "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"

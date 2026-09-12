"""Data Consistency Integration Test.

Tests that IDs, transaction counts, and financial values remain strictly
consistent across upload, listing, detail, transaction, and address layers.
"""

from fastapi.testclient import TestClient


def test_cross_layer_id_and_count_consistency(client: TestClient, uploaded_dataset: dict):
    """Verify that dataset IDs, transaction IDs, address IDs, and balances match across all endpoints."""
    dataset_id = uploaded_dataset["datasetId"]

    # 1. Dataset ID in list == uploaded dataset ID
    list_resp = client.get("/api/datasets")
    assert list_resp.status_code == 200
    listed_datasets = {d["datasetId"]: d for d in list_resp.json()["data"]}
    assert dataset_id in listed_datasets
    assert listed_datasets[dataset_id]["rowCount"] == 5

    # 2. Dataset ID in detail == uploaded dataset ID
    detail_resp = client.get(f"/api/datasets/{dataset_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["data"]["datasetId"] == dataset_id
    assert detail_resp.json()["data"]["canonicalTxCount"] == 5
    assert detail_resp.json()["data"]["rowCount"] == 5

    # 3. Transactions match their detail endpoints
    txs_resp = client.get(f"/api/datasets/{dataset_id}/transactions")
    assert txs_resp.status_code == 200
    transactions = txs_resp.json()["data"]
    assert len(transactions) == 5
    for tx in transactions:
        # Transaction ID matches its detail endpoint
        tx_detail_resp = client.get(f"/api/transactions/{tx['transactionId']}")
        assert tx_detail_resp.status_code == 200
        assert tx_detail_resp.json()["data"]["transactionId"] == tx["transactionId"]
        assert tx_detail_resp.json()["data"]["totalOutputValueBtc"] == tx["totalOutputValueBtc"]

    # 4. Addresses match their detail endpoints
    addrs_resp = client.get(f"/api/datasets/{dataset_id}/addresses")
    assert addrs_resp.status_code == 200
    addresses = addrs_resp.json()["data"]
    assert len(addresses) == 5
    for addr in addresses:
        # Address ID matches its detail endpoint
        addr_detail_resp = client.get(f"/api/addresses/{addr['addressId']}")
        assert addr_detail_resp.status_code == 200
        assert addr_detail_resp.json()["data"]["addressId"] == addr["addressId"]
        assert addr_detail_resp.json()["data"]["transactionCount"] == addr["transactionCount"]

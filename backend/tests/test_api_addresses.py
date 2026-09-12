"""API tests for address query endpoints."""

from fastapi.testclient import TestClient


def test_list_addresses(client: TestClient, seeded_db):
    response = client.get("/api/datasets/test-dataset-1/addresses?analysisId=test-analysis-1")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert len(res["data"]) == 3

    bob = next(a for a in res["data"] if a["addressId"] == "addr-bob")
    assert bob["transactionCount"] == 2
    assert bob["totalReceivedBtc"] == "40.00000000"
    assert bob["totalSentBtc"] == "10.00000000"
    assert bob["riskScore"] == 0.82
    assert bob["riskLevel"] == "high"


def test_get_address_detail(client: TestClient, seeded_db):
    response = client.get("/api/addresses/addr-bob?analysisId=test-analysis-1")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    addr = res["data"]
    assert addr["addressId"] == "addr-bob"
    assert addr["mlResult"] is not None
    assert len(addr["mlResult"]["explanations"]) == 1
    assert addr["mlResult"]["explanations"][0]["featureName"] == "graph_pagerank"


def test_address_not_found(client: TestClient):
    response = client.get("/api/addresses/non-existent-addr")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ADDRESS_NOT_FOUND"

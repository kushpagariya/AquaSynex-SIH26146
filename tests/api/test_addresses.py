"""Address API endpoint tests.

Verifies querying derived addresses, pagination, deduplication, and profile detail.
"""

from fastapi.testclient import TestClient


def test_list_addresses_default(client: TestClient, uploaded_dataset: dict):
    """Verify addresses derived from transactions are listed with no duplicates."""
    dataset_id = uploaded_dataset["datasetId"]
    resp = client.get(f"/api/datasets/{dataset_id}/addresses")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    addresses = body["data"]
    # We had 5 unique addresses across inputs and outputs in sample_bitcoin_dataset.csv
    assert len(addresses) == 5

    # Check for no duplicate address IDs
    addr_ids = [a["addressId"] for a in addresses]
    assert len(addr_ids) == len(set(addr_ids)), "Duplicate addresses detected in listing!"

    expected_addrs = {
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "1BoatSLRHtKNngkdXEeobR76b53LETtpyT",
        "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
        "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
        "1CounterpartyXXXXXXXXXXXXXXXUWLpVr",
    }
    assert set(addr_ids) == expected_addrs

    # Pagination metadata
    pag = body["meta"]["pagination"]
    assert pag["totalItems"] == 5


def test_get_address_detail(client: TestClient, uploaded_dataset: dict):
    """Verify getting address detail returns valid behavioral metrics and balances."""
    addr = "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"
    resp = client.get(f"/api/addresses/{addr}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    profile = body["data"]
    assert profile["addressId"] == addr
    assert profile["transactionCount"] >= 1
    assert "totalReceivedBtc" in profile
    assert "totalSentBtc" in profile
    assert float(profile["totalReceivedBtc"]) > 0


def test_get_address_not_found(client: TestClient):
    """Verify requesting an unknown address returns controlled 404 ADDRESS_NOT_FOUND."""
    resp = client.get("/api/addresses/1UnknownAddressNonExistentXXXXXXXXXXXXXXXX")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ADDRESS_NOT_FOUND"

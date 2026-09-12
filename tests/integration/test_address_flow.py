"""Address Flow Integration Test.

Tests derived address aggregations, balances, and multi-transaction address histories.
"""

from fastapi.testclient import TestClient


def test_address_aggregation_and_balance_flow(client: TestClient, uploaded_dataset: dict):
    """Verify addresses correctly aggregate received/sent satoshis across multiple transactions."""
    # 1. Alice's address: 1BoatSLRHtKNngkdXEeobR76b53LETtpyT
    # - Received in Tx1: 50 BTC
    # - Sent in Tx2: 30 BTC
    # - Sent in Tx5: 15 BTC
    # Total received = 50.00000000 BTC, Total sent = 45.00000000 BTC, Tx count = 3
    alice_resp = client.get("/api/addresses/1BoatSLRHtKNngkdXEeobR76b53LETtpyT")
    assert alice_resp.status_code == 200
    alice = alice_resp.json()["data"]

    assert alice["addressId"] == "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"
    assert alice["transactionCount"] == 3
    assert alice["totalReceivedBtc"] == "50.00000000"
    assert alice["totalSentBtc"] == "45.00000000"

    # 2. Dave's address: 1CounterpartyXXXXXXXXXXXXXXXUWLpVr
    # - Received in Tx4: 10 BTC
    # - Received in Tx5: 15 BTC
    # Total received = 25.00000000 BTC, Total sent = 0.00000000 BTC, Tx count = 2
    dave_resp = client.get("/api/addresses/1CounterpartyXXXXXXXXXXXXXXXUWLpVr")
    assert dave_resp.status_code == 200
    dave = dave_resp.json()["data"]

    assert dave["addressId"] == "1CounterpartyXXXXXXXXXXXXXXXUWLpVr"
    assert dave["transactionCount"] == 2
    assert dave["totalReceivedBtc"] == "25.00000000"
    assert dave["totalSentBtc"] == "0.00000000"

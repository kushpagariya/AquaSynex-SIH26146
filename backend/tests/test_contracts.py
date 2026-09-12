"""Contract compliance tests for frontend, ML, and data contracts."""

import re
from fastapi.testclient import TestClient


BTC_8_DECIMAL_REGEX = re.compile(r"^\d+\.\d{8}$")


def test_frontend_response_envelope_success(client: TestClient):
    response = client.get("/api/health")
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    assert "data" in data
    assert "meta" in data
    assert "timestamp" in data["meta"]
    assert "requestId" in data["meta"]


def test_frontend_response_envelope_error(client: TestClient):
    response = client.get("/api/datasets/non-existent-uuid")
    data = response.json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "meta" in data
    assert "timestamp" in data["meta"]
    assert "requestId" in data["meta"]


def test_btc_values_are_always_8_decimal_strings(client: TestClient, seeded_db):
    # Test transactions endpoint
    res = client.get("/api/datasets/test-dataset-1/transactions")
    assert res.status_code == 200
    tx_list = res.json()["data"]

    for tx in tx_list:
        for field in ["totalInputValueBtc", "totalOutputValueBtc", "feeBtc"]:
            val = tx.get(field)
            if val is not None:
                assert isinstance(val, str), f"{field} is not a string: {val}"
                assert BTC_8_DECIMAL_REGEX.match(val), f"{field} does not match 8 decimals: {val}"

    # Test addresses endpoint
    addr_res = client.get("/api/datasets/test-dataset-1/addresses")
    assert addr_res.status_code == 200
    addr_list = addr_res.json()["data"]

    for addr in addr_list:
        for field in ["totalReceivedBtc", "totalSentBtc"]:
            val = addr.get(field)
            if val is not None:
                assert isinstance(val, str), f"{field} is not a string: {val}"
                assert BTC_8_DECIMAL_REGEX.match(val), f"{field} does not match 8 decimals: {val}"


def test_ml_result_schema_contract(client: TestClient, seeded_db):
    res = client.get("/api/analyses/test-analysis-1/results/addr-bob")
    assert res.status_code == 200
    data = res.json()["data"]

    assert 0.0 <= data["anomalyScore"] <= 1.0
    assert 0.0 <= data["riskScore"] <= 1.0
    assert data["riskLevel"] in ["low", "medium", "high", "critical"]
    assert "explanations" in data
    for exp in data["explanations"]:
        assert "featureName" in exp
        assert "shapValue" in exp
        assert exp["direction"] in ["increases_risk", "decreases_risk", "neutral"]
        assert 0.0 <= exp["normalizedImportance"] <= 1.0

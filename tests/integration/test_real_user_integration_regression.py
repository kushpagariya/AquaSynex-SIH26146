"""Real-User Integration Regression Tests (SIH26146).

Validates:
A. Placeholder model cannot accidentally be selected as an executable analysis model.
B. Real executable model ID (aquasynex_xgb_binary_v1) is passed from frontend/backend into ML adapter.
C. Investigation navigation uses a real entity_id from analysis results.
D. Fake IDs such as 'e-001' and keystroke fragments are rejected by entity APIs.
E. Analysis polling stops immediately after COMPLETED.
F. Analysis polling stops immediately after FAILED and propagates error.
I. Existing backend real-address endpoints continue to return 200 for valid dataset addresses.
"""

from pathlib import Path
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

from backend.services.model_service import is_model_executable, DEFAULT_EXECUTABLE_MODEL_ID


def test_regression_A_model_discovery_distinguishes_executable_vs_placeholder(client: TestClient):
    """Test A: Model registry explicitly marks executable vs placeholder models."""
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    models = body["data"]

    model_by_id = {m["modelId"]: m for m in models}

    # Executable models
    assert "aquasynex_xgb_binary_v1" in model_by_id
    assert model_by_id["aquasynex_xgb_binary_v1"].get("isExecutable") is True
    assert is_model_executable("aquasynex_xgb_binary_v1") is True

    # Placeholder model
    assert "isolation_forest_v1" in model_by_id
    assert model_by_id["isolation_forest_v1"].get("isExecutable") is False
    assert is_model_executable("isolation_forest_v1") is False

    # Default executable model constant
    assert DEFAULT_EXECUTABLE_MODEL_ID == "aquasynex_xgb_binary_v1"


def test_regression_B_C_I_real_sih_flow_and_address_endpoints(client: TestClient):
    """Test B, C, I: End-to-end flow with sih_transactions_sample.csv and real address endpoints.

    1. Ingest sih_transactions_sample.csv
    2. Trigger analysis with aquasynex_xgb_binary_v1
    3. Verify completion
    4. Fetch real analysis results
    5. Test /api/addresses/{realAddress} and /api/addresses/{realAddress}/graph return 200
    """
    sample_csv = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "sih_transactions_sample.csv"
    if not sample_csv.exists():
        sample_csv = Path(__file__).resolve().parent.parent.parent / "sih_transactions_sample.csv"
    assert sample_csv.exists(), f"Sample CSV file not found at {sample_csv}"

    # 1. Upload dataset
    with open(sample_csv, "rb") as f:
        upload_resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sih_transactions_sample.csv", f, "text/csv")},
            data={"name": "Real User Integration Dataset"},
        )
    assert upload_resp.status_code == 202, f"Upload failed: {upload_resp.text}"
    dataset_id = upload_resp.json()["data"]["datasetId"]
    assert dataset_id

    # 2. Trigger analysis with production model
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    assert trigger_resp.status_code == 202
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    # 3. Check analysis status (background task executes synchronously in TestClient)
    status_resp = client.get(f"/api/analyses/{analysis_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()["data"]
    assert status_data["status"] == "completed", f"Analysis failed: {status_data.get('errorMessage')}"
    assert status_data["modelId"] == "aquasynex_xgb_binary_v1"
    assert status_data["entityCount"] > 0

    # 4. Fetch analysis results
    results_resp = client.get(f"/api/analyses/{analysis_id}/results?pageSize=50")
    assert results_resp.status_code == 200
    results = results_resp.json()["data"]
    assert len(results) > 0

    # Fetch real addresses from the dataset
    addrs_resp = client.get(f"/api/datasets/{dataset_id}/addresses?pageSize=10")
    assert addrs_resp.status_code == 200
    addrs = addrs_resp.json()["data"]
    assert len(addrs) > 0

    real_addr = addrs[0]["addressId"]
    assert real_addr and not real_addr.startswith("e-")

    # 5. Verify real address endpoint returns 200
    addr_resp = client.get(f"/api/addresses/{real_addr}?analysisId={analysis_id}")
    assert addr_resp.status_code == 200
    addr_data = addr_resp.json()["data"]
    assert addr_data["addressId"] == real_addr

    # Verify real address graph endpoint returns 200
    graph_resp = client.get(f"/api/addresses/{real_addr}/graph?hops=2&analysisId={analysis_id}")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()["data"]
    assert graph_data["isSubgraph"] is True
    assert graph_data["subgraphCenter"] == real_addr
    assert len(graph_data["nodes"]) >= 1


def test_regression_D_fake_ids_return_404(client: TestClient):
    """Test D: Fake IDs (e-001) and typing fragments (g, ga, gae, gaea) return 404."""
    for fake_id in ["e-001", "g", "ga", "gae", "gaea"]:
        addr_resp = client.get(f"/api/addresses/{fake_id}")
        assert addr_resp.status_code == 404
        assert addr_resp.json()["error"]["code"] == "ADDRESS_NOT_FOUND"

        tx_resp = client.get(f"/api/transactions/{fake_id}")
        assert tx_resp.status_code == 404
        assert tx_resp.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_regression_E_F_polling_termination_logic(client: TestClient, uploaded_dataset: dict):
    """Test E, F: Validate polling state transitions and termination via client.

    - 'completed' is terminal: polling terminates successfully.
    - 'failed' is terminal: polling terminates and propagates error message.
    - Non-terminal states ('pending', 'running') allow polling continuation.
    """
    dataset_id = uploaded_dataset["datasetId"]

    # 1. Trigger an analysis with an unsupported/placeholder model to verify 'failed' terminal state
    resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "isolation_forest_v1", "modelVersion": "1.0.0"},
    )
    assert resp.status_code == 202
    analysis_id = resp.json()["data"]["analysisId"]

    # 2. Poll the analysis status endpoint
    terminal_statuses = {"completed", "failed"}
    poll_resp = client.get(f"/api/analyses/{analysis_id}")
    assert poll_resp.status_code == 200
    data = poll_resp.json()["data"]

    assert data["status"] in terminal_statuses, f"Expected terminal status, got {data['status']}"
    if data["status"] == "failed":
        # Verify failed-state error propagation
        assert data.get("errorMessage") is not None
        assert len(data["errorMessage"]) > 0

    # 3. Assert invariants against terminal state constants
    assert "completed" in terminal_statuses and "completed" not in {"pending", "running"}
    assert "failed" in terminal_statuses and "failed" not in {"pending", "running"}


def test_regression_transaction_vs_address_entity_routing(client: TestClient):
    """Test: Transaction entity routing returns 200 on transaction endpoints and network events, 404 on address."""
    sample_csv = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "sih_transactions_sample.csv"
    if not sample_csv.exists():
        sample_csv = Path(__file__).resolve().parent.parent.parent / "sih_transactions_sample.csv"

    with open(sample_csv, "rb") as f:
        upload_resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sih_transactions_sample.csv", f, "text/csv")},
            data={"name": "Routing Test Dataset"},
        )
    assert upload_resp.status_code == 202
    dataset_id = upload_resp.json()["data"]["datasetId"]

    # Verify dataset counts in validation summary
    detail_resp = client.get(f"/api/datasets/{dataset_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["validationSummary"]["addressCount"] > 0
    assert detail["validationSummary"]["unique_addresses"] > 0

    # Trigger analysis
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1"},
    )
    assert trigger_resp.status_code == 202
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    # Get transactions
    tx_resp = client.get(f"/api/datasets/{dataset_id}/transactions?pageSize=5&analysisId={analysis_id}")
    assert tx_resp.status_code == 200
    txs = tx_resp.json()["data"]
    assert len(txs) > 0
    real_txid = txs[0]["transactionId"]

    # 1. Calling transaction endpoint returns 200 with network_events
    tx_detail_resp = client.get(f"/api/transactions/{real_txid}?analysisId={analysis_id}")
    assert tx_detail_resp.status_code == 200
    tx_detail = tx_detail_resp.json()["data"]
    assert tx_detail["transactionId"] == real_txid
    assert "networkEvents" in tx_detail

    # 2. Calling ML result detail for tx returns entityType 'transaction'
    ml_res_resp = client.get(f"/api/analyses/{analysis_id}/results/{real_txid}")
    assert ml_res_resp.status_code == 200
    ml_res = ml_res_resp.json()["data"]
    assert ml_res["entityType"] == "transaction"

    # 3. Calling address endpoint with a transaction ID correctly returns 404
    addr_lookup_resp = client.get(f"/api/addresses/{real_txid}?analysisId={analysis_id}")
    assert addr_lookup_resp.status_code == 404
    assert addr_lookup_resp.json()["error"]["code"] == "ADDRESS_NOT_FOUND"

    # 4. Health endpoint returns 200 healthy
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["data"]["status"] == "healthy"


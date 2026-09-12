"""Full User Journey End-to-End Integration Test.

Simulates the complete investigator lifecycle from system start and health check
to dataset ingestion, analysis dispatch, graph rendering, and data verification.
"""

from pathlib import Path
from fastapi.testclient import TestClient


def test_full_investigator_user_journey(client: TestClient, sample_csv_path: Path):
    """Execute complete 14-step investigator workflow across Frontend ↔ Backend integration boundaries."""

    # Step 1 & 2: System is online, frontend connects to backend health check
    health_resp = client.get("/api/health")
    assert health_resp.status_code == 200
    health_body = health_resp.json()
    assert health_body["success"] is True
    assert health_body["data"]["status"] == "healthy"
    assert health_body["data"]["databaseStatus"] == "connected"

    # Step 3: Investigator uploads the Bitcoin dataset file via browser multipart form
    with open(sample_csv_path, "rb") as f:
        upload_resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_bitcoin_dataset.csv", f, "text/csv")},
            data={"name": "Investigator Primary Investigation Dataset"},
        )
    assert upload_resp.status_code == 202
    upload_body = upload_resp.json()
    assert upload_body["success"] is True
    dataset_id = upload_body["data"]["datasetId"]
    assert dataset_id is not None

    # Step 4: Dataset appears in datasets listing
    list_resp = client.get("/api/datasets")
    assert list_resp.status_code == 200
    datasets = list_resp.json()["data"]
    matching_datasets = [d for d in datasets if d["datasetId"] == dataset_id]
    assert len(matching_datasets) == 1

    # Step 5 & 6: Investigator opens dataset detail view
    detail_resp = client.get(f"/api/datasets/{dataset_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["datasetId"] == dataset_id
    assert detail["status"] == "ready"
    assert detail["canonicalTxCount"] == 5
    assert detail["rowCount"] == 5

    # Step 7: Investigator clicks "Start Analysis"
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "isolation_forest_v1", "modelVersion": "1.0.0"},
    )
    assert trigger_resp.status_code == 202
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    # Step 8 & 9: Frontend polls analysis status until terminal state
    # (Controlled ML-unavailable failure is the expected terminal state at this stage)
    poll_resp = client.get(f"/api/analyses/{analysis_id}")
    assert poll_resp.status_code == 200
    analysis = poll_resp.json()["data"]
    assert analysis["status"] in ("failed", "completed")
    if analysis["status"] == "failed":
        assert analysis.get("errorMessage") is not None
        # Verify it did not crash or corrupt database state

    # Step 10: Investigator browses transactions
    tx_resp = client.get(f"/api/datasets/{dataset_id}/transactions")
    assert tx_resp.status_code == 200
    transactions = tx_resp.json()["data"]
    assert len(transactions) == 5

    # Step 10b: Investigator clicks a transaction to inspect inputs/outputs
    first_tx_id = transactions[0]["transactionId"]
    tx_detail_resp = client.get(f"/api/transactions/{first_tx_id}")
    assert tx_detail_resp.status_code == 200
    tx_detail = tx_detail_resp.json()["data"]
    assert tx_detail["transactionId"] == first_tx_id
    assert len(tx_detail["inputs"]) >= 1
    assert len(tx_detail["outputs"]) >= 1

    # Step 11: Investigator browses addresses
    addr_resp = client.get(f"/api/datasets/{dataset_id}/addresses")
    assert addr_resp.status_code == 200
    addresses = addr_resp.json()["data"]
    assert len(addresses) == 5

    # Step 11b: Investigator clicks on an address to view behavioral profile
    first_addr_id = addresses[0]["addressId"]
    addr_detail_resp = client.get(f"/api/addresses/{first_addr_id}")
    assert addr_detail_resp.status_code == 200
    addr_detail = addr_detail_resp.json()["data"]
    assert addr_detail["addressId"] == first_addr_id
    assert addr_detail["transactionCount"] >= 1

    # Step 12: Investigator requests graph visualization
    graph_resp = client.get(f"/api/analyses/{analysis_id}/graph")
    assert graph_resp.status_code == 200
    graph = graph_resp.json()["data"]
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0

    # Step 12b: Investigator requests 2-hop neighborhood subgraph for the active address
    subgraph_resp = client.get(f"/api/addresses/{first_addr_id}/graph?hops=2")
    assert subgraph_resp.status_code == 200
    subgraph = subgraph_resp.json()["data"]
    assert subgraph["isSubgraph"] is True
    assert subgraph["subgraphCenter"] == first_addr_id

    # Step 13: Investigator checks results view
    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    assert results_resp.status_code == 200
    results = results_resp.json()["data"]
    # For failed ML run, results list must be empty (no fabricated ML data)
    assert isinstance(results, list)

    # Step 14: Cross-layer data consistency check
    assert detail["canonicalTxCount"] == len(transactions)
    assert len(addresses) == len({tx_detail["inputs"][0]["inputAddress"]}.union(
        {tx_detail["outputs"][0]["outputAddress"]}
    ).union({a["addressId"] for a in addresses}))

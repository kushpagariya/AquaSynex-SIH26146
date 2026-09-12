"""Graph API endpoint tests.

Verifies Cytoscape.js export schemas, address neighborhood subgraphs, and node/edge contracts.
"""

from fastapi.testclient import TestClient


def test_get_analysis_graph_contract(client: TestClient, uploaded_dataset: dict):
    """Verify GET /api/analyses/{analysisId}/graph returns valid Cytoscape node/edge contract."""
    dataset_id = uploaded_dataset["datasetId"]

    # Trigger analysis to have an analysis record
    trig_resp = client.post(f"/api/datasets/{dataset_id}/analyses", json={})
    analysis_id = trig_resp.json()["data"]["analysisId"]

    # Request graph for the analysis
    resp = client.get(f"/api/analyses/{analysis_id}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    graph = body["data"]
    assert graph["analysisId"] == analysis_id
    assert graph["datasetId"] == dataset_id
    assert "nodes" in graph
    assert "edges" in graph
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)

    # Validate node structure
    assert len(graph["nodes"]) > 0
    for node in graph["nodes"]:
        assert "id" in node
        assert "label" in node
        assert node.get("nodeType") == "address"
        assert "metadata" in node

    # Validate edge structure
    assert len(graph["edges"]) > 0
    for edge in graph["edges"]:
        assert "id" in edge
        assert "source" in edge
        assert "target" in edge
        assert edge.get("edgeType") == "transaction"
        assert "totalValueBtc" in edge
        assert "transactions" in edge


def test_get_address_subgraph_contract(client: TestClient, uploaded_dataset: dict):
    """Verify GET /api/addresses/{addressId}/graph returns N-hop neighborhood subgraph."""
    center_addr = "1BoatSLRHtKNngkdXEeobR76b53LETtpyT"

    resp = client.get(f"/api/addresses/{center_addr}/graph?hops=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True

    graph = body["data"]
    assert graph["isSubgraph"] is True
    assert graph["subgraphCenter"] == center_addr
    assert len(graph["nodes"]) >= 1

    # Verify center node is included in the graph
    node_ids = {n["id"] for n in graph["nodes"]}
    assert center_addr in node_ids


def test_graph_endpoints_unknown_entities_return_404(client: TestClient):
    """Verify requesting graph for non-existent analysis or address returns controlled error."""
    # Unknown analysis
    resp1 = client.get("/api/analyses/nonexistent-analysis-id/graph")
    assert resp1.status_code == 404
    assert resp1.json()["success"] is False

    # Unknown address
    resp2 = client.get("/api/addresses/nonexistent-address-id/graph")
    assert resp2.status_code == 404
    assert resp2.json()["success"] is False

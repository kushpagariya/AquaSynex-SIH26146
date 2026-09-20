"""API tests for graph visualization and export endpoints."""

from fastapi.testclient import TestClient


def test_get_analysis_graph(client: TestClient, seeded_db):
    response = client.get("/api/analyses/test-analysis-1/graph")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    graph = res["data"]
    assert "graphId" in graph
    assert graph["analysisId"] == "test-analysis-1"
    assert graph["isSubgraph"] is False
    assert len(graph["nodes"]) >= 2
    assert len(graph["edges"]) >= 1

    # Check node structure
    node = graph["nodes"][0]
    assert "id" in node
    assert "label" in node
    assert node["nodeType"] == "address"

    # Check edge structure
    edge = graph["edges"][0]
    assert "source" in edge
    assert "target" in edge
    assert "totalValueBtc" in edge
    assert "transactions" in edge


def test_get_address_subgraph(client: TestClient, seeded_db):
    response = client.get("/api/addresses/addr-bob/graph?hops=2")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    graph = res["data"]
    assert graph["isSubgraph"] is True
    assert graph["subgraphCenter"] == "addr-bob"
    assert len(graph["nodes"]) >= 1


def test_get_graph_neighborhood_txid_resolution(client: TestClient, seeded_db):
    """Test authoritative resolution of a TXID returning entityType=transaction and graph data."""
    response = client.get(
        "/api/graph/neighborhood?entityId=tx-001&analysisId=test-analysis-1&depth=2"
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]

    # Verify authoritative entity type resolution
    assert data["selectedEntity"]["entityId"] == "tx-001"
    assert data["selectedEntity"]["entityType"] == "transaction"
    assert data["selectedEntity"]["exists"] is True

    # Verify bipartite graph structure and counts
    assert data["summary"]["nodeCount"] >= 3  # tx-001 + input addr-alice + output addr-bob
    assert data["summary"]["edgeCount"] >= 2
    assert data["summary"]["transactionCount"] >= 1
    assert data["summary"]["addressCount"] >= 2

    # Verify selected node is present in nodes array
    tx_node = next((n for n in data["nodes"] if n["id"] == "tx-001"), None)
    assert tx_node is not None
    assert tx_node["nodeType"] == "transaction"
    assert "totalInputValueBtc" in tx_node["metadata"] or "amountBtc" in tx_node["metadata"]


def test_get_graph_neighborhood_address_resolution(client: TestClient, seeded_db):
    """Test authoritative resolution of an address returning entityType=address."""
    response = client.get(
        "/api/graph/neighborhood?entityId=addr-bob&analysisId=test-analysis-1&depth=2"
    )
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["selectedEntity"]["entityId"] == "addr-bob"
    assert data["selectedEntity"]["entityType"] == "address"
    assert data["summary"]["nodeCount"] >= 2


def test_get_address_subgraph_txid_fallback(client: TestClient, seeded_db):
    """Test backward compatibility fallback when /api/addresses/{id}/graph is called with a TXID."""
    response = client.get("/api/addresses/tx-001/graph?hops=2&analysisId=test-analysis-1")
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    graph = res["data"]
    assert graph["isSubgraph"] is True
    assert graph["subgraphCenter"] == "tx-001"
    assert len(graph["nodes"]) >= 2


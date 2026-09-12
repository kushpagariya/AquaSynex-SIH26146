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

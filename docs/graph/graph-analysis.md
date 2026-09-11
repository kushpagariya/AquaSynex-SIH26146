# Graph Analysis

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Analysis Goals

Graph analysis serves two purposes:

1. **Feature generation** — Produce numeric graph features per entity for the ML model.
2. **Structural insights** — Identify notable graph structures (clusters, hubs, bridges) for the investigator.

---

## 2. Implemented Analyses

### 2.1 Degree Analysis (`PLANNED`)

**Purpose**: Identify high-activity nodes (potential hubs, mixers, exchanges).

```python
in_degrees = dict(G.in_degree())
out_degrees = dict(G.out_degree())
weighted_in = dict(G.in_degree(weight='value_satoshi'))
weighted_out = dict(G.out_degree(weight='value_satoshi'))
```

**Investigative signal**:
- High in-degree with high weighted value: potential receiving hub (exchange address)
- High out-degree with many small outputs: potential dust/mixing attack
- High in-degree + high out-degree: mixing or routing node

---

### 2.2 PageRank (`PLANNED`)

**Purpose**: Identify structurally central nodes — addresses that appear on many transaction paths.

```python
pagerank_scores = nx.pagerank(G, alpha=0.85, weight='value_satoshi', max_iter=100)
```

**Investigative signal**:
- High PageRank: Address is frequently involved in value routing across the network.
- Anomalously high PageRank relative to transaction count: may indicate rapid pass-through transactions.

---

### 2.3 Connected Components (`PLANNED`)

**Purpose**: Identify the scale of an entity's associated network.

```python
weakly_connected = list(nx.weakly_connected_components(G))
component_sizes = {node: len(component) for component in weakly_connected for node in component}
```

**Investigative signal**:
- Large component membership: Address is part of a highly interconnected cluster.
- Small component (singleton or 2–3 nodes): Isolated address with few connections.

---

### 2.4 Betweenness Centrality (`CANDIDATE`)

**Purpose**: Identify addresses that serve as bridges between network clusters.

```python
betweenness = nx.betweenness_centrality(G, k=500, normalized=True, weight='value_satoshi')
```

**Status**: `CANDIDATE` — Expensive for large graphs. Only compute if graph has < 100K nodes or use approximation.

**Investigative signal**:
- High betweenness: Address acts as a critical routing point between otherwise disconnected parts of the network.

---

### 2.5 Neighborhood Analysis (`PLANNED` for API)

**Purpose**: For a specific flagged entity, return its N-hop neighborhood for the investigator to explore.

```python
def get_neighborhood(G: nx.DiGraph, center_node: str, hops: int = 2) -> nx.DiGraph:
    nodes = {center_node}
    for _ in range(hops):
        nodes.update(nx.single_source_shortest_path_length(G, center_node, cutoff=hops).keys())
    return G.subgraph(nodes).copy()
```

This subgraph is exported as the Cytoscape.js graph for the frontend.

---

## 3. Graph Analysis Output

After running all algorithms, produce a `graph_analysis_summary` for each analysis run:

```json
{
  "totalNodes": 45230,
  "totalEdges": 89431,
  "totalComponents": 1243,
  "largestComponentSize": 12450,
  "averageDegree": 3.95,
  "maxInDegree": 1842,
  "maxOutDegree": 923,
  "maxPagerank": 0.00234,
  "algorithmStatus": {
    "degree": "completed",
    "pagerank": "completed",
    "connectedComponents": "completed",
    "betweennessCentrality": "skipped_too_large"
  }
}
```

This summary is stored in the `analysis_runs` table.

---

## 4. What Graph Analysis Does NOT Claim

| Claim | Correct statement |
|---|---|
| High PageRank = suspicious | High PageRank = structurally central; requires investigator judgment |
| Large component = illegal network | Large component = interconnected addresses; may be a normal exchange |
| High degree = mixer | High degree = high-activity node; investigation required |

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner (Graph)*
*References: [graph-features.md](./graph-features.md) | [graph-schema.md](./graph-schema.md)*

# Graph Features

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> Graph features are computed by the Graph Layer and consumed by the ML Layer.
> Feature names here are canonical and must match [feature-specification.md](../ml/feature-specification.md).

**Status**: `PLANNED`

---

## 1. Feature Extraction Pipeline

```
NetworkX DiGraph (in-memory)
    │
    ├── Degree computation (all nodes)
    ├── Weighted degree computation
    ├── PageRank (all nodes)
    ├── Connected components (all nodes)
    └── [CANDIDATE] Betweenness centrality (sampled)
    │
    ▼
Graph Feature DataFrame
    index: address_id (string)
    columns: canonical graph feature names
    │
    ▼
Merge with tabular feature DataFrame
    │
    ▼
Combined Feature Matrix → ML Model
```

---

## 2. Computed Graph Features

### `graph_in_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_in_degree` |
| Formula | `G.in_degree(node)` |
| Type | `integer` |
| Status | `PLANNED` |
| NetworkX API | `G.in_degree()` |
| Notes | Number of incoming edges (sending addresses) |

---

### `graph_out_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_out_degree` |
| Formula | `G.out_degree(node)` |
| Type | `integer` |
| Status | `PLANNED` |
| NetworkX API | `G.out_degree()` |
| Notes | Number of outgoing edges (receiving addresses) |

---

### `graph_weighted_in_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_weighted_in_degree` |
| Formula | `sum(G[u][node]['value_satoshi'] for u in G.predecessors(node))` |
| Type | `float` (satoshis) |
| Status | `PLANNED` |
| NetworkX API | `G.in_degree(node, weight='value_satoshi')` |

---

### `graph_weighted_out_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_weighted_out_degree` |
| Formula | `sum(G[node][v]['value_satoshi'] for v in G.successors(node))` |
| Type | `float` (satoshis) |
| Status | `PLANNED` |
| NetworkX API | `G.out_degree(node, weight='value_satoshi')` |

---

### `graph_pagerank`

| Property | Value |
|---|---|
| Canonical name | `graph_pagerank` |
| Formula | `nx.pagerank(G, weight='value_satoshi')` |
| Type | `float` |
| Range | (0.0, 1.0) |
| Status | `PLANNED` |
| NetworkX API | `nx.pagerank(G, alpha=0.85, max_iter=100, tol=1e-6)` |
| Notes | Use `weight='value_satoshi'` to weight edges by BTC value |

---

### `graph_connected_component_size`

| Property | Value |
|---|---|
| Canonical name | `graph_connected_component_size` |
| Formula | `len(component containing node)` for weakly connected components |
| Type | `integer` |
| Status | `PLANNED` |
| NetworkX API | `nx.weakly_connected_components(G)` |

---

### `graph_betweenness_centrality`

| Property | Value |
|---|---|
| Canonical name | `graph_betweenness_centrality` |
| Formula | Fraction of shortest paths passing through node |
| Type | `float` |
| Status | `CANDIDATE` |
| NetworkX API | `nx.betweenness_centrality(G, k=500, normalized=True)` (sampled) |
| Notes | Expensive on large graphs. Only compute if graph has < 100K nodes, or use k-sampling. |

---

## 3. Feature DataFrame Format

```python
# Output DataFrame
graph_features: pd.DataFrame = pd.DataFrame({
    "entity_id": [...],                          # Bitcoin address
    "graph_in_degree": [...],                    # int
    "graph_out_degree": [...],                   # int
    "graph_weighted_in_degree": [...],           # float
    "graph_weighted_out_degree": [...],          # float
    "graph_pagerank": [...],                     # float
    "graph_connected_component_size": [...],     # int
})
# index: 0..N-1 (reset index)
```

---

## 4. Missing Node Handling

If an address in the canonical data is not in the graph (e.g., output-only address with no recorded inputs):

- Set all in-degree features to `0`
- Set all out-degree features to `0`
- Set `graph_pagerank` to the minimum observed value in the dataset
- Set `graph_connected_component_size` to `1` (singleton)

These are handled by the feature engineering imputation step, not the graph layer itself.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner (Graph)*
*References: [feature-specification.md](../ml/feature-specification.md) | [graph-construction.md](./graph-construction.md)*

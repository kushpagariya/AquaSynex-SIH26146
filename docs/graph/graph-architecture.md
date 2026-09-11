# Graph Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Overview

The graph layer builds a directed transaction graph from canonical Bitcoin transaction data and extracts graph-theoretic features that augment the ML model's behavioral analysis.

```
Canonical Transaction Records
    │
    ▼
Graph Construction (NetworkX DiGraph)
    │
    ├──► Graph Feature Extraction (per node)
    │         └──► Feature DataFrame → ML Layer
    │
    └──► Graph Topology Export (nodes + edges JSON)
              └──► Backend API → Frontend (Cytoscape.js)
```

---

## 2. Technology

**Primary library**: `networkx` (Python)

NetworkX provides:
- Directed graph (`DiGraph`) data structure
- Degree computation
- PageRank algorithm
- Connected components
- Centrality algorithms (betweenness, closeness)
- Path analysis

**Graph is in-memory only** in Phase 1. It is reconstructed per analysis run from canonical DuckDB records. No graph database is used. See [ADR-001](../decisions/ADR-001-duckdb-selection.md).

---

## 3. Graph Entity Model

### Nodes: Bitcoin Addresses

Each unique Bitcoin address observed in the dataset is a **node**.

```
Node properties:
    - id: str                  # Bitcoin address string
    - node_type: str           # "address"
    - first_seen: datetime     # Earliest transaction
    - last_seen: datetime      # Latest transaction
    - transaction_count: int   # Transactions involving this address
    - total_received: int      # Total satoshis received
    - total_sent: int          # Total satoshis sent
```

### Edges: Transaction Value Flows

A directed edge from node A to node B represents a **value flow** from address A to address B through one or more transactions.

```
Edge properties:
    - id: str                          # {source}→{target} or specific edge ID
    - source: str                      # Input address
    - target: str                      # Output address
    - transaction_id: str              # If single transaction
    - value_satoshi: int               # BTC value transferred (satoshis)
    - timestamp: datetime              # Transaction timestamp (earliest if aggregated)
    - edge_type: str                   # "transaction" | "aggregated"
    - transaction_count: int           # Number of transactions on this edge (if aggregated)
```

---

## 4. Graph Directionality

The graph is **directed**:

```
Address A ──(value flow)──► Address B
```

This represents: "Address A sent Bitcoin to Address B."

The direction is from **input address** to **output address** via the transaction.

**For transactions with multiple inputs and outputs**, one edge is created per (input_address, output_address) pair in a transaction, OR edges are aggregated — see [graph-construction.md](./graph-construction.md).

---

## 5. Edge Aggregation Strategy

`DECISION REQUIRED`: Should edges be:

**Option A**: One edge per transaction output (raw representation)
- Pros: Precise; each edge maps to one output
- Cons: Large graph for high-volume addresses

**Option B**: Aggregated edges (one edge per address pair)
- Pros: Smaller graph; shows total flow between address pairs
- Cons: Loses per-transaction detail

**Proposed default**: Option A for graph construction, Option B for Cytoscape.js visualization. `DECISION REQUIRED`.

---

## 6. Graph Scale Considerations

| Dataset Size | Estimated Nodes | Estimated Edges | NetworkX feasibility |
|---|---|---|---|
| 10K transactions | ~20K | ~40K | ✅ Fast |
| 100K transactions | ~200K | ~400K | ✅ Feasible |
| 1M transactions | ~2M | ~4M | ⚠️ PageRank slow; sample or limit |
| 10M transactions | ~20M | ~40M | ❌ In-memory NetworkX at limit |

**For large datasets**, the following strategies apply:
- Compute graph features on a subgraph (e.g., top N addresses by volume)
- Use approximate algorithms for PageRank (damping factor, max iterations)
- Export only the subgraph around flagged entities for visualization

`DECISION REQUIRED`: Define the subgraph strategy for large datasets.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner (Graph)*
*References: [graph-schema.md](./graph-schema.md) | [graph-construction.md](./graph-construction.md) | [graph-features.md](./graph-features.md)*

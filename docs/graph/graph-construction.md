# Graph Construction

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Input

Graph construction consumes canonical transaction records from DuckDB/Parquet.

**Required canonical fields** (analysis capability depends on availability):

| Field | Required for graph? |
|---|---|
| `transaction_id` | Yes |
| `output_address` | Yes (nodes cannot be created without addresses) |
| `input_address` | Preferred (edges require input addresses) |
| `output_value_satoshi` | Preferred (edge weights) |
| `timestamp` | Preferred (temporal analysis) |

If `output_address` is unavailable, graph construction is disabled and a warning is recorded in the analysis run.

---

## 2. Construction Algorithm

```python
import networkx as nx

def build_transaction_graph(
    transactions: list[dict],
    transaction_inputs: list[dict],
    transaction_outputs: list[dict],
) -> nx.DiGraph:
    
    G = nx.DiGraph()
    
    # Phase 1: Add address nodes
    for output in transaction_outputs:
        if output["output_address"]:
            G.add_node(output["output_address"], node_type="address")
    for inp in transaction_inputs:
        if inp["input_address"] and inp["input_address"] not in G:
            G.add_node(inp["input_address"], node_type="address")
    
    # Phase 2: Add transaction edges
    # For each transaction, create edges from each input address to each output address
    tx_inputs_map = group_by_transaction(transaction_inputs)
    tx_outputs_map = group_by_transaction(transaction_outputs)
    
    for tx in transactions:
        tx_id = tx["transaction_id"]
        inputs = tx_inputs_map.get(tx_id, [])
        outputs = tx_outputs_map.get(tx_id, [])
        
        for inp in inputs:
            src = inp.get("input_address")
            if not src:
                continue
            for out in outputs:
                tgt = out.get("output_address")
                if not tgt:
                    continue
                # Add or update edge
                if G.has_edge(src, tgt):
                    G[src][tgt]["value_satoshi"] += (out.get("output_value_satoshi") or 0)
                    G[src][tgt]["transaction_count"] += 1
                    G[src][tgt]["transactions"].append(tx_id)
                else:
                    G.add_edge(
                        src, tgt,
                        value_satoshi=(out.get("output_value_satoshi") or 0),
                        transaction_count=1,
                        transactions=[tx_id],
                        timestamp=tx.get("timestamp"),
                    )
    
    return G
```

> **Status**: This is the proposed algorithm. Implementation may refine it for performance.

---

## 3. Handling Missing Input Addresses

When input addresses are unknown (common in datasets without raw input detail):

**Option A**: Create a synthetic "unknown" node per transaction and connect to outputs.
- Node ID: `"unknown:{transaction_id}"`
- Downside: Creates many pseudo-nodes that inflate degree metrics

**Option B**: Create output-only address nodes without incoming edges.
- Nodes are created; in-degree is 0 for all.
- Graph is a DAG with no cross-transaction connections.

**Proposed default**: Option B. Address nodes are created from outputs only. In-degree graph features will be 0 or unavailable.

`DECISION REQUIRED`: Confirm Option B is acceptable.

---

## 4. Graph Enrichment with Node Attributes

After construction, node attributes are populated from the canonical address table:

```python
for node_id in G.nodes():
    address_data = address_lookup[node_id]
    G.nodes[node_id].update({
        "transaction_count": address_data.get("transaction_count", 0),
        "total_received_satoshi": address_data.get("total_received_satoshi", 0),
        "total_sent_satoshi": address_data.get("total_sent_satoshi", 0),
        "first_seen": address_data.get("first_seen_timestamp"),
        "last_seen": address_data.get("last_seen_timestamp"),
    })
```

---

## 5. Graph Size Management

For large graphs (>500K nodes), full algorithm execution may be slow.

**PageRank** — Use `max_iter=100` and `tol=1e-6`. For very large graphs, use the power iteration with convergence check.

**Betweenness centrality** — Sample-based approximation: `nx.betweenness_centrality(G, k=500)` where k is the number of sampled nodes.

`DECISION REQUIRED`: Define the size threshold above which approximations are used.

---

## 6. Graph Persistence Strategy

**Phase 1**: Graph is **in-memory only** and reconstructed per analysis run. No graph serialization to disk.

**Future**: If graph reconstruction becomes a bottleneck, consider:
- Serializing the graph to GraphML or GEXF format
- Caching graph in memory for the duration of an analysis session
- Using a graph summary in DuckDB (node/edge tables)

`FUTURE` consideration — not implemented in Phase 1.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner (Graph)*
*References: [graph-schema.md](./graph-schema.md) | [graph-features.md](./graph-features.md) | [canonical-schema.md](../data/canonical-schema.md)*

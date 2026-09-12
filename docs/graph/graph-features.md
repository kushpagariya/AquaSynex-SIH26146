# Graph Features & Link Analysis Specification (Phase 2.4)

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Authoritative Specification**: Graph features are derived from the bipartite directed graph (`Address → Transaction → Address`) and consumed by the ML Layer.
> All features in the ML feature set are strictly historical ($t < T_{\text{tx}}$ or $t \le T_{\text{tx}}$ snapshot) to prevent temporal data leakage.

**Status**: `IMPLEMENTED`

---

## 1. Feature Extraction Pipeline & Temporal Boundaries

```
Canonical Parquet / DuckDB
    │
    ▼
Chronological Stream (sorted by timestamp_epoch_sec)
    │
    ├── [1] Entity Clustering (Multi-Input & Change Heuristics)
    │       Captured BEFORE updating cluster state (t < T_tx)
    │       ──> hist_cluster_id, hist_cluster_size, hist_cluster_tx_count
    │
    ├── [2] Historical Degree Tracking
    │       Incident edges observed prior to current tx (t < T_tx)
    │       ──> hist_in_mean_neighbor_degree, hist_out_mean_neighbor_degree
    │
    ├── [3] Address Reuse Tracking
    │       Inputs previously observed prior to tx (t < T_tx)
    │       ──> hist_address_reuse_ratio
    │
    ├── [4] Bipartite Graph Snapshot (t <= T_tx)
    │       Component state as-of transaction execution
    │       ──> hist_component_size
    │
    └── [5] Transaction Local Topology (intrinsic to tx)
            ──> graph_fan_in, graph_fan_out, graph_unique_in_addrs, graph_unique_out_addrs
    │
    ▼
Graph Feature Table: data/processed/graph/graph_features.parquet
    (10,000 rows x 12 columns: 1 key + 11 features)
```

---

## 2. Canonical ML Graph Feature Catalog (11 Features + 1 Key)

| Column Name | Type | Temporal Scope | Description | Anti-Leakage Rationale |
|---|---|---|---|---|
| `transaction_id` | `VARCHAR` | N/A | Primary key matching `canonical_transactions`. | Deterministic identifier. |
| `graph_fan_in` | `BIGINT` | $T_{\text{tx}}$ | Total count of inputs to transaction node. | Intrinsic to transaction structure. |
| `graph_fan_out` | `BIGINT` | $T_{\text{tx}}$ | Total count of outputs from transaction node. | Intrinsic to transaction structure. |
| `graph_unique_in_addrs` | `BIGINT` | $T_{\text{tx}}$ | Count of distinct input addresses. | Intrinsic to transaction structure. |
| `graph_unique_out_addrs` | `BIGINT` | $T_{\text{tx}}$ | Count of distinct output addresses. | Intrinsic to transaction structure. |
| `hist_in_mean_neighbor_degree` | `DOUBLE` | $t < T_{\text{tx}}$ | Average degree of input addresses strictly before $T_{\text{tx}}$. | Evaluated only from prior transactions; never sees future activity. |
| `hist_out_mean_neighbor_degree` | `DOUBLE` | $t < T_{\text{tx}}$ | Average degree of output addresses strictly before $T_{\text{tx}}$. | Evaluated only from prior transactions; never sees future activity. |
| `hist_component_size` | `BIGINT` | $t \le T_{\text{tx}}$ | Size (node count) of weakly connected component at timestamp. | Bipartite component evaluated at snapshot; future connections do not back-propagate. |
| `hist_address_reuse_ratio` | `DOUBLE` | $t < T_{\text{tx}}$ | Proportion of input addresses previously observed in stream. | Strict historical lookback. |
| `hist_cluster_id` | `VARCHAR` | $t < T_{\text{tx}}$ | Primary input address cluster root prior to transaction. | Captured before unioning inputs or change outputs. |
| `hist_cluster_size` | `BIGINT` | $t < T_{\text{tx}}$ | Distinct address count in primary cluster prior to transaction. | Captured before unioning inputs or change outputs. |
| `hist_cluster_tx_count` | `BIGINT` | $t < T_{\text{tx}}$ | Cumulative transaction count of cluster prior to transaction. | Incremented only after feature recording. |

---

## 3. Post-Hoc Macroscopic Metrics (Strictly Quarantined from ML)

The following metrics require the complete, aggregate graph topology. Incorporating them into transaction-level feature matrices constitutes **catastrophic temporal leakage** (future graph topology leaking into past events).

They are computed exclusively by `ml/graph_analysis/graph_metrics.py` and exported to `data/processed/graph/graph_summary.json` for architectural verification:

1. **Full-Graph PageRank (`graph_pagerank`)**:
   - Computes stationary state across the entire transaction dataset.
   - Quarantined: Exported in `graph_summary.json` and visualized in exploratory notebooks only.
2. **Static Giant Component Membership (`is_giant_component`)**:
   - In a full retrospective graph, almost all active nodes coalesce into a single giant component.
   - Quarantined: Replaced in ML by `hist_component_size` (snapshot $t \le T_{\text{tx}}$).
3. **Full-Graph Louvain Modularity Communities**:
   - Macroscopic partition of the entire transaction network into dense behavioral communities.

---

## 4. Integration with Tabular Feature Matrix

In Phase 2.5 (Feature Store Integration), `graph_features.parquet` is joined on `transaction_id` with `feature_matrix_v1.parquet` (40 tabular features). While the graph pipeline exports 11 total columns for analytical observability, exactly 6 are selected as predictive ML features (excluding `hist_cluster_id` and the four duplicate retrospective topology fields):

$$\text{Combined Feature Space} = 40 \text{ Tabular Features} + 6 \text{ Predictive Graph Features} = 46 \text{ Frozen Features}$$

---

*Last updated: 2026-09-12 | Status: IMPLEMENTED | Owner: ML Owner (Graph)*

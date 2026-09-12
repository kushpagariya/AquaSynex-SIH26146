# AquaSynex — Graph Analysis & Link Analysis (Phase 2.4)
**SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## 1. Overview & Architecture

The `ml/graph_analysis/` package constructs and analyzes the Bitcoin transaction network derived from the canonical dataset (`data/processed/canonical/`).

Bitcoin transactions do not connect addresses directly; rather, they form a **directed bipartite graph**:
$$\text{Address } \xrightarrow{\text{INPUT\_TO}} \text{Transaction } \xrightarrow{\text{OUTPUT\_TO}} \text{Address}$$

Preserving this bipartite structure guarantees that multi-input and multi-output transaction topologies, transaction fees, and exact value splits remain completely faithful without lossy address-to-address projection.

---

## 2. Module Directory

| Module | Core Responsibility | Anti-Leakage Boundary |
|---|---|---|
| `graph_builder.py` | Constructs `nx.DiGraph` bipartite network; exports `nodes.parquet` & `edges.parquet`. | Topological structure representation. |
| `entity_clustering.py` | Streaming chronological Union-Find clustering using Multi-Input and Change heuristics. | Strictly chronological state evolution ($t < T_{\text{tx}}$ for feature capture). |
| `graph_features.py` | Extracts 11 ML-safe historical graph features per transaction. | Future-invariant ($t < T_{\text{tx}}$ or $t \le T_{\text{tx}}$ snapshot). |
| `graph_metrics.py` | Computes full-graph macroscopic statistics (PageRank, giant components, degree percentiles, Louvain communities). | **Strictly Post-Hoc**: Exported to `graph_summary.json` only; NEVER fed to ML models. |

---

## 3. Strict Temporal Anti-Leakage Rules

In longitudinal financial graphs, calculating topological metrics over the aggregated or future graph creates catastrophic temporal data leakage. AquaSynex implements four non-negotiable boundaries:

1. **Quarantined Macroscopic Metrics**: Full-graph PageRank and static giant component membership are classified as post-hoc exploratory metrics. They are saved in `data/processed/graph/graph_summary.json` and inspected in notebooks, but are barred from `graph_features.parquet`.
2. **Strict Chronological Clustering**: Transactions are processed in timestamp order. For transaction $T$ at time $t$, features (`hist_cluster_id`, `hist_cluster_size`, `hist_cluster_tx_count`) are captured *before* applying the transaction's unions or updating its activity count.
3. **Historical Node Degrees**: `hist_in_mean_neighbor_degree` and `hist_out_mean_neighbor_degree` average the degrees of addresses based strictly on prior transaction observations ($t < T_{\text{tx}}$).
4. **Historical Component Size**: `hist_component_size` is calculated on the snapshot graph $G_{\le t}$ at the time of the transaction. Future edges do not retroactively increase the component size recorded for $T$.

---

## 4. Entity Clustering Heuristics & Terminology

### Heuristics Applied
1. **Multi-Input (Common Spending) Heuristic**: All distinct addresses consumed as inputs in transaction $T$ are inferred to be co-controlled by the same behavioral entity.
2. **Change Address Heuristic**: Output addresses marked as change (`is_change == True`) are linked to the spending cluster.

### Neutral Terminology Mandate
Graph analysis tools infer cluster co-control through structural graph heuristics. Outputs are officially documented as:
- **"Inferred Behavioral Cluster"** or **"Address Cluster"**
- Clusters represent algorithmic groupings of co-spent addresses.
- They **do not** prove legal identity, real-world ownership, or illicit culpability.

---

## 5. Canonical Graph Feature Catalog (11 Features + 1 Key)

| Feature Name | Type | Temporal Scope | Description |
|---|---|---|---|
| `transaction_id` | `VARCHAR` | N/A | Canonical transaction identifier (Primary Key). |
| `graph_fan_in` | `BIGINT` | $T_{\text{tx}}$ | In-degree of transaction node (count of inputs). |
| `graph_fan_out` | `BIGINT` | $T_{\text{tx}}$ | Out-degree of transaction node (count of outputs). |
| `graph_unique_in_addrs` | `BIGINT` | $T_{\text{tx}}$ | Distinct count of input addresses. |
| `graph_unique_out_addrs` | `BIGINT` | $T_{\text{tx}}$ | Distinct count of output addresses. |
| `hist_in_mean_neighbor_degree` | `DOUBLE` | $t < T_{\text{tx}}$ | Mean degree of incoming address nodes prior to transaction. |
| `hist_out_mean_neighbor_degree` | `DOUBLE` | $t < T_{\text{tx}}$ | Mean degree of outgoing address nodes prior to transaction. |
| `hist_component_size` | `BIGINT` | $t \le T_{\text{tx}}$ | Connected component size in bipartite snapshot graph $G_t$. |
| `hist_address_reuse_ratio` | `DOUBLE` | $t < T_{\text{tx}}$ | Ratio of input addresses previously observed in the stream. |
| `hist_cluster_id` | `VARCHAR` | $t < T_{\text{tx}}$ | Identifier of primary input behavioral cluster before transaction. |
| `hist_cluster_size` | `BIGINT` | $t < T_{\text{tx}}$ | Number of addresses in primary input cluster before transaction. |
| `hist_cluster_tx_count` | `BIGINT` | $t < T_{\text{tx}}$ | Prior transaction count of input cluster before transaction. |

---

## 6. Execution & Verification

Run the end-to-end graph pipeline via CLI:
```bash
python -m ml.graph_analysis.run_pipeline
```
Or execute through unit tests:
```bash
pytest tests/ml/test_graph_analysis.py
```

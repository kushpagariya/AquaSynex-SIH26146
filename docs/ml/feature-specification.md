# Feature Specification

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative feature definition document.**
> Feature names defined here are canonical and must be used consistently across the ML pipeline, backend storage, and frontend explainability display.

---

## Feature Status Labels

| Label | Meaning |
|---|---|
| `IMPLEMENTED` | Code exists and is tested |
| `PLANNED` | Agreed; will be implemented |
| `CANDIDATE` | Under consideration; not yet approved |
| `DATASET_DEPENDENT` | Only possible if the dataset contains the required raw fields |
| `RESEARCH_REQUIRED` | Needs further validation before inclusion |

---

## Feature Schema Version

**Current version**: `v1.0.0` (`IN PROGRESS`)

All ML model artifacts must record which feature schema version they were trained on. See [model-versioning.md](./model-versioning.md).

---

## 1. Transaction-Level Features

These features are computed per transaction.

### `tx_input_count`

| Property | Value |
|---|---|
| Canonical name | `tx_input_count` |
| Type | `integer` |
| Unit | count |
| Formula | `COUNT(transaction_inputs WHERE transaction_id = tx)` or `transactions.input_count` |
| Status | `PLANNED` |
| Dataset required | At minimum `input_count` field |
| Missing value | `null` → impute with dataset median |
| Normalized | Yes (MinMaxScaler) |
| Used by graph | No |
| Used by ML | Yes |
| Explainable | Yes — "Number of transaction inputs" |
| Expected range | [1, 10000] |
| Investigative meaning | Coinjoins and mixing transactions tend to have many inputs |

---

### `tx_output_count`

| Property | Value |
|---|---|
| Canonical name | `tx_output_count` |
| Type | `integer` |
| Unit | count |
| Formula | `COUNT(transaction_outputs WHERE transaction_id = tx)` or `transactions.output_count` |
| Status | `PLANNED` |
| Normalized | Yes |
| Explainable | Yes — "Number of transaction outputs" |
| Expected range | [1, 5000] |
| Investigative meaning | Very high output counts may indicate mixing or dust attacks |

---

### `tx_total_value_satoshi`

| Property | Value |
|---|---|
| Canonical name | `tx_total_value_satoshi` |
| Type | `integer` (satoshis) |
| Unit | satoshis |
| Formula | `transactions.total_output_value_satoshi` |
| Status | `PLANNED` |
| Dataset required | `total_output_value_satoshi` |
| Normalized | Yes (log-scale before normalization due to wide range) |
| Explainable | Yes — "Total transaction value" |

---

### `tx_fee_satoshi`

| Property | Value |
|---|---|
| Canonical name | `tx_fee_satoshi` |
| Type | `integer` (satoshis) |
| Formula | `transactions.fee_satoshi` |
| Status | `PLANNED` |
| Dataset required | `fee_satoshi` or derivable |
| Normalized | Yes (log-scale) |
| Explainable | Yes — "Transaction fee" |
| Investigative meaning | Unusually high fees can indicate urgency or obfuscation |

---

### `tx_fee_rate_sat_per_byte`

| Property | Value |
|---|---|
| Canonical name | `tx_fee_rate_sat_per_byte` |
| Type | `float` |
| Unit | satoshis per byte |
| Formula | `fee_satoshi / transaction_size_bytes` |
| Status | `CANDIDATE` |
| Dataset required | `fee_satoshi` + `transaction_size_bytes` |
| Normalized | Yes |
| Explainable | Yes |

---

### `tx_value_balance_ratio`

| Property | Value |
|---|---|
| Canonical name | `tx_value_balance_ratio` |
| Type | `float` |
| Unit | ratio [0.0, 1.0] |
| Formula | `total_output_value_satoshi / total_input_value_satoshi` |
| Status | `CANDIDATE` |
| Dataset required | Both input and output values |
| Missing value | null if either is unavailable |
| Normalized | Already bounded [0, 1] |
| Explainable | Yes — "Input/output value balance" |

---

## 2. Address-Level Behavioral Features

These features are computed per Bitcoin address, aggregated from all transactions in the dataset.

### `addr_transaction_count`

| Property | Value |
|---|---|
| Canonical name | `addr_transaction_count` |
| Type | `integer` |
| Formula | `COUNT(DISTINCT transaction_id) WHERE address appears in inputs or outputs` |
| Status | `PLANNED` |
| Normalized | Yes (log) |
| Explainable | Yes — "Total transactions involving this address" |
| Investigative meaning | Unusually high activity can indicate exchange or mixer |

---

### `addr_total_received_satoshi`

| Property | Value |
|---|---|
| Canonical name | `addr_total_received_satoshi` |
| Type | `integer` (satoshis) |
| Formula | `SUM(output_value_satoshi) WHERE output_address = addr` |
| Status | `PLANNED` |
| Dataset required | `output_address` + `output_value_satoshi` |
| Normalized | Yes (log) |
| Explainable | Yes — "Total BTC received" |

---

### `addr_total_sent_satoshi`

| Property | Value |
|---|---|
| Canonical name | `addr_total_sent_satoshi` |
| Type | `integer` (satoshis) |
| Formula | `SUM(input_value_satoshi) WHERE input_address = addr` |
| Status | `PLANNED` |
| Dataset required | `input_address` + `input_value_satoshi` |
| Normalized | Yes (log) |
| Explainable | Yes — "Total BTC sent" |

---

### `addr_net_flow_satoshi`

| Property | Value |
|---|---|
| Canonical name | `addr_net_flow_satoshi` |
| Type | `integer` (satoshis, can be negative) |
| Formula | `total_received_satoshi - total_sent_satoshi` |
| Status | `PLANNED` |
| Normalized | Yes (symmetric log) |
| Explainable | Yes — "Net BTC flow" |

---

### `addr_unique_counterparties`

| Property | Value |
|---|---|
| Canonical name | `addr_unique_counterparties` |
| Type | `integer` |
| Formula | Count of distinct addresses that sent to or received from this address |
| Status | `CANDIDATE` |
| Normalized | Yes |
| Explainable | Yes — "Number of unique counterparties" |

---

### `addr_avg_tx_value_satoshi`

| Property | Value |
|---|---|
| Canonical name | `addr_avg_tx_value_satoshi` |
| Type | `float` (satoshis) |
| Formula | `total_received_satoshi / addr_transaction_count` |
| Status | `PLANNED` |
| Normalized | Yes (log) |
| Explainable | Yes — "Average transaction value" |

---

## 3. Temporal Features

These features capture time-based behavioral patterns.

### `addr_first_seen_timestamp`

| Property | Value |
|---|---|
| Canonical name | `addr_first_seen_timestamp` |
| Type | `datetime (UTC)` |
| Formula | `MIN(timestamp) WHERE address involved` |
| Status | `DATASET_DEPENDENT` (requires timestamp field) |
| Used by ML | Derived to compute duration |
| Explainable | No (timestamp itself); Yes (derived duration) |

---

### `addr_active_days`

| Property | Value |
|---|---|
| Canonical name | `addr_active_days` |
| Type | `integer` |
| Formula | `(last_seen_timestamp - first_seen_timestamp).days + 1` |
| Status | `DATASET_DEPENDENT` |
| Normalized | Yes |
| Explainable | Yes — "Days active" |
| Investigative meaning | Short activity windows with high transaction counts are suspicious |

---

### `addr_tx_per_day`

| Property | Value |
|---|---|
| Canonical name | `addr_tx_per_day` |
| Type | `float` |
| Formula | `addr_transaction_count / addr_active_days` |
| Status | `DATASET_DEPENDENT` |
| Normalized | Yes |
| Explainable | Yes — "Transaction velocity (per day)" |

---

### `addr_velocity_spike`

| Property | Value |
|---|---|
| Canonical name | `addr_velocity_spike` |
| Type | `float` |
| Formula | `max_daily_tx_count / mean_daily_tx_count` |
| Status | `CANDIDATE` |
| Notes | Requires time-windowed aggregation |
| Explainable | Yes — "Transaction activity spike ratio" |

---

## 4. Graph Topology Features

These features are produced by the Graph Layer (NetworkX) and consumed by the ML layer.

### `graph_in_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_in_degree` |
| Type | `integer` |
| Formula | Number of incoming edges to this address node |
| Status | `PLANNED` |
| Producer | Graph Layer |
| Consumer | ML Layer |
| Normalized | Yes |
| Explainable | Yes — "Number of incoming transaction connections" |

---

### `graph_out_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_out_degree` |
| Type | `integer` |
| Formula | Number of outgoing edges from this address node |
| Status | `PLANNED` |
| Normalized | Yes |
| Explainable | Yes — "Number of outgoing transaction connections" |

---

### `graph_weighted_in_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_weighted_in_degree` |
| Type | `float` (satoshis) |
| Formula | Sum of edge weights (values) on incoming edges |
| Status | `PLANNED` |
| Normalized | Yes (log) |
| Explainable | Yes — "Total BTC received via graph connections" |

---

### `graph_weighted_out_degree`

| Property | Value |
|---|---|
| Canonical name | `graph_weighted_out_degree` |
| Type | `float` (satoshis) |
| Formula | Sum of edge weights on outgoing edges |
| Status | `PLANNED` |
| Normalized | Yes (log) |
| Explainable | Yes — "Total BTC sent via graph connections" |

---

### `graph_pagerank`

| Property | Value |
|---|---|
| Canonical name | `graph_pagerank` |
| Type | `float` |
| Range | [0.0, 1.0] (approx) |
| Formula | NetworkX `pagerank(G)` value for this node |
| Status | `PLANNED` |
| Normalized | Yes |
| Explainable | Yes — "Network influence / centrality score" |
| Investigative meaning | High PageRank nodes are central to many transaction flows |

---

### `graph_betweenness_centrality`

| Property | Value |
|---|---|
| Canonical name | `graph_betweenness_centrality` |
| Type | `float` |
| Formula | NetworkX `betweenness_centrality(G)` for this node |
| Status | `CANDIDATE` |
| Notes | Expensive to compute for large graphs; may need sampling |
| Explainable | Yes — "How often this address lies on shortest paths between others" |

---

### `graph_connected_component_size`

| Property | Value |
|---|---|
| Canonical name | `graph_connected_component_size` |
| Type | `integer` |
| Formula | Size of the weakly connected component containing this node |
| Status | `PLANNED` |
| Normalized | Yes (log) |
| Explainable | Yes — "Size of associated network cluster" |

---

## 5. Feature Vector Schema

The final feature vector fed to the ML model is a Pandas DataFrame row with columns named using the canonical feature names above.

**Feature vector record**:
```python
{
    "entity_id": "bc1q...",              # Not a model feature; identifier
    "entity_type": "address",            # Not a model feature; identifier
    "dataset_id": "uuid...",             # Not a model feature; identifier
    "tx_input_count": 3,
    "tx_output_count": 5,
    "tx_total_value_satoshi": 500000000,
    "addr_transaction_count": 142,
    "addr_total_received_satoshi": 1200000000,
    "addr_active_days": 30,
    "addr_tx_per_day": 4.73,
    "graph_in_degree": 12,
    "graph_out_degree": 8,
    "graph_pagerank": 0.00312,
    "graph_connected_component_size": 450,
    # ... additional features
}
```

Fields prefixed `tx_` that are address-level features contain aggregated values (e.g., mean `tx_input_count` across all transactions involving this address).

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: ML Owner*
*References: [model-input-contract.md](./model-input-contract.md) | [graph-features.md](../graph/graph-features.md) | [data-dictionary.md](../data/data-dictionary.md)*

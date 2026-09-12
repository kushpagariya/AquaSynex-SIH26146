# AquaSynex Synthetic Development Dataset (SIH26146)

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Official Disclaimer**:
> This dataset is a project-generated synthetic development dataset inspired by the SIH26146 problem statement.
> It contains **no real identities, no real wallet ownership claims, no real people, and no real criminal data**.
> All hashes, addresses, IP addresses, ASNs, amounts, timestamps, and graph topologies are generated deterministically for offline software development, pipeline benchmarking, and algorithm evaluation.

---

## 1. Purpose & Motivation

In the SIH26146 competition problem statement (*AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic*), the problem statement explicitly specifies:
- `Dataset Link: Nil`
- *"Participants will work with a synthetic dataset modelled on real Bitcoin P2P/transaction fields (no real seized or live-intercept data will be provided)."*
- Minimum required fields: `timestamp`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `txid`, `input_addresses[]`, `output_addresses[]`, `input_amounts[]`, `output_amounts[]`, `fee`, `script_type`, `country`, `asn`.

Because the official test dataset is distributed during final evaluation, this synthetic development dataset provides our offline team with a realistic transaction and network graph to build, test, and benchmark:
1. **Data Ingestion & DuckDB Pipelines**: Ingesting bulk Parquet files into analytical tables without precision loss.
2. **Feature Engineering**: Computing behavioral metrics (fan-in, fan-out, velocity, active days, fee ratios).
3. **Graph Construction (NetworkX)**: Generating address-to-transaction and address-to-address directed multigraphs.
4. **AI/ML Use Cases**: Preparing feature vectors for entity clustering, anomaly detection, peeling-chain detection, and risk scoring.
5. **Dashboard & Visualization**: Verifying Cytoscape.js link-analysis views and alert ranking.

---

## 2. Dataset Architecture & Schemas

The dataset is generated in both **Consolidated SIH Format** and **Normalized Relational Tables** stored as Parquet files under `data/sample/`.

```
data/sample/
├── sih_transactions.parquet        # Consolidated raw SIH problem statement format
├── transactions.parquet            # Canonical transaction records
├── transaction_inputs.parquet      # Normalized UTXO spending inputs
├── transaction_outputs.parquet     # Normalized created outputs with change flags
├── network_events.parquet          # Correlated peer-to-peer network observations
├── entities.parquet                # Synthetic wallet clusters & entities
├── labels.parquet                  # Ground-truth scenario labels (isolated from features)
├── generation_metadata.json        # Run parameters, seeds, and distribution stats
├── sih_transactions_sample.csv     # 500-row sample for quick human inspection
└── README.md                       # Manifest and quickstart guide
```

### Table 1: `sih_transactions.parquet` (Consolidated SIH Format)
Directly mirrors the schema defined in Section iii of the SIH26146 problem statement:

| Field | Type | Description |
|---|---|---|
| `txid` | `VARCHAR` | Synthetic 64-character SHA-256 transaction hash |
| `timestamp` | `TIMESTAMPTZ` | UTC ISO-8601 transaction broadcast timestamp |
| `input_addresses` | `LIST<VARCHAR>` | Array of spending Bitcoin addresses (P2WPKH, P2PKH, P2SH) |
| `output_addresses` | `LIST<VARCHAR>` | Array of receiving Bitcoin addresses |
| `input_amounts` | `LIST<BIGINT>` | Array of input values in Satoshis ($1 \text{ BTC} = 10^8 \text{ sat}$) |
| `output_amounts` | `LIST<BIGINT>` | Array of output values in Satoshis |
| `fee` | `BIGINT` | Miner transaction fee in Satoshis ($\sum \text{in} - \sum \text{out}$) |
| `script_type` | `VARCHAR` | Primary script format (`P2WPKH`, `P2PKH`, `P2SH`) |
| `src_ip` | `VARCHAR` | Correlated source IPv4 peer address |
| `src_port` | `INTEGER` | Source peer port (ephemeral port or Tor/SOCKS proxy) |
| `dst_ip` | `VARCHAR` | Destination peer IPv4 address |
| `dst_port` | `INTEGER` | Destination port (typically 8333) |
| `country` | `VARCHAR` | ISO-3166-1 alpha-2 geo-location country code |
| `asn` | `INTEGER` | Autonomous System Number of network peer |
| `scenario_id` | `VARCHAR` | Traceability identifier linking event to behavior scenario |

### Table 2: `transactions.parquet` (Canonical Header)

| Column | Type | Description |
|---|---|---|
| `txid` | `VARCHAR` | Primary Key: 64-character transaction hash |
| `block_height` | `INTEGER` | Monotonically increasing synthetic block height |
| `timestamp` | `TIMESTAMPTZ` | Broadcast timestamp (UTC) |
| `input_count` | `INTEGER` | Count of inputs ($\ge 1$) |
| `output_count` | `INTEGER` | Count of outputs ($\ge 1$) |
| `total_input_value_satoshi` | `BIGINT` | Sum of input satoshis |
| `total_output_value_satoshi` | `BIGINT` | Sum of output satoshis |
| `fee_satoshi` | `BIGINT` | $\text{total\_in} - \text{total\_out}$ |
| `transaction_size_bytes` | `INTEGER` | Estimated wire size in bytes |
| `script_type` | `VARCHAR` | Script type |
| `scenario_id` | `VARCHAR` | Scenario identifier |

### Table 3: `transaction_inputs.parquet` (Normalized Inputs)

| Column | Type | Description |
|---|---|---|
| `txid` | `VARCHAR` | Foreign key to `transactions.txid` |
| `input_index` | `INTEGER` | 0-indexed position within transaction |
| `address` | `VARCHAR` | Address of the UTXO being spent |
| `amount_satoshi` | `BIGINT` | Value of the UTXO in satoshis |
| `prev_txid` | `VARCHAR` | Hash of the previous transaction creating this UTXO |
| `prev_output_index` | `INTEGER` | Output index (`vout`) in `prev_txid` |
| `scenario_id` | `VARCHAR` | Scenario identifier |

### Table 4: `transaction_outputs.parquet` (Normalized Outputs)

| Column | Type | Description |
|---|---|---|
| `txid` | `VARCHAR` | Foreign key to `transactions.txid` |
| `output_index` | `INTEGER` | 0-indexed position (`vout`) |
| `address` | `VARCHAR` | Recipient or change Bitcoin address |
| `amount_satoshi` | `BIGINT` | Value allocated to output in satoshis |
| `script_type` | `VARCHAR` | Script standard |
| `is_change` | `BOOLEAN` | `True` if output returns change to sender entity |
| `scenario_id` | `VARCHAR` | Scenario identifier |

### Table 5: `network_events.parquet` (Network Observations)

| Column | Type | Description |
|---|---|---|
| `event_id` | `VARCHAR` | Primary Key: `EVT_{txid_prefix}` |
| `txid` | `VARCHAR` | Correlated transaction ID |
| `timestamp` | `TIMESTAMPTZ` | Network observation time |
| `src_ip` | `VARCHAR` | Synthetic IPv4 origin |
| `src_port` | `INTEGER` | Source port |
| `dst_ip` | `VARCHAR` | Peer receiver IPv4 |
| `dst_port` | `INTEGER` | Peer receiver port |
| `country` | `VARCHAR` | Country code (US, DE, SG, NL, etc.) |
| `asn` | `INTEGER` | Autonomous system number |
| `scenario_id` | `VARCHAR` | Scenario trace identifier |
| `has_network_anomaly` | `BOOLEAN` | True if exhibiting rapid IP hopping or bulletproof ASNs |

### Table 6: `entities.parquet` (Wallet Clusters)

| Column | Type | Description |
|---|---|---|
| `entity_id` | `VARCHAR` | Primary Key: `ENT_{id}` |
| `entity_type` | `VARCHAR` | Category (`exchange`, `merchant`, `service`, `individual`, `mixer`, `suspicious_cluster`) |
| `primary_address` | `VARCHAR` | Seed address of the entity |
| `address_count` | `INTEGER` | Total addresses clustered under this entity |
| `created_at` | `TIMESTAMPTZ` | Entity creation timestamp |
| `total_volume_satoshi` | `BIGINT` | Aggregate volume |

### Table 7: `labels.parquet` (Ground-Truth Labels)
> **Target Leakage Protection**: This table is kept strictly separate so ordinary feature engineering pipelines cannot leak target labels into training matrices.

| Column | Type | Description |
|---|---|---|
| `txid` | `VARCHAR` | Transaction ID |
| `entity_id` | `VARCHAR` | Associated entity |
| `scenario_id` | `VARCHAR` | Traceability identifier |
| `behavior_type` | `VARCHAR` | Scenario name (see Section 3) |
| `ground_truth_label` | `INTEGER` | `0` = Benign, `1` = Suspicious/Anomaly |
| `risk_seed` | `BOOLEAN` | `True` for seed wallets initiating illicit flows |
| `related_entities` | `VARCHAR[]` | List of entities participating in the scenario |

---

## 3. Scenario Catalog & Detection Signatures

The generator implements controlled behavioral patterns with realistic synthetic variations:

| Scenario Name | Target Share | Ground Truth | Graph & Behavioral Pattern | Temporal & Network Characteristics |
|---|---|---|---|---|
| `normal` | 70% | `0` (Benign) | 1-to-2 or 2-to-2 wallet transfers; standard payment + change output | Diurnal inter-arrival timing (5–90s); stable residential or cloud ASNs |
| `benign_high_volume` | 8% | `0` (Benign) | High-throughput exchange deposit/withdrawal sweeps (5–15 outputs) | Rapid steady volume; legitimate hosting ASNs (Google, AWS); **not** flagged as suspicious |
| `transaction_burst` | 4% | `1` (Suspicious) | Rapid surge of 3–5 transactions from a single entity within seconds | 1–10s burst window; 50% overlay with rapid IP hopping |
| `high_fan_in` | 3% | `1` (Suspicious) | Consolidation of 8–16 distinct UTXOs into a single destination address | Aggregation pattern commonly preceding cash-outs |
| `high_fan_out` | 3% | `1` (Suspicious) | Dispersal from 1 UTXO to 15–25 fresh recipient addresses | Structuring / smurfing pattern breaking up large balances |
| `rapid_multihop` | 3% | `1` (Suspicious) | $A \to B \to C \to D$ sequential transfers across different entities | 5–25s latency between hops; overlay with proxy/VPN ASNs |
| `peeling_chain` | 2% | `1` (Suspicious) | Iterative peeling: peels 5–15% to external address, sends remainder to fresh change | Consecutive peeling steps ($4–6$ hops); classic layering behavior |
| `mixing_like` | 2% | `1` (Suspicious) | CoinJoin structure: 4–6 distinct entities provide inputs and receive equal 0.1 BTC outputs | Shuffled outputs breaking linkability; Tor SOCKS / proxy network overlay |
| `coordinated_activity` | 2% | `1` (Suspicious) | Multiple distinct entities concurrently funding a single destination sink | 30–120s synchronized activity window |
| `amount_anomaly` | 1% | `1` (Suspicious) | Whale movement ($>200 \text{ BTC}$) or micro-dust fan-out ($546 \text{ sat}$) | Extreme statistical outliers in value distribution |
| `temporal_anomaly` | 1% | `1` (Suspicious) | Off-hours activity (02:00–04:00 UTC) with robotic 60s periodicity | Unnatural machine timing; overlay with foreign network hops |

---

## 4. Bitcoin-Consistency Rules Enforced

1. **UTXO Conservation**: For every transaction:
   $$\sum \text{input\_amounts} = \sum \text{output\_amounts} + \text{fee}$$
2. **Strict Fee Positivity**: $\text{fee} > 0$ for all transactions (ranging from $2,000$ to $60,000$ satoshis based on transaction byte size).
3. **No Negative Balances**: All amounts in satoshis are strictly positive integers ($\ge 546 \text{ satoshis}$ to respect dust thresholds).
4. **UTXO Lifecycle**: A spent output is removed from the spendable UTXO pool and cannot be double-spent; newly created outputs are added to the pool for downstream spending.
5. **Scenario Traceability**: The `scenario_id` links the scenario entity, transactions, inputs, outputs, network events, and ground-truth labels.

---

## 5. Generation & Scalability Guide

### Generating Datasets via CLI
The generator supports deterministic random seeds and arbitrary scale:

```bash
# 10,000 transactions (Development sample, ~5 seconds)
python scripts/generate_synthetic_dataset.py --transactions 10000 --seed 42 --output data/sample/

# 100,000 transactions (Medium scale, ~45 seconds)
python scripts/generate_synthetic_dataset.py --transactions 100000 --seed 42 --output data/raw/synthetic/100k/

# 500,000 transactions (Full scale, ~3.5 minutes)
python scripts/generate_synthetic_dataset.py --transactions 500000 --seed 42 --output data/raw/synthetic/500k/
```

### Validating Datasets
Run the automated validation suite:
```bash
python scripts/validate_synthetic_dataset.py --data-dir data/sample/
```

### Ingesting into DuckDB
Load Parquet tables directly into the offline analytical DuckDB instance:
```bash
python scripts/load_dataset_to_duckdb.py --data-dir data/sample/ --db-path database/aquasynex.duckdb
```

---

## 6. Limitations & Roadmap to Competition Dataset

| Dimension | Synthetic Development Dataset | Future Official SIH26146 Dataset |
|---|---|---|
| **Data Origin** | Algorithmic simulation (UTXO graph + network overlay) | Official synthetic benchmark provided by NTRO / SIH organizers |
| **P2P Realism** | Simplified peer topology (1 event per transaction) | May include multiple broadcast hops / orphan tx announcements |
| **Address Formats** | P2WPKH, P2PKH, P2SH | Standard Bitcoin formats + potential non-standard scripts |
| **Pipeline Compatibility** | 100% compliant with canonical schema & SIH minimum fields | Will be ingested through the exact same data pipeline without changes |

*Last updated: 2026-09-12 | Owner: ML / Data Subsystem Owner*

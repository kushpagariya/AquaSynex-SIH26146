# AquaSynex — Production Model Card: Transaction Risk Engine v1.0.0

**Model Release Version**: `1.0.0` (`Phase2.7-Production-Freeze`)  
**Release Date**: 2026-09-12  
**Frameworks**: XGBoost (`v2.1.4`), CatBoost (`v1.2.7`), Scikit-Learn (`v1.5.3`), DuckDB (`v1.2.1`)  
**Training/Validation/Test Split**: Chronological 70% / 15% / 15% ($N = 7,000$ / $1,500$ / $1,500$)  
**Dataset Reference**: `data/processed/modeling_v2/modeling_dataset.parquet` (Hardened Synthetic Benchmark `v2.0.0`)  
**Specification Manifest**: `data/processed/modeling_v2/feature_manifest.yaml`  
**Configuration File**: `ml/modeling_experimentation/frozen_model_spec.yaml`  
**Metadata & Integrity Registry**: `models/model_metadata.json`

---

## 1. Scientific Framing, Scope & Disclaimers

> [!CAUTION]
> **SYNTHETIC BENCHMARK DISCLAIMER & INTENDED USE**:
> - This model was trained and evaluated strictly on the AquaSynex **hardened synthetic development dataset (`v2.0.0`)**, engineered with realistic transaction topologies, varied change-ratio distributions, mixed network telemetry, and historical bipartite graph structures.
> - **NO REAL-WORLD CRIMINAL DETECTION CLAIM**: High performance on this simulated UTXO topology validates algorithmic design, graph heuristics, and temporal pipeline engineering. It **DOES NOT** prove real-world Bitcoin criminal detection or sanction screening performance without empirical evaluation on live, verified public ledgers.
> - **Intended Use**: Operational prototype and benchmark reference for the Smart India Hackathon (SIH26146) AI-powered Bitcoin monitoring architecture.

---

## 2. Production Artifacts & Cryptographic Integrity

All production model files and preprocessing pipelines are stored in [`models/`](models/) with immutable SHA256 checksums:

| Artifact Name | Path | Format | SHA256 Checksum |
|---|---|---|---|
| **Binary Detector** | `models/aquasynex_xgb_binary_v1.json` | Native XGBoost Booster JSON | `80994bb26b9ed3d3a88ba3e03d8a14f6c83c4307e047753a6d6157119ad0abe4` |
| **Multiclass Attribution** | `models/aquasynex_catboost_multiclass_v1.cbm` | Native CatBoost Binary Model | `31a16f6d54fb9eec9de420bbec4fba4f5719cead624eae40d61a2b45e06dd115` |
| **Preprocessing Bundle** | `models/preprocessor_v1.joblib` | Scikit-Learn Pipeline (`RobustScaler` + `OHE`) | `68d45547ab70b41bfe759006e4e2beffb564a89c2aa8e4031591bffc1cb0da15` |
| **Model Metadata** | `models/model_metadata.json` | JSON Schema & Version Registry | Monitored |

*Roundtrip verification test confirmed exact floating-point deserialization ($|\Delta_{\text{prob}}| = 0.00\times 10^0$).*

---

## 3. Input Feature Specification (46 Canonical Features)

The engine accepts **strictly the 46 canonical predictive features** defined in the feature catalog:
- **44 Numeric Features**: Preprocessed via `RobustScaler` fit strictly on the training partition.
- **2 Categorical Features** (`net_country`, `net_asn`): Preprocessed via `OneHotEncoder(handle_unknown='ignore')` fit strictly on the training partition.
- **Post-Transformation Dimension**: **71 dense features**.

### Strictly Quarantined Columns
The following fields are strictly excluded from predictive features:
- `transaction_id` (Hex SHA256 transaction hash)
- `timestamp_epoch_sec` (Chronological sorting anchor)
- `hist_cluster_id` (High-cardinality investigation entity cluster identifier)
- `graph_fan_in`, `graph_fan_out`, `graph_unique_in_addrs`, `graph_unique_out_addrs` (Exact duplicates of relational tabular features)
- `target_binary`, `target_multiclass`, `temporal_split` (Ground truth labels and partitions)

---

## 4. Frozen Operating Thresholds & Triage Recommendations

The primary binary detector outputs a continuous anomaly probability $P(\text{suspicious}) \in [0, 1]$. Three operating thresholds are frozen for deployment:

| Operating Point | Threshold ($\tau$) | Validation Recall | Test Recall | Validation Precision | Test Precision | Validation F1 | Test F1 | Test Confusion Matrix (TN / FP / FN / TP) | Operational Profile |
|---|---|---|---|---|---|---|---|---|---|
| **Default Baseline** | `0.50` | 0.9763 | 0.9677 | 0.9702 | 0.9724 | 0.9733 | 0.9700 | 864 / 17 / 20 / 599 | Standard continuous mempool surveillance |
| **$F_1$-Optimal** | `0.32` | **0.9921** | **0.9871** | 0.9632 | 0.9517 | **0.9775** | **0.9691** | 850 / 31 / **8** / **611** | **Compliance Audit / Maximum Anomaly Capture** |
| **High-Precision $R_{95}$** | `0.67` | 0.9543 | 0.9499 | **0.9821** | **0.9833** | 0.9680 | 0.9663 | **871** / **10** / 31 / 588 | **Low False-Alarm Escalation Queue** |

### Operational Deployment Guidance:
All threshold recommendations are limited strictly to prototype analyst review and triage assistance. No automated blocking, direct escalation, or automated settlement decisions should be executed based solely on model outputs. Production operational deployment requires validation on representative real-world transaction traffic and formal approval of an operational policy before any automated decisioning:
1. **High-Priority Review Queue ($\tau \ge 0.67$)**: Recommended for prioritized human analyst triage due to high precision ($98.33\%$) in prototype testing.
2. **Standard Review Queue ($\tau \in [0.32, 0.67)$)**: Captures $98.71\%$ of benchmark anomalies for secondary analyst review.
3. **Low-Priority Queue ($\tau < 0.32$)**: Low operational priority for baseline analyst triage.

---

## 5. Temporal Generalization & Side-by-Side Audit

The 15% out-of-time test partition ($N = 1,500$, chronologically the newest transactions) was evaluated in a **single measurement pass** without post-hoc modifications:

### 5.1 Binary Discrimination (Validation vs Test)

| Metric | Validation ($N = 1,500$) | Test ($N = 1,500$) | Temporal Delta ($\Delta = \text{Test} - \text{Val}$) | Generalization Assessment |
|---|---|---|---|---|
| **ROC-AUC** | 0.9981 | 0.9977 | **-0.0005** | Exceptional stability; virtually zero degradation |
| **PR-AUC** | 0.9976 | 0.9965 | **-0.0011** | Robust under slight class balance shift ($42.27\% \to 41.27\%$) |
| **Inference Latency** | 2.67 ms / 1k | 2.58 ms / 1k | **-0.09 ms** | High throughput ($\approx 387,000$ transactions/second) |

---

## 6. Secondary Multiclass Attribution (11 Behavioral Scenarios)

The secondary CatBoost model attributes transactions into 11 distinct structural and behavioral scenarios:

### 6.1 Multiclass Summary Metrics
- **Top-1 Accuracy**: Validation = 0.9660 | Test = **0.9673** ($\Delta = +0.0013$)
- **Macro F1-Score**: Validation = 0.9566 | Test = **0.9469** ($\Delta = -0.0097$)
- **Weighted F1-Score**: Validation = 0.9660 | Test = **0.9669** ($\Delta = +0.0009$)
- **Log-Loss**: Validation = 0.1002 | Test = **0.1040** ($\Delta = +0.0038$)

### 6.2 Test Partition Breakdown by Scenario ($N = 1,500$)

| Scenario Type | Precision | Recall | F1-Score | Test Support |
|---|---|---|---|---|
| `amount_anomaly` | 1.0000 | 1.0000 | 1.0000 | 11 |
| `benign_high_volume` | 1.0000 | 0.9813 | 0.9906 | 107 |
| `coordinated_activity` | 0.9683 | 0.8714 | 0.9173 | 70 |
| `high_fan_in` | 1.0000 | 1.0000 | 1.0000 | 36 |
| `high_fan_out` | 0.9524 | 1.0000 | 0.9756 | 40 |
| `mixing_like` | 1.0000 | 0.9333 | 0.9655 | 30 |
| `normal` (Benign) | 0.9767 | 0.9742 | 0.9754 | 774 |
| `peeling_chain` | 0.9813 | 1.0000 | 0.9906 | 105 |
| `rapid_multihop` | 1.0000 | 0.9929 | 0.9964 | 140 |
| `temporal_anomaly` | 1.0000 | 0.5333 | 0.6957 | 15 |
| `transaction_burst` | 0.8677 | 0.9535 | 0.9086 | 172 |
| **Overall Macro Average** | **0.9769** | **0.9309** | **0.9469** | **1,500** |

---

## 7. Explainability & Test SHAP Feature Attributions

Exact Tree SHAP feature attributions on the unblinded test partition ($N = 1,500$) confirm architectural stability and alignment with validation attribution:

| Rank | Feature Name | Domain | Test Mean \|SHAP\| | Physical / Behavioral Meaning |
|---|---|---|---|---|
| 1 | `hist_out_mean_neighbor_degree` | **Graph** | **2.7862** | Outgoing address connectivity; separates peer-to-peer from peel/mix networks |
| 2 | `time_since_prev_global_tx_sec` | **Temporal** | **1.3736** | Global transaction arrival pacing; detects synchronized batches |
| 3 | `time_txs_last_1m` | **Temporal** | **0.5566** | Short-window velocity; detects burst activity |
| 4 | `tx_input_count` | **Tabular** | **0.4602** | UTXO consolidation fan-in |
| 5 | `rel_change_value_ratio` | **Relational** | **0.4485** | Proportion of volume returned as change |
| 6 | `time_day_of_week` | **Temporal** | **0.3912** | Weekly seasonality patterns |
| 7 | `tx_fee_sats` | **Tabular** | **0.3744** | Satoshi fee volume |
| 8 | `tx_size_bytes` | **Tabular** | **0.3010** | Wire byte footprint |
| 9 | `tx_fee_rate_sat_per_byte` | **Tabular** | **0.2641** | Miner priority fee density |
| 10 | `hist_cluster_tx_count` | **Graph** | **0.2243** | Entity cluster activity frequency |

---

## 8. Known Limitations & Failure Modes

1. **Synthetic Generation Bounds**: Real-world Bitcoin transactions involve Taproot (P2TR), CoinJoin variations (Wasabi, Whirlpool), multi-sig scripts, and complex Layer-2 (Lightning Network) settlement channels not fully modeled in the current synthetic topology.
2. **Temporal Anomaly Recall**: Sensitivity on `temporal_anomaly` on the test partition is $53.33\%$ ($8$ out of $15$ captured), because timing intervals exhibit high natural variance.
3. **Address Clustering Approximation**: Historical clustering uses a future-invariant union-find heuristic. Adversarial clustering countermeasures (e.g., intentional address reuse poisoning) could degrade graph features.
4. **Mempool Dynamics**: Network features (`net_src_port`, `net_dst_port`) rely on direct peer telemetry; node relay privacy features (e.g., Dandelion++) will attenuate network indicators.

---

## 9. Governance & Lifecycle Status

- **Phase Status**: **Phase 2.7 Complete — Final Freeze Signed Off**.
- **Model Training**: **Permanently Stopped**. No further tuning or refitting is permitted on this model version.
- **Backend Hand-off**: Production artifacts in `models/` are verified, hashed, and ready for ingestion by the AquaSynex inference engine and REST API.

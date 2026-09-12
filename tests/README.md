# AquaSynex — Unified Test Suite & ML Subsystem Baseline

**AquaSynex (SIH26146)**: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic.

This document describes the unified test suite organization (`tests/`), test execution procedures, and the formal audit baseline for the standalone Machine Learning & Graph Analysis subsystem.

---

## 1. Unified Test Suite Structure

The repository maintains **ONE unified test root**: `tests/`.

```text
tests/
├── README.md                                # Suite documentation, ML feature catalog & baseline
├── conftest.py                              # Pytest fixtures: DuckDB isolation, TestClient, ML paths
├── fixtures/
│   ├── sample_bitcoin_dataset.csv           # 5-transaction connected Bitcoin fixture (FastAPI upload)
│   └── ml_sample/                           # Deterministic 5-tx multi-entity Parquet fixture
│       ├── transactions.parquet             # Canonical headers, inputs/outputs count, fees
│       ├── transaction_inputs.parquet       # Spending addresses, values, indices
│       ├── transaction_outputs.parquet      # Destination addresses, values, change flags
│       ├── network_events.parquet           # IP telemetry, ports, countries, ASNs
│       └── labels.parquet                   # Ground-truth scenario and binary labels
├── api/                                     # Fast boundary verification for REST endpoints
│   ├── test_health.py                       # GET /api/health boundary
│   ├── test_datasets.py                     # Dataset upload, list, detail, delete endpoints
│   ├── test_analyses.py                     # Analysis dispatch and status polling
│   ├── test_transactions.py                 # Transaction listing, filtering, pagination
│   ├── test_addresses.py                    # Address list, balance aggregation, profile
│   ├── test_graph.py                        # Cytoscape graph export and subgraph endpoints
│   └── test_results.py                      # ML results listing and entity explanations
├── integration/                             # Full end-to-end multi-step investigator user journeys
│   ├── test_dataset_upload_flow.py          # Multipart upload -> file storage -> DuckDB
│   ├── test_analysis_flow.py                # Analysis trigger -> runner -> terminal state
│   ├── test_transaction_flow.py             # Transactions query, sorting, and detail cross-referencing
│   ├── test_address_flow.py                 # Address derivation, multi-transaction balances
│   ├── test_frontend_backend_contract.py    # TypeScript client routes vs FastAPI OpenAPI routes
│   ├── test_vite_proxy.py                   # Vite proxy config and FastAPI CORS headers
│   ├── test_error_handling.py               # Domain error codes, 404s, and validation envelopes
│   ├── test_data_consistency.py             # Cross-layer ID and count consistency
│   ├── test_no_mock_data.py                 # Automated scan verifying zero mock data in frontend/src
│   └── test_full_user_journey.py            # Complete 14-step investigator user workflow
└── ml/                                      # Standalone ML, Feature Engineering & Graph Test Suite
    ├── test_data_pipeline.py                # Ingestion, metadata quarantine, cleaning, normalization
    ├── test_feature_engineering.py          # Tabular feature extraction (tx, addr, time, net, rel)
    ├── test_graph_analysis.py               # Bipartite graph, clustering, component tracking, future invariance
    ├── test_modeling_dataset.py             # Modeling dataset builder and 10k split verification
    ├── test_model_loading.py                # Artifact deserialization, SHA256 checksums, metadata verification
    ├── test_feature_model_compatibility.py  # 46 canonical features -> preprocessor -> 71-dim vector
    ├── test_inference.py                    # XGBoost binary risk scoring, thresholds, CatBoost 11-class attribution
    ├── test_explanations.py                 # Native TreeSHAP feature attributions, additivity, driver ranking
    └── test_ml_pipeline.py                  # End-to-end pipeline execution and backend contract validation
```

---

## 2. ML Subsystem Architecture & Baseline

### 2.1 Actual Pipeline Flow (Independent of Backend)
```text
Raw Transaction Data (Parquet / DuckDB)
         │
         ▼
[1] Ingestion & Generator Metadata Quarantine (DataIngestionEngine)
         │
         ▼
[2] Pre-cleaning Validation (DataValidationEngine: dust, UTXO conservation, hex, IP)
         │
         ▼
[3] Cleaning & Deduplication (DataCleaningEngine: casing, trimming, fee imputation)
         │
         ▼
[4] Canonical Normalization (DataNormalizationEngine: UTC epoch, sat/BTC, rates, log values)
         │
         ├────────────────────────────────────────┐
         ▼                                        ▼
[5A] Tabular Feature Extraction          [5B] Graph Analysis (NetworkX / Streaming)
     - Transaction features (15)              - Chronological Entity Clustering (UnionFind)
     - Address history lookback (8)           - Graph Bipartite Component Tracking
     - Temporal activity features (7)         - Historical Mean Neighbor Degrees
     - Network telemetry features (6)         - Historical Cluster Size & Tx Counts
     - Relational topological features (4)    - Address Reuse Ratios
         │                                        │
         └───────────────────┬────────────────────┘
                             │ (Merge on transaction_id)
                             ▼
[6] 46 Canonical Predictive Features Matrix
         │
         ▼
[7] Preprocessor Bundle (models/preprocessor_v1.joblib)
     - RobustScaler applied to 44 numeric features
     - OneHotEncoder applied to 2 categorical features ('net_country', 'net_asn')
         │
         ▼
[8] 71-Dimensional Transformed Matrix (X_transformed)
         │
         ├────────────────────────────────────────┬────────────────────────────────────────┐
         ▼                                        ▼                                        ▼
[9A] XGBoost Binary Detector             [9B] CatBoost Multiclass Classifier       [9C] TreeSHAP Explainability
     (aquasynex_xgb_binary_v1.json)           (aquasynex_catboost_multiclass_v1.cbm)    (booster.predict, pred_contribs=True)
     - Suspicious transaction probability     - 11-Class Typology Attribution           - 71 feature attributions + 1 bias
     - Frozen thresholds: 0.50, 0.32, 0.67    - Classes: normal, burst, peeling, etc.   - Additive local accuracy: sum=margin
         │                                        │                                        │
         └────────────────────────────────────────┼────────────────────────────────────────┘
                                                  ▼
                               [10] Structured Backend MLResult Payload
                                    (Ready for DuckDB persistence & Frontend visualization)
```

---

## 3. 46-Feature Schema Manifest

The ML models consume strictly the **46 canonical features** below, transformed into **71 dense features** by `preprocessor_v1.joblib`:

| # | Feature Name | Domain | Type | Scaler / Encoder | Used By |
|---|---|---|---|---|---|
| 1–15 | `tx_input_count`, `tx_output_count`, `tx_input_output_ratio`, `tx_total_input_sats`, `tx_total_output_sats`, `tx_fee_sats`, `tx_size_bytes`, `tx_fee_rate_sat_per_byte`, `tx_value_balance_ratio`, `tx_avg_input_value_sats`, `tx_max_input_value_sats`, `tx_avg_output_value_sats`, `tx_max_output_value_sats`, `tx_log_total_value`, `tx_log_fee` | Transaction | Float/Int | RobustScaler | XGBoost & CatBoost |
| 16–23 | `addr_hist_tx_count`, `addr_hist_total_sent_sats`, `addr_hist_total_received_sats`, `addr_hist_avg_tx_val_sats`, `addr_hist_unique_counterparties`, `addr_hist_active_days`, `addr_hist_tx_per_day`, `addr_reuse_count` | Historical Address ($t < T_{tx}$) | Float/Int | RobustScaler | XGBoost & CatBoost |
| 24–30 | `time_hour_of_day`, `time_day_of_week`, `time_since_prev_global_tx_sec`, `time_txs_last_1m`, `time_txs_last_5m`, `time_txs_last_1h`, `time_since_prev_addr_tx_sec` | Temporal Activity | Float/Int | RobustScaler | XGBoost & CatBoost |
| 31–34 | `net_src_port`, `net_dst_port`, `net_is_standard_bitcoin_port`, `net_hist_unique_ips_for_addr` | Network Telemetry | Float/Int | RobustScaler | XGBoost & CatBoost |
| 35–38 | `rel_fan_in`, `rel_fan_out`, `rel_has_change_output`, `rel_change_value_ratio` | Relational Topology | Float/Int | RobustScaler | XGBoost & CatBoost |
| 39–44 | `hist_in_mean_neighbor_degree`, `hist_out_mean_neighbor_degree`, `hist_component_size`, `hist_address_reuse_ratio`, `hist_cluster_size`, `hist_cluster_tx_count` | Graph Historical ($t < T_{tx}$) | Float/Int | RobustScaler | XGBoost & CatBoost |
| 45 | `net_country` | Categorical Context | String (2-letter ISO) | OneHotEncoder (16 binary cols) | XGBoost & CatBoost |
| 46 | `net_asn` | Categorical Context | Integer (ASN number) | OneHotEncoder (11 binary cols) | XGBoost & CatBoost |

---

## 4. Frozen Production Model Artifacts (`models/`)

| Artifact File | Library & Version | Checksum (SHA-256) | Input Dimension | Output Specification |
|---|---|---|---|---|
| `aquasynex_xgb_binary_v1.json` | `xgboost` 2.1.4 / 3.x | `80994bb26b9ed3d3a88ba3e03d8a14f6c83c4307e047753a6d6157119ad0abe4` | 71 features | Suspicious transaction probability $P(\text{illicit}) \in [0.0, 1.0]$ |
| `aquasynex_catboost_multiclass_v1.cbm` | `catboost` 1.2.7 / 1.2.10 | `31a16f6d54fb9eec9de420bbec4fba4f5719cead624eae40d61a2b45e06dd115` | 71 features | 11-class probability distribution across typologies |
| `preprocessor_v1.joblib` | `scikit-learn` / `joblib` | `68d45547ab70b41bfe759006e4e2beffb564a89c2aa8e4031591bffc1cb0da15` | 46 canonical features | 71-dim array (`RobustScaler` + `OneHotEncoder`) |
| `model_metadata.json` | JSON Schema v1.0.0 | — | — | Metadata, operating points, checksums, feature names |

### Multiclass Typology Targets (11 Classes)
1. `amount_anomaly`
2. `benign_high_volume`
3. `coordinated_activity`
4. `high_fan_in`
5. `high_fan_out`
6. `mixing_like`
7. `normal` (Index 6)
8. `peeling_chain`
9. `rapid_multihop`
10. `temporal_anomaly`
11. `transaction_burst`

---

## 5. Execution Commands

### Run Only the ML Subsystem Tests
```bash
backend\.venv\Scripts\python -m pytest tests/ml/ -v
```

### Run Only Integration Tests
```bash
backend\.venv\Scripts\python -m pytest tests/integration/ -v
```

### Run Full Test Suite (Backend Unit + Integration + ML)
```bash
backend\.venv\Scripts\python -m pytest -v
```

### Run Specific Test Modules
```bash
# Model Loading & Checksums
backend\.venv\Scripts\python -m pytest tests/ml/test_model_loading.py -v

# Feature Engineering & Preprocessor Compatibility
backend\.venv\Scripts\python -m pytest tests/ml/test_feature_model_compatibility.py -v

# XGBoost & CatBoost Inference
backend\.venv\Scripts\python -m pytest tests/ml/test_inference.py -v

# TreeSHAP Explainability
backend\.venv\Scripts\python -m pytest tests/ml/test_explanations.py -v

# End-to-End Pipeline Execution
backend\.venv\Scripts\python -m pytest tests/ml/test_ml_pipeline.py -v
```

---

## 6. Audit Summary & Test Execution Status

Current execution results across the entire repository:

```text
================================================================================
Test Suite Partition                   Passed   Skipped   Failed   Total Tests
================================================================================
Backend Unit Tests (backend/tests/)       62         0        0            62
API Integration Tests (tests/api/)        17         0        0            17
Integration Journeys (tests/integration/) 19         1        0            20
ML Subsystem (tests/ml/)                  40        14        0            54
--------------------------------------------------------------------------------
Total Suite                              138        15        0           153
================================================================================
```

*Note on Skipped Tests*:
- 1 test in `tests/integration/test_vite_proxy.py` (`test_live_vite_proxy_if_running`) is skipped when the Vite development server is offline.
- 14 tests in `tests/ml/test_modeling_dataset.py` are skipped in clean clones because `data/processed/modeling/modeling_dataset.parquet` is a 10,000-row generated benchmark file excluded by `.gitignore`.

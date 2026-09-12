# ML ↔ Backend Integration Contract & Architecture Specification

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**  
**Document**: `docs/integration/ml-backend-integration.md`  
**Status**: ACTIVE & VERIFIED  

---

## 1. Executive Summary

This document specifies the integration architecture connecting the FastAPI backend, DuckDB analytical storage, and the standalone ML / Graph subsystem of AquaSynex.

The integration establishes an end-to-end analytical pipeline where raw Bitcoin transactions and network telemetry ingested into DuckDB are extracted, cleaned, normalized, validated, passed through graph-theoretic feature extraction, transformed via frozen preprocessors, evaluated by frozen gradient-boosted ensembles (XGBoost + CatBoost), explained via TreeSHAP attributions, validated against backend schemas, and persisted into DuckDB for consumption by the React frontend via REST endpoints.

---

## 2. Architectural Boundary & Sequence

### 2.1 Component Topology

```text
                  BACKEND (FastAPI)
                         │
                         │ POST /api/analyses
                         ▼
                 [AnalysisService]
                         │
                         │ triggers background task
                         ▼
                 [PipelineService]
                         │
                         │ invokes entrypoint
                         ▼
             ┌───────────────────────┐
             │      ML ADAPTER       │
             │ (pipeline.ml.         │
             │  model_inference)     │
             │                       │
             │ run_analysis()        │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │  STANDALONE ML ENGINE │
             │                       │
             │ 1. Data Ingestion/Val │
             │ 2. Data Cleaning/Norm │
             │ 3. FeatureEngineering │
             │ 4. Graph Analysis     │
             │ 5. preprocessor_v1    │
             │ 6. XGBoost (Binary)   │
             │ 7. CatBoost (11-Class)│
             │ 8. TreeSHAP           │
             └───────────┬───────────┘
                         │
                         ▼
                   List[MLResult]
                         │
                         ▼
             ┌───────────────────────┐
             │ PipelineService       │
             │ Validation            │
             └───────────┬───────────┘
                         │
                         │ atomic batch write
                         ▼
                      DuckDB
                    (ml_results)
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
      REST API: Results       REST API: Graph
     (/api/results/...)      (/api/addresses/.../graph)
             │                       │
             └───────────┬───────────┘
                         ▼
                  React Frontend
              (Investigator Dashboard)
```

### 2.2 Detailed Execution Flow

1. **Dataset Upload & Ingestion**:
   - Investigator uploads raw Bitcoin data (`CSV` or `Parquet`).
   - `DatasetService._ingest_file` extracts `transactions`, `transaction_inputs`, `transaction_outputs`, and `network_events` into DuckDB partitioned by `dataset_id`.
   - Dataset status transitions to `ready`.
2. **Analysis Initiation**:
   - Investigator or API client requests `POST /api/analyses` with `dataset_id` and optional `model_id` / `model_version`.
   - `AnalysisService` registers the run in `analysis_runs` (`status = 'pending'`), validates model presence via `ModelService`, and queues `PipelineService.run_analysis` as a `BackgroundTask`.
3. **ML Pipeline Execution**:
   - `PipelineService` marks the run `status = 'running'`.
   - Dynamically resolves `pipeline.ml.model_inference.run_analysis`.
   - The ML Adapter:
     - Connects to DuckDB with strict `WHERE dataset_id = ?` scoping (dataset isolation).
     - Loads transactions, inputs, outputs, and network events into DataFrames.
     - Runs `DataValidationEngine`, `DataCleaningEngine`, and `DataNormalizationEngine`.
     - Executes `FeatureEngineeringPipeline` to generate domain and statistical features.
     - Builds bipartite transaction-address graph via `BipartiteGraphBuilder` / `TemporalEntityClusterer` and computes graph topology features via `GraphFeatureExtractor`.
     - Merges tabular and graph features into the canonical 46-feature schema (44 numeric, 2 categorical).
     - Transforms canonical features through frozen `preprocessor_v1.joblib` (RobustScaler + OneHotEncoder) into a 71-dimensional matrix.
     - Executes binary inference via `aquasynex_xgb_binary_v1.json` to compute illicit risk probability $P(\text{illicit})$.
     - Executes multiclass inference via `aquasynex_catboost_multiclass_v1.cbm` over the 71-dim representation to predict an 11-class typology and confidence score.
     - Computes TreeSHAP attributions ($71 \text{ features} + \text{bias}$) and extracts top-$k$ driver explanations.
     - Maps graph-derived properties into investigator-facing `graph_evidence`.
     - Maps risk scores to discrete severity bands (`low`, `medium`, `high`, `critical`).
4. **Validation & Persistence**:
   - Returns a list of standardized result dictionaries.
   - `PipelineService` validates each record against `PipelineService._validate_ml_result`.
   - Validated records are batch-inserted into DuckDB `ml_results` table.
   - Analysis record is updated to `status = 'completed'` with timestamps and metadata.
5. **Consumption**:
   - Frontend polls `/api/analyses/{id}` until `completed`.
   - Results are queried via `/api/results/{analysis_id}`, showing risk scores, typology badges, TreeSHAP explanation cards, and graph neighborhoods.

---

## 3. ML Entrypoint Specification

### 3.1 Function Signature

```python
def run_analysis(
    dataset_id: str,
    model_id: str,
    model_version: str,
    config: Any,
    db_path: str,
    data_dir: str,
    models_dir: str,
) -> List[Dict[str, Any]]:
    """Execute complete ML & graph analysis for a single dataset.
    
    Args:
        dataset_id: Unique UUID of the target dataset.
        model_id: Model identifier (e.g. 'aquasynex_xgb_binary_v1' or 'aquasynex_v1').
        model_version: Model version tag (e.g. '1.0.0').
        config: Analysis configuration dictionary or Pydantic object.
        db_path: Path to the target DuckDB database file.
        data_dir: Path to base data directory.
        models_dir: Path to directory containing frozen model artifacts.
        
    Returns:
        List of validated ML result dictionaries compatible with Backend MLResult schema.
        
    Raises:
        ValueError: If unsupported model requested, empty dataset, or invalid data.
        RuntimeError: If model loading, feature engineering, or inference fails.
    """
```

### 3.2 Dynamic Import Boundary

`backend/services/pipeline_service.py` dynamically resolves:
```python
ml_module = importlib.import_module("pipeline.ml.model_inference")
run_analysis_fn = getattr(ml_module, "run_analysis")
```
This decouple the backend core from ML frameworks at import time while enforcing strict contract validation at runtime.

---

## 4. Data Mapping Specification

### 4.1 DuckDB Schema to ML Canonical Input

| DuckDB Table | DuckDB Column | ML Canonical Field | Type | Transformation / Notes |
|---|---|---|---|---|
| `transactions` | `transaction_id` | `txid` | `VARCHAR` | Identifier aliasing |
| `transactions` | `block_height` | `block_height` | `BIGINT` | Direct pass |
| `transactions` | `block_hash` | `block_hash` | `VARCHAR` | Direct pass |
| `transactions` | `timestamp` | `timestamp` | `TIMESTAMP` | Timestamp normalization |
| `transactions` | `tx_size_bytes` | `tx_size_bytes` | `INTEGER` | Direct pass |
| `transactions` | `tx_vsize` | `tx_vsize` | `INTEGER` | Direct pass |
| `transactions` | `tx_weight` | `tx_weight` | `INTEGER` | Direct pass |
| `transactions` | `locktime` | `locktime` | `INTEGER` | Direct pass |
| `transactions` | `version` | `version` | `INTEGER` | Direct pass |
| `transactions` | `input_count` | `input_count` | `INTEGER` | Direct pass |
| `transactions` | `output_count` | `output_count` | `INTEGER` | Direct pass |
| `transactions` | `total_input_satoshi` | `total_input_satoshi` | `BIGINT` | Direct pass |
| `transactions` | `total_output_satoshi` | `total_output_satoshi` | `BIGINT` | Direct pass |
| `transactions` | `fee_satoshi` | `fee_satoshi` | `BIGINT` | Direct pass |
| `transaction_inputs` | `input_id` | `input_id` | `VARCHAR` | Direct pass |
| `transaction_inputs` | `transaction_id` | `txid` | `VARCHAR` | Aliased to `txid` |
| `transaction_inputs` | `input_index` | `input_index` | `INTEGER` | Direct pass |
| `transaction_inputs` | `input_address` | `address` | `VARCHAR` | Aliased to `address` |
| `transaction_inputs` | `input_value_satoshi` | `amount_satoshi` | `BIGINT` | Aliased to `amount_satoshi` |
| `transaction_inputs` | `witness` | `witness` | `VARCHAR` | Direct pass |
| `transaction_outputs` | `output_id` | `output_id` | `VARCHAR` | Direct pass |
| `transaction_outputs` | `transaction_id` | `txid` | `VARCHAR` | Aliased to `txid` |
| `transaction_outputs` | `output_index` | `output_index` | `INTEGER` | Direct pass |
| `transaction_outputs` | `output_address` | `address` | `VARCHAR` | Aliased to `address` |
| `transaction_outputs` | `output_value_satoshi` | `amount_satoshi` | `BIGINT` | Aliased to `amount_satoshi` |
| `transaction_outputs` | `script_type` | `script_type` | `VARCHAR` | Categorical normalization |
| `network_events` | `event_id` | `event_id` | `VARCHAR` | Direct pass |
| `network_events` | `transaction_id` | `txid` | `VARCHAR` | Aliased to `txid` |
| `network_events` | `src_ip` | `src_ip` | `VARCHAR` | IP geolocation lookup |
| `network_events` | `dst_port` | `dst_port` | `INTEGER` | Peer telemetry |
| `network_events` | `country` | `country` | `VARCHAR` | Categorical normalization |
| `network_events` | `asn` | `asn` | `INTEGER` | Autonomous System Number |

---

## 5. Result Mapping & Schema Specification

### 5.1 ML Output to Backend MLResult

| ML Adapter Field | Backend Schema Field | DB Column (`ml_results`) | Type | Semantics |
|---|---|---|---|---|
| `entity_id` | `entity_id` | `entity_id` | `VARCHAR` | Transaction hash (`txid`) |
| `entity_type` | `entity_type` | `entity_type` | `VARCHAR` | Always `'transaction'` for transaction models |
| `risk_score` | `risk_score` | `risk_score` | `FLOAT` | XGBoost probability $P(\text{illicit}) \in [0.0, 1.0]$ |
| `anomaly_score` | `anomaly_score` | `anomaly_score` | `FLOAT` | Consistent XGBoost probability |
| `risk_level` | `risk_level` | `risk_level` | `VARCHAR` | Threshold-derived: `critical`, `high`, `medium`, `low` |
| `confidence` | `confidence` | `confidence` | `FLOAT` | CatBoost predicted class probability $\in [0.0, 1.0]$ |
| `prediction_label` | `prediction_label` | `prediction_label` | `VARCHAR` | CatBoost predicted typology class name |
| `explanations` | `explanations` | `explanations` | `JSON` | List of top-$k$ TreeSHAP attributions |
| `features` | `features` | `features` | `JSON` | Key-value pairs of 46 model features |
| `graph_evidence` | `graph_evidence` | `graph_evidence` | `JSON` | Graph-derived metrics (cluster size, reuse, fan-in) |
| `predicted_at` | `predicted_at` | `predicted_at` | `TIMESTAMP` | UTC execution timestamp |

### 5.2 Risk Level Mapping Semantics

Risk levels are derived from the XGBoost risk probability $s$:
- $s \ge 0.90 \implies \mathbf{critical}$
- $s \ge 0.70 \implies \mathbf{high}$
- $s \ge 0.40 \implies \mathbf{medium}$
- $s < 0.40 \implies \mathbf{low}$

### 5.3 Explanation Structure

```json
[
  {
    "feature": "fee_per_byte",
    "attribution": 0.4821,
    "value": 142.5
  },
  {
    "feature": "hist_address_reuse_ratio",
    "attribution": 0.3129,
    "value": 0.8
  }
]
```

### 5.4 Graph Evidence Structure

```json
{
  "hist_cluster_size": 4.0,
  "hist_component_size": 4.0,
  "hist_address_reuse_ratio": 0.0,
  "rel_fan_in": 1.0,
  "rel_fan_out": 2.0
}
```

---

## 6. Error Handling & Resilience Rules

1. **Strict No-Fake-Results Invariant**:
   - Synthetic risk scores, heuristic approximations, or mocked classifications are strictly forbidden when ML fails.
   - Any runtime failure during model loading, feature extraction, graph clustering, preprocessor transformation, or inference immediately marks the analysis run as `status = 'failed'`.
   - Incomplete or corrupted result batches are rolled back; zero partial results are persisted.
2. **Model Validation**:
   - `ModelService` verifies requested model artifacts (`.json`, `.cbm`, `.joblib`) exist on disk and match registered versions.
   - Unrecognized model IDs or versions raise a controlled `ValueError` resulting in an immediate 400 or failed run with clean error messaging.
3. **Dataset Scoping & Isolation**:
   - All extraction queries explicitly filter on `WHERE dataset_id = ?`.
   - Results are persisted with matching `dataset_id` and `analysis_id`.
   - Multitenancy and cross-dataset contamination tests ensure strict data boundary isolation.

---

## 7. Verification & Test Metrics

### Test Suite Comparison

| Test Stage | Collected | Passed | Skipped | Failed | Duration |
|---|---|---|---|---|---|
| **Before ML Integration Baseline** | 153 | 138 | 15 | 0 | 12.4s |
| **After ML Integration Full Suite** | 168 | **153** | 15 | 0 | **13.92s** |

### Verified Coverage

- **Adapter Discovery**: `test_ml_adapter_import_and_discovery` verified dynamically.
- **Model Registry Discovery**: `test_model_discovery_and_selection` verified with `model_metadata.json`.
- **Controlled Error Handling**: `test_invalid_model_error` and `test_ml_controlled_failure_no_fake_predictions` verified.
- **Dataset Isolation**: `test_dataset_isolation_strict` verified with dual isolated datasets.
- **Real ML Pipeline & Model Inference**: `test_real_ml_pipeline_execution_and_persistence` verified using real frozen XGBoost, CatBoost, and TreeSHAP.
- **Full User Journey**: Ingestion $\to$ Analysis $\to$ Persistence $\to$ REST API Retrieval $\to$ Transaction & Graph Queries fully verified.

---
*AquaSynex SIH26146 ML Integration Documentation | Last updated: 2026-09-12*

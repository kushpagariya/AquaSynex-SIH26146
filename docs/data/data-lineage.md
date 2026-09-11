# Data Lineage

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This document defines how data flows and transforms from raw input to ML prediction,
> and how that provenance can be traced for forensic verification.

---

## 1. Why Lineage Matters

This is a forensic investigation tool. Every ML prediction that drives an investigator's decision must be traceable to:

1. The **original dataset file** uploaded by the investigator.
2. The **normalization and cleaning decisions** made during ingestion.
3. The **feature engineering logic** applied.
4. The **specific ML model and version** used.
5. The **graph features** that contributed to the prediction.

Without lineage, a risk score is an opaque number. With lineage, it is an auditable analytical conclusion.

---

## 2. Data Lineage Chain

```
Original Dataset File
    │  fileName, fileHash, uploadedAt
    ▼
Dataset Registration
    │  datasetId, canonicalFieldMap, validationSummary
    ▼
Canonical Records (DuckDB)
    │  ingested_at, dataset_id
    ▼
Feature Engineering
    │  featureSchemaVersion, featureComputedAt
    ▼
Graph Construction
    │  graphId, graphComputedAt, nodeCount, edgeCount
    ▼
Graph Feature Extraction
    │  graphFeatureSchemaVersion
    ▼
ML Model Inference
    │  modelId, modelVersion, featureSchemaVersion, analysisId
    ▼
Structured ML Result
    │  resultId, predictedAt
    ▼
DuckDB (ml_results)
    │  analysis_id, dataset_id, entity_id
    ▼
Backend API Response
    │  analysisId, datasetId, modelId, modelVersion
    ▼
Frontend Display
    │  Shows provenance metadata to investigator
```

---

## 3. Provenance Metadata per Stage

### 3.1 Dataset Provenance

| Field | Stored in | Purpose |
|---|---|---|
| `datasetId` | `datasets.dataset_id` | Unique dataset identifier |
| `fileName` | `datasets.file_name` | Original file name |
| `fileHash` | `PLANNED` — `datasets.file_hash` | SHA256 of original file for integrity |
| `uploadedAt` | `datasets.uploaded_at` | When file was received |
| `canonicalFieldMap` | `datasets.canonical_field_map` | How raw columns mapped to canonical |
| `validationSummary` | `datasets.validation_summary` | What was accepted/rejected |

### 3.2 Analysis Run Provenance

| Field | Stored in | Purpose |
|---|---|---|
| `analysisId` | `analysis_runs.analysis_id` | Unique analysis run identifier |
| `datasetId` | `analysis_runs.dataset_id` | Which dataset was analyzed |
| `startedAt` | `analysis_runs.started_at` | Analysis start time |
| `completedAt` | `analysis_runs.completed_at` | Analysis end time |
| `modelId` | `analysis_runs.model_id` | Which ML model was used |
| `modelVersion` | `analysis_runs.model_version` | Exact model version |
| `featureSchemaVersion` | `analysis_runs.feature_schema_version` | Feature schema used |
| `config` | `analysis_runs.config` | Analysis configuration snapshot |

### 3.3 ML Prediction Provenance

| Field | Stored in | Purpose |
|---|---|---|
| `resultId` | `ml_results.result_id` | Unique prediction identifier |
| `analysisId` | `ml_results.analysis_id` | Links to analysis run |
| `datasetId` | `ml_results.dataset_id` | Links to source dataset |
| `entityId` | `ml_results.entity_id` | Which entity was scored |
| `modelId` | `ml_results.model_id` | Which model produced this |
| `modelVersion` | `ml_results.model_version` | Exact model version |
| `predictedAt` | `ml_results.predicted_at` | When this prediction was made |
| `featuresJson` | `ml_results.features_json` | Exact feature values used |
| `explanationJson` | `ml_results.explanation_json` | SHAP values for traceability |

---

## 4. Traceability Example

Given a risk score for address `bc1qar0...`:

```
Step 1: Find result_id in ml_results WHERE entity_id = 'bc1qar0...'
Step 2: Get analysis_id → find analysis_run record
Step 3: Get dataset_id → find original dataset
Step 4: Get model_id + model_version → identify exact model artifact
Step 5: Get features_json → see exact feature values that drove the score
Step 6: Get explanation_json → see SHAP contributions per feature
Step 7: Get dataset.canonical_field_map → see how raw data mapped to features
Step 8: Cross-reference canonical transactions WHERE output_address = 'bc1qar0...'
```

This full chain allows an investigator to explain exactly why a score was produced.

---

## 5. Model Artifact Provenance

Trained model artifacts (`.pkl`, `.joblib`, `.json`) must include metadata:

```json
{
  "modelId": "isolation_forest_v1",
  "modelVersion": "1.0.0",
  "featureSchemaVersion": "1.0.0",
  "trainingDatasetId": "dataset-uuid-of-training-data",
  "trainingCompletedAt": "2026-09-11T16:00:00+00:00",
  "trainingMetrics": {
    "f1Score": 0.89,
    "precision": 0.91,
    "recall": 0.87,
    "rocAuc": 0.94
  },
  "featureNames": ["tx_count", "avg_value_satoshi", "..."],
  "hyperparameters": {}
}
```

This is stored as a sidecar JSON file alongside each model artifact. See [model-versioning.md](../ml/model-versioning.md).

---

## 6. Lineage Limitations

The following limitations are acknowledged:

| Limitation | Notes |
|---|---|
| File integrity hashing | `PLANNED` — not yet implemented |
| Intermediate feature persistence | Feature DataFrames are not persisted separately (only final values in `features_json`) |
| Graph intermediate state | Graph snapshots are not persisted (graph is reconstructed per analysis run) |
| Training data provenance | Training datasets must be manually tracked; no automated training lineage in Phase 1 |

---

*Last updated: 2026-09-11 | Owner: All*
*References: [canonical-schema.md](./canonical-schema.md) | [model-versioning.md](../ml/model-versioning.md) | [duckdb-schema.md](../backend/duckdb-schema.md)*

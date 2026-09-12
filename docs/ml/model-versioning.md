# Model Versioning

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Version Identifiers

A complete ML model identity requires four linked identifiers:

| Identifier | Description | Example |
|---|---|---|
| `model_id` | Named model identifier | `"isolation_forest_v1"` |
| `model_version` | Semantic version of the model artifact | `"1.0.0"` |
| `feature_schema_version` | Version of the feature specification used | `"1.0.0"` |
| `training_dataset_id` | Dataset UUID used for training | UUID v4 |

All four must be recorded in:
1. The model's sidecar `model_metadata.json` file
2. The `analysis_runs` DuckDB table for each inference run
3. The `ml_results` DuckDB table for each prediction

---

## 2. Model Artifact Directory Structure

```
/models/
    isolation_forest_v1/
        1.0.0/
            model.pkl               # Serialized sklearn model
            scaler.pkl              # Fitted MinMaxScaler or StandardScaler
            model_metadata.json     # Full metadata
            evaluation_report.json  # Evaluation metrics
            pr_curve.png            # Precision-Recall curve
            feature_importance.json # Global SHAP importance
    xgboost_v1/
        1.0.0/
            model.pkl
            scaler.pkl
            model_metadata.json
            evaluation_report.json
```

---

## 3. Model Metadata Schema

`model_metadata.json`:

```json
{
  "modelId": "isolation_forest_v1",
  "modelVersion": "1.0.0",
  "featureSchemaVersion": "1.0.0",
  "algorithm": "IsolationForest",
  "modelType": "anomaly_detection",
  "trainingDatasetId": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "trainingCompletedAt": "2026-09-11T10:00:00+00:00",
  "featureNames": [
    "tx_input_count",
    "tx_output_count",
    "addr_transaction_count",
    "addr_tx_per_day",
    "graph_in_degree",
    "graph_out_degree",
    "graph_pagerank",
    "graph_connected_component_size"
  ],
  "hyperparameters": {
    "n_estimators": 100,
    "max_samples": "auto",
    "contamination": 0.1,
    "random_state": 42
  },
  "scalerType": "MinMaxScaler",
  "trainingMetrics": {
    "auprc": null,
    "auroc": null,
    "note": "Unsupervised model — metrics estimated from manual validation"
  }
}
```

---

## 4. Version Compatibility Rules

| Scenario | Allowed? |
|---|---|
| Model trained on feature schema v1.0.0 → inference with v1.0.0 features | ✅ Yes |
| Model trained on feature schema v1.0.0 → inference with v1.1.0 features | ⚠️ Allowed if v1.1.0 is backward compatible (new features added only) |
| Model trained on feature schema v1.0.0 → inference with v2.0.0 features | ❌ No — major version change; retrain required |
| Using an older model with a new feature schema that removed features | ❌ No — `INVALID_FEATURES` error |

**Backward compatibility rule**: A feature schema version bump is backward compatible only if existing feature names and types are unchanged and only new features are added.

---

## 5. Model Selection at Inference Time

The backend selects the model to use based on:
1. `analysis_config.model_id` specified in the analysis request.
2. If not specified: the **default model** configured in `BACKEND_DEFAULT_MODEL_ID` environment variable.
3. The model directory is scanned at backend startup to detect available models.

---

## 6. Serialization Format

| Artifact | Serialization | Library |
|---|---|---|
| sklearn model | Pickle (`.pkl`) | `joblib.dump()` preferred over `pickle.dump()` |
| Scaler | Pickle (`.pkl`) | `joblib.dump()` |
| XGBoost model | JSON (`.json`) | `model.save_model("model.json")` |
| Metadata | JSON | Standard `json.dump()` |

**Joblib is preferred** over pickle for sklearn models because it handles large numpy arrays more efficiently.

---

## 7. Versioning Workflow

When a new model version is created:

```
1. Train new model
2. Evaluate on held-out test set
3. Create /models/{model_id}/{version}/ directory
4. Save model.pkl, scaler.pkl, model_metadata.json, evaluation_report.json
5. Update BACKEND_DEFAULT_MODEL_ID if this becomes the new default
6. Do NOT delete old model versions (for lineage)
7. Record training_dataset_id in model_metadata.json
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner*
*References: [model-input-contract.md](./model-input-contract.md) | [model-output-contract.md](./model-output-contract.md) | [data-lineage.md](../data/data-lineage.md)*

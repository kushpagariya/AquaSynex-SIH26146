# ML Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## 1. ML Pipeline Architecture

```
Canonical Transaction Records (from DuckDB / Parquet)
        │
        ▼
┌───────────────────────────────────────┐
│         DATA PREPARATION              │
│  - Load canonical records             │
│  - Filter by dataset_id               │
│  - Join transactions + addresses      │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│       FEATURE ENGINEERING             │
│  Transaction-level features           │
│  Address-level behavioral features    │
│  Temporal features                    │
│  Value-flow features                  │
└───────────────────┬───────────────────┘
                    │
        ┌───────────┤
        ▼           ▼
┌─────────────┐ ┌───────────────────────┐
│   GRAPH     │ │  TABULAR FEATURES     │
│  LAYER      │ │  (transaction/addr)   │
│  (NetworkX) │ └───────────────────────┘
│             │          │
│  Graph      │          │
│  features   │          │
└──────┬──────┘          │
       │                 │
       └────────┬────────┘
                ▼
┌───────────────────────────────────────┐
│        FEATURE MERGING                │
│  Combine tabular + graph features     │
│  Handle missing values                │
│  Feature normalization / scaling      │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│          ML MODEL                     │
│  Anomaly detection (unsupervised)     │
│  Classification (if labels available) │
│  XGBoost / IsolationForest / etc.     │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│         RISK SCORING                  │
│  Normalize anomaly score → [0.0, 1.0] │
│  Apply composite weighting            │
│  Assign risk level                    │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│        EXPLAINABILITY (SHAP)          │
│  Compute SHAP values                  │
│  Structure feature contributions      │
│  Generate human-readable labels       │
└───────────────┬───────────────────────┘
                │
                ▼
┌───────────────────────────────────────┐
│    STRUCTURED ML RESULT               │
│  (see model-output-contract.md)       │
└───────────────────────────────────────┘
```

**Status**: `PLANNED`

---

## 2. Model Selection Strategy

The ML architecture is designed to be **model-agnostic** at the system level. The backend and frontend consume only the standardized ML output contract, not model internals.

This means the model can be replaced or upgraded without changing the API or frontend.

### Phase 1 — Anomaly Detection (Unsupervised)

**When label data is not available**, use unsupervised anomaly detection:

| Algorithm | Library | Status | Notes |
|---|---|---|---|
| Isolation Forest | `sklearn.ensemble` | `PLANNED` | Primary candidate; efficient for high-dimensional data |
| Local Outlier Factor | `sklearn.neighbors` | `CANDIDATE` | Good for density-based anomalies |
| One-Class SVM | `sklearn.svm` | `CANDIDATE` | Research-required for performance |
| Autoencoder | TensorFlow/PyTorch | `FUTURE` | Excluded from Phase 1 (adds dep) |

### Phase 2 — Classification (Supervised)

**When label data is available** (e.g., Elliptic dataset):

| Algorithm | Library | Status | Notes |
|---|---|---|---|
| XGBoost | `xgboost` | `PLANNED` | Primary candidate for classification |
| Random Forest | `sklearn.ensemble` | `CANDIDATE` | Ensemble baseline |
| Gradient Boosting | `sklearn.ensemble` | `CANDIDATE` | Alternative to XGBoost |

### Model Selection Principle

> Do not lock into a single algorithm before evaluation. The `model-output-contract.md` defines the output shape. Experimentation happens within the ML layer without breaking other subsystems.

---

## 3. Training vs Inference

| Mode | Description | Trigger |
|---|---|---|
| **Training** | Fit model on a labeled or unlabeled dataset; save artifact | Offline — manual trigger or CLI |
| **Inference** | Load pre-trained model artifact; score entities in a new dataset | Online — triggered by backend when analysis is requested |

**Training does not happen on every analysis run.** Models are pre-trained and persisted. Inference loads the artifact.

**Model artifacts** are stored in `/models/` directory. See [model-versioning.md](./model-versioning.md).

---

## 4. Component Responsibilities

| Component | File Location (Proposed) | Responsibility |
|---|---|---|
| `data_loader.py` | `pipeline/data/` | Load canonical records from DuckDB/Parquet |
| `feature_engineering.py` | `pipeline/ml/` | Compute transaction + address + temporal features |
| `graph_builder.py` | `pipeline/graph/` | Build NetworkX graph from canonical data |
| `graph_features.py` | `pipeline/graph/` | Extract graph features per node |
| `model_trainer.py` | `pipeline/ml/` | Train and save model artifacts |
| `model_inference.py` | `pipeline/ml/` | Load model, run inference, produce scored output |
| `risk_scorer.py` | `pipeline/ml/` | Convert model scores to risk levels |
| `explainer.py` | `pipeline/ml/` | Compute SHAP values and structure explanations |
| `result_builder.py` | `pipeline/ml/` | Assemble final ML output contract structure |

**Status**: All `PLANNED` — directory structure not yet created.

---

## 5. Analysis Pipeline Entry Point

The backend invokes the ML pipeline via a single entry function:

```python
# Proposed interface — PLANNED
def run_analysis(
    dataset_id: str,
    model_id: str,
    model_version: str,
    config: dict
) -> list[MLResult]:
    """
    Run the complete analysis pipeline for a dataset.
    Returns a list of MLResult objects (one per entity).
    """
    ...
```

This function is the only entry point the backend calls. It encapsulates the entire pipeline.

See [backend-ml-contract.md](../backend/backend-ml-contract.md) for the interface contract.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner*
*References: [feature-specification.md](./feature-specification.md) | [model-output-contract.md](./model-output-contract.md) | [backend-ml-contract.md](../backend/backend-ml-contract.md)*

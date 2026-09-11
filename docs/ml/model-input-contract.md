# Model Input Contract

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This document defines what the ML model receives as input.**
> The feature engineering layer must produce exactly this format.
> The backend orchestration must ensure this format is provided.

---

## 1. Input Contract Overview

The ML model receives a **feature matrix** — a Pandas DataFrame where:
- Each row represents one entity (address or transaction).
- Each column is a canonical feature from [feature-specification.md](./feature-specification.md).
- All values are numeric (float64 or int64).
- All values have been normalized/scaled.
- Missing values have been imputed (no NaN values in model input).

Additionally, a **metadata DataFrame** provides entity identifiers (not used as model features).

---

## 2. Feature Matrix Format

```python
# Type: pd.DataFrame
# Index: default integer index
# Columns: list of canonical feature names (strings)

feature_matrix: pd.DataFrame = pd.DataFrame({
    "tx_input_count":                 [3.0, 1.0, 2.0, ...],
    "tx_output_count":                [5.0, 2.0, 1.0, ...],
    "tx_total_value_satoshi":         [8.2, 4.1, 3.9, ...],  # log-normalized
    "addr_transaction_count":         [142.0, 3.0, 27.0, ...],  # log-normalized
    "addr_total_received_satoshi":    [...],
    "addr_tx_per_day":                [...],
    "graph_in_degree":                [...],
    "graph_out_degree":               [...],
    "graph_pagerank":                 [...],
    "graph_connected_component_size": [...],
    # ... all features from feature-specification.md with status PLANNED
})
```

---

## 3. Metadata DataFrame Format

```python
# Type: pd.DataFrame, same row order as feature_matrix
metadata: pd.DataFrame = pd.DataFrame({
    "entity_id":   ["bc1q...", "1A1z...", ...],  # Bitcoin address or txid
    "entity_type": ["address", "address", ...],  # "address" | "transaction"
    "dataset_id":  ["uuid...", "uuid...", ...],
    "analysis_id": ["uuid...", "uuid...", ...],
})
```

**The metadata DataFrame must have the same row count and row order as the feature matrix.**

---

## 4. Preprocessing Requirements

Before passing to the model, the feature engineering layer must:

| Requirement | Rule |
|---|---|
| No NaN values | All missing values imputed. Imputation method recorded in `FeatureValue.imputation_method` |
| Numeric only | All columns are numeric (float64 or int64). No string columns. |
| Correct column order | Columns match the order defined in the model artifact's `feature_names` metadata |
| Normalization applied | Features are scaled using the scaler fit during training (not re-fit on inference data) |
| Log transformation | Value fields (satoshi amounts) are log1p-transformed before normalization |
| Outlier clipping | Values are clipped to [−3σ, +3σ] of training distribution before normalization |

---

## 5. Imputation Rules

| Feature | Missing value strategy |
|---|---|
| Count features (`_count`) | Median of training dataset |
| Value features (`_satoshi`) | Median of training dataset |
| Temporal features (`_days`, `_per_day`) | Median of training dataset |
| Graph features | 0 (entity not in graph → no connections) |

`DECISION REQUIRED`: The exact imputation strategy requires validation against real dataset distributions.

---

## 6. Feature Name Compatibility

The model artifact stores the **list of feature names it was trained on**. Before inference:

1. Load model artifact.
2. Read `feature_names` from model metadata.
3. Verify the incoming feature matrix has all required columns.
4. If the feature matrix has extra columns → drop them.
5. If the feature matrix is missing a required column → raise `INVALID_FEATURES` error.
6. Reorder columns to match model's expected order.

```python
# Pseudo-code
required_features = model_metadata["feature_names"]
missing = set(required_features) - set(feature_matrix.columns)
if missing:
    raise InvalidFeaturesError(f"Missing features: {missing}")
feature_matrix = feature_matrix[required_features]  # Reorder
```

---

## 7. Feature Schema Version

Each feature matrix must be associated with a **feature schema version** that matches the model's expected version.

If the feature schema version in the analysis run does not match the model's expected feature schema version, the inference must be rejected with an `ML_ERROR`.

See [model-versioning.md](./model-versioning.md).

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: ML Owner*
*References: [feature-specification.md](./feature-specification.md) | [model-output-contract.md](./model-output-contract.md) | [model-versioning.md](./model-versioning.md)*

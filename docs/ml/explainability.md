# Explainability Contract

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Overview

The explainability layer transforms SHAP model outputs into structured, investigator-facing evidence. The goal is to answer the question:

> *Why did this entity receive a high risk score?*

SHAP (SHapley Additive exPlanations) is used to compute feature contributions to each prediction.

---

## 2. SHAP → Structured Explanation Pipeline

```
ML Model
    │
    ▼
SHAP TreeExplainer (or LinearExplainer)
    │
    ▼
Raw SHAP values (float array, one per feature per entity)
    │
    ▼
Feature importance ranking
    │
    ▼
Direction assignment (positive SHAP = increases risk)
    │
    ▼
Human-readable label lookup (from feature-specification.md)
    │
    ▼
FeatureExplanation objects (per model-output-contract.md)
    │
    ▼
Backend stores in ml_results.explanation_json
    │
    ▼
Frontend renders as explanation cards
```

---

## 3. SHAP Implementation

### Supported Explainers

| Model Type | SHAP Explainer | Notes |
|---|---|---|
| Isolation Forest | `shap.TreeExplainer` | Supported in SHAP ≥ 0.41 |
| XGBoost | `shap.TreeExplainer` | Native support |
| Random Forest | `shap.TreeExplainer` | Native support |
| One-Class SVM | `shap.KernelExplainer` | Slow; use sampling |

**Primary**: `shap.TreeExplainer` (`PLANNED`)

### Code Pattern (Proposed)

```python
import shap
import numpy as np

explainer = shap.TreeExplainer(trained_model)
shap_values = explainer.shap_values(feature_matrix)  # shape: (n_entities, n_features)

# For entity i
entity_shap = shap_values[i]                          # shape: (n_features,)
feature_names = feature_matrix.columns.tolist()
```

---

## 4. SHAP Value Interpretation

| SHAP Value | Meaning |
|---|---|
| Positive | This feature **increases** the risk score for this entity |
| Negative | This feature **decreases** the risk score for this entity |
| Near zero | This feature has little influence on this entity's score |
| Large magnitude | This feature is highly influential (in either direction) |

**Note on Isolation Forest SHAP**: For tree-based anomaly detectors, SHAP values represent feature contributions to the anomaly score, not a probability. The interpretation is directional but not probabilistic.

---

## 5. Feature Explanation Transformation

For each entity, produce a sorted list of `FeatureExplanation` objects:

```python
def build_explanations(
    entity_shap_values: np.ndarray,
    feature_names: list[str],
    feature_values: dict[str, float],
    feature_display_labels: dict[str, str],  # from feature-specification.md
    feature_units: dict[str, str | None],
) -> list[FeatureExplanation]:
    
    abs_shap = np.abs(entity_shap_values)
    total_abs_shap = abs_shap.sum()
    
    explanations = []
    for i, (feat_name, shap_val, abs_val) in enumerate(
        sorted(zip(feature_names, entity_shap_values, abs_shap),
               key=lambda x: abs(x[1]), reverse=True)
    ):
        explanations.append(FeatureExplanation(
            feature_name=feat_name,
            display_label=feature_display_labels[feat_name],
            shap_value=float(shap_val),
            direction="increases_risk" if shap_val > 0 else "decreases_risk" if shap_val < 0 else "neutral",
            importance_rank=i + 1,
            normalized_importance=float(abs_val / total_abs_shap) if total_abs_shap > 0 else 0.0,
            feature_value=feature_values.get(feat_name),
            feature_unit=feature_units.get(feat_name),
        ))
    
    return explanations
```

---

## 6. Feature Display Labels

Every canonical feature name must have a corresponding human-readable display label. This mapping is defined in [feature-specification.md](./feature-specification.md) and is used by the explainability layer.

**Examples**:

| Canonical Name | Display Label | Unit |
|---|---|---|
| `addr_tx_per_day` | "Transaction velocity per day" | "tx/day" |
| `graph_pagerank` | "Network centrality score" | null |
| `addr_transaction_count` | "Total transactions" | "count" |
| `addr_total_received_satoshi` | "Total BTC received" | "BTC" |
| `tx_input_count` | "Number of inputs" | "count" |
| `graph_in_degree` | "Incoming connections" | "count" |
| `graph_connected_component_size` | "Network cluster size" | "count" |

> **The display label must not be computed or invented by the frontend.** It is produced by the ML layer and passed through the backend in the explanation contract.

---

## 7. Frontend Rendering Contract

The frontend receives a list of `FeatureExplanation` objects and renders them as **explanation cards**.

Each card displays:
- Feature display label
- Direction indicator (icon: ↑ increases risk, ↓ decreases risk)
- Feature value with unit
- Relative importance bar (based on `normalizedImportance`)
- SHAP value (optional — for advanced view)

**The frontend must NOT**:
- Re-compute SHAP values
- Re-rank explanations
- Change display labels
- Interpret SHAP values beyond the `direction` field

---

## 8. Top-N Explanations

By default, only the **top 5 explanations** (by `importance_rank`) are shown in the summary view. All explanations are available in the full detail view.

`DECISION REQUIRED`: Whether "top 5" or "top 10" is the right default. This can be a configurable backend parameter.

---

## 9. Base Value / Expected Value

SHAP explanations also include a **base value** — the model's expected prediction (average across the dataset). This is useful for showing how much each feature pushes the score above or below the baseline.

```python
base_value = explainer.expected_value
```

This should be included in the API response for full SHAP waterfall visualization if needed by the frontend.

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner*
*References: [model-output-contract.md](./model-output-contract.md) | [feature-specification.md](./feature-specification.md) | [visualization-specification.md](../frontend/visualization-specification.md)*

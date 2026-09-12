# Model Output Contract

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is one of the most important documents in the project.**
> The ML layer MUST produce output matching this schema exactly.
> The Backend layer MUST consume this schema and not assume anything beyond what is defined here.
>
> **Changing this contract requires review from both ML Owner and Backend Owner.**

---

## 1. Contract Overview

The ML Output Contract defines the structured result that the ML pipeline produces for each analyzed entity (address or transaction). This is the interface boundary between the ML layer and the Backend layer.

```
ML Pipeline
     │
     │  List[MLResult]  (Python objects conforming to this schema)
     │
     ▼
Backend API
     │
     │  REST API JSON response (derived from MLResult)
     │
     ▼
Frontend
```

---

## 2. MLResult Schema

Each entity (address or transaction) that the ML pipeline analyzes produces one `MLResult` object.

### Python Representation (Pydantic model — PLANNED)

```python
class MLResult:
    entity_id: str                    # Bitcoin address or transaction ID
    entity_type: str                  # "address" | "transaction"
    analysis_id: str                  # UUID of the analysis run
    dataset_id: str                   # UUID of the analyzed dataset
    
    prediction: Prediction
    explanations: list[FeatureExplanation]
    features: list[FeatureValue]
    graph_evidence: list[GraphEvidence]
    
    model: ModelMetadata
    predicted_at: datetime            # UTC datetime
```

---

### 2.1 Prediction Schema

```python
class Prediction:
    anomaly_score: float              # Raw model anomaly score [0.0, 1.0]
    risk_score: float                 # Calibrated risk score [0.0, 1.0]
    risk_level: str                   # "low" | "medium" | "high" | "critical"
    prediction_label: str | None      # "illicit" | "licit" | "unknown" | null
    confidence: float | None          # Model confidence if available [0.0, 1.0]
```

**Field definitions**:

| Field | Type | Required | Range | Description |
|---|---|---|---|---|
| `anomaly_score` | `float` | Yes | [0.0, 1.0] | Raw model output, normalized. Higher = more anomalous. |
| `risk_score` | `float` | Yes | [0.0, 1.0] | Calibrated risk score for investigator use. See [risk-scoring.md](./risk-scoring.md). |
| `risk_level` | `string (enum)` | Yes | See enum | One of: `low`, `medium`, `high`, `critical` |
| `prediction_label` | `string \| null` | No | See enum | Classification label if supervised model was used. Null if unsupervised. |
| `confidence` | `float \| null` | No | [0.0, 1.0] | Model confidence in prediction. Null if not computable. |

**`risk_level` enum values**:

| Value | Risk Score Range | Meaning |
|---|---|---|
| `low` | [0.0, 0.32) | Low analytical priority |
| `medium` | [0.32, 0.50) | Warrants attention |
| `high` | [0.50, 0.67) | Significant risk indicators |
| `critical` | [0.67, 1.00] | Highest priority for investigation |

> **NOTE**: Risk score thresholds are `DECISION REQUIRED`. See [risk-scoring.md](./risk-scoring.md).

---

### 2.2 FeatureExplanation Schema

Each `FeatureExplanation` object represents one SHAP-derived explanation for a feature that contributed to the prediction.

```python
class FeatureExplanation:
    feature_name: str                 # Canonical feature name (from feature-specification.md)
    display_label: str                # Human-readable label for frontend display
    shap_value: float                 # Raw SHAP value (positive = increases risk, negative = decreases)
    direction: str                    # "increases_risk" | "decreases_risk" | "neutral"
    importance_rank: int              # 1-based rank (1 = most important for this entity)
    normalized_importance: float      # |shap_value| normalized to [0.0, 1.0] relative to this entity
    feature_value: float | int | str  # Actual value of this feature for this entity
    feature_unit: str | None          # Unit label for display (e.g., "BTC", "count", "days")
```

**Field definitions**:

| Field | Type | Required | Description |
|---|---|---|---|
| `feature_name` | `string` | Yes | Must match a canonical name in [feature-specification.md](./feature-specification.md) |
| `display_label` | `string` | Yes | Investigator-facing label (e.g., "Transaction velocity per day") |
| `shap_value` | `float` | Yes | Raw SHAP value. Sign indicates risk direction. |
| `direction` | `string (enum)` | Yes | `increases_risk`, `decreases_risk`, or `neutral` |
| `importance_rank` | `integer` | Yes | 1 = top contributor for this entity |
| `normalized_importance` | `float` | Yes | Relative importance [0.0, 1.0] |
| `feature_value` | `any` | Yes | The actual feature value for this entity |
| `feature_unit` | `string \| null` | No | Display unit |

**The frontend renders these as explanation cards.** Only the top N (suggested: 5–10) explanations should be included by default. The full list can be paginated.

---

### 2.3 FeatureValue Schema

Raw feature values for transparency/debugging (separate from explanations):

```python
class FeatureValue:
    feature_name: str                 # Canonical feature name
    raw_value: float | int | None     # Pre-normalization value
    normalized_value: float | None    # Post-normalization value fed to model
    is_imputed: bool                  # True if value was missing and imputed
    imputation_method: str | None     # "median" | "mean" | "zero" | null
```

---

### 2.4 GraphEvidence Schema

Graph-derived features and evidence that contributed to the risk assessment:

```python
class GraphEvidence:
    evidence_type: str               # "graph_metric" | "neighborhood" | "path"
    label: str                       # Human-readable label
    feature_name: str                # Canonical graph feature name
    value: float | int               # Value for this entity
    description: str                 # One-sentence investigator explanation
```

**Examples**:
```json
[
  {
    "evidenceType": "graph_metric",
    "label": "Network Centrality",
    "featureName": "graph_pagerank",
    "value": 0.00891,
    "description": "This address has unusually high centrality — it appears in many transaction paths."
  },
  {
    "evidenceType": "graph_metric",
    "label": "Cluster Size",
    "featureName": "graph_connected_component_size",
    "value": 1843,
    "description": "This address belongs to a large cluster of 1,843 interconnected addresses."
  }
]
```

---

### 2.5 ModelMetadata Schema

Provenance metadata for the model that produced this prediction:

```python
class ModelMetadata:
    model_id: str                    # Model identifier (e.g., "isolation_forest_v1")
    model_version: str               # Semver (e.g., "1.0.0")
    feature_schema_version: str      # Feature schema version (e.g., "1.0.0")
    model_type: str                  # "anomaly_detection" | "classification"
    algorithm: str                   # "IsolationForest" | "XGBoost" | etc.
```

---

## 3. Complete JSON Example

This is the JSON form of an `MLResult` as it would be stored or passed to the backend:

```json
{
  "entityId": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
  "entityType": "address",
  "analysisId": "550e8400-e29b-41d4-a716-446655440000",
  "datasetId": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "prediction": {
    "anomalyScore": 0.87,
    "riskScore": 0.82,
    "riskLevel": "high",
    "predictionLabel": null,
    "confidence": null
  },
  "explanations": [
    {
      "featureName": "addr_tx_per_day",
      "displayLabel": "Transaction velocity per day",
      "shapValue": 0.234,
      "direction": "increases_risk",
      "importanceRank": 1,
      "normalizedImportance": 1.0,
      "featureValue": 47.3,
      "featureUnit": "tx/day"
    },
    {
      "featureName": "graph_pagerank",
      "displayLabel": "Network centrality",
      "shapValue": 0.187,
      "direction": "increases_risk",
      "importanceRank": 2,
      "normalizedImportance": 0.80,
      "featureValue": 0.00891,
      "featureUnit": null
    }
  ],
  "features": [
    {
      "featureName": "addr_tx_per_day",
      "rawValue": 47.3,
      "normalizedValue": 0.932,
      "isImputed": false,
      "imputationMethod": null
    }
  ],
  "graphEvidence": [
    {
      "evidenceType": "graph_metric",
      "label": "Network Centrality",
      "featureName": "graph_pagerank",
      "value": 0.00891,
      "description": "This address has unusually high centrality in the transaction network."
    }
  ],
  "model": {
    "modelId": "isolation_forest_v1",
    "modelVersion": "1.0.0",
    "featureSchemaVersion": "1.0.0",
    "modelType": "anomaly_detection",
    "algorithm": "IsolationForest"
  },
  "predictedAt": "2026-09-11T16:30:00+00:00"
}
```

---

## 4. Contract Invariants

The following invariants MUST always hold. Backend validation should enforce them.

| Invariant | Rule |
|---|---|
| `anomaly_score` bounded | `0.0 ≤ anomaly_score ≤ 1.0` |
| `risk_score` bounded | `0.0 ≤ risk_score ≤ 1.0` |
| `risk_level` consistent | `risk_level` must match the `risk_score` range |
| `entity_type` valid | Must be `"address"` or `"transaction"` |
| `feature_name` canonical | Must match a name in [feature-specification.md](./feature-specification.md) |
| `importance_rank` ordered | `explanations` sorted by `importance_rank` ascending |
| `normalized_importance` range | `0.0 ≤ normalized_importance ≤ 1.0` |
| `direction` from sign | `direction` must agree with sign of `shap_value` |
| `model_id` non-empty | Cannot be null or empty string |
| `predicted_at` UTC | Must be UTC timezone-aware datetime |

---

## 5. What the Backend Must NOT Assume

- The backend must not assume a specific ML algorithm. The `algorithm` field tells it what was used.
- The backend must not assume `prediction_label` is always present (unsupervised models return null).
- The backend must not assume `confidence` is always present.
- The backend must not assume the top explanation is always the same feature across all entities.

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: ML Owner + Backend Owner (joint)*
*References: [feature-specification.md](./feature-specification.md) | [risk-scoring.md](./risk-scoring.md) | [explainability.md](./explainability.md) | [backend-ml-contract.md](../backend/backend-ml-contract.md)*

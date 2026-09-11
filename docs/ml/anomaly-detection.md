# Anomaly Detection

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Overview

Anomaly detection identifies Bitcoin addresses or transactions that exhibit statistically unusual behavior relative to the dataset population. An anomaly in this context is an entity whose behavioral features are significantly different from the norm — not a definitive indicator of criminal activity.

> **Critical disclaimer**: Anomaly detection produces analytical signals, not legal conclusions. An entity flagged as anomalous requires investigator review and contextual judgment.

---

## 2. Problem Framing

The system supports two detection modes depending on dataset availability:

### Mode 1: Unsupervised Anomaly Detection

**When to use**: No ground-truth labels are available (most real-world datasets).

**Approach**: Use the distribution of behavioral features to identify outliers.

**Algorithms (candidates)**:

| Algorithm | Library | Strength | Weakness |
|---|---|---|---|
| Isolation Forest | `sklearn.ensemble.IsolationForest` | Fast, scalable, handles high dimensions | Less interpretable |
| Local Outlier Factor | `sklearn.neighbors.LocalOutlierFactor` | Good for density-based anomalies | Slow on large datasets |
| One-Class SVM | `sklearn.svm.OneClassSVM` | Non-linear boundary | Sensitive to hyperparameters |

**Primary candidate**: Isolation Forest (`PLANNED`)

**Selection rationale**: Isolation Forest is efficient (O(n log n)), handles Bitcoin transaction feature distributions well (many near-zero values, heavy tails), and is supported by SHAP for explainability.

---

### Mode 2: Supervised Classification

**When to use**: Labeled training data is available (e.g., Elliptic dataset with illicit/licit labels).

**Approach**: Train a binary classifier on labeled data; predict probability of illicit behavior.

**Algorithms (candidates)**:

| Algorithm | Library | Strength |
|---|---|---|
| XGBoost | `xgboost.XGBClassifier` | State-of-the-art for tabular data |
| Random Forest | `sklearn.ensemble.RandomForestClassifier` | Robust baseline |
| Gradient Boosted Trees | `sklearn.ensemble.GradientBoostingClassifier` | Alternative GBM |

**Primary candidate**: XGBoost (`PLANNED`)

---

## 3. Class Imbalance Handling

In Bitcoin transaction datasets, illicit transactions are rare (<5% in Elliptic dataset). This imbalance must be addressed.

**Strategies**:

| Strategy | Method | Status |
|---|---|---|
| Class weight adjustment | `class_weight='balanced'` or manual weighting | `PLANNED` |
| SMOTE oversampling | `imbalanced-learn` (if added as dep) | `CANDIDATE` |
| Threshold tuning | Adjust classification threshold for precision/recall balance | `PLANNED` |
| Focal loss | XGBoost custom objective | `CANDIDATE` |

---

## 4. Anomaly Score Production

The raw model output is normalized to the range [0.0, 1.0] before being passed to the risk scoring stage.

### Isolation Forest

Isolation Forest returns a `decision_function` score in the range `(-inf, +inf)`. Normalization:

```python
# Raw scores from Isolation Forest
raw_scores = model.decision_function(X)

# Normalize to [0, 1] where 1 = most anomalous
# decision_function: negative = anomalous, positive = normal
anomaly_scores = 1 - (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min())
```

> `DECISION REQUIRED`: The exact normalization formula needs validation against a real dataset. The above is the proposed approach.

### XGBoost Classifier

XGBoost returns `predict_proba()`, the probability of the positive class (illicit). This is already in [0.0, 1.0]:

```python
# Probability of illicit class
anomaly_scores = model.predict_proba(X)[:, 1]
```

---

## 5. Feature Importance for Anomaly Detection

SHAP TreeExplainer works directly with both Isolation Forest and XGBoost. This produces per-feature SHAP values for each entity.

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
```

See [explainability.md](./explainability.md) for how SHAP values are transformed into the structured explanation contract.

---

## 6. Evaluation Strategy

See [model-evaluation.md](./model-evaluation.md) for the full evaluation framework.

**Key metrics for anomaly detection**:

| Metric | Relevance |
|---|---|
| AUPRC | Primary metric for imbalanced datasets |
| AUROC | Overall discrimination ability |
| Precision@K | Precision among top-K flagged entities |
| F1 Score (at optimal threshold) | Balance of precision and recall |

---

## 7. What Anomaly Detection Is NOT

| NOT | Correct interpretation |
|---|---|
| Proof of criminal activity | Probabilistic analytical signal |
| Legal evidence | Input to investigative judgment |
| Infallible | Subject to false positives and false negatives |
| Based on identity | Based only on behavioral patterns in the dataset |

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner*
*References: [feature-specification.md](./feature-specification.md) | [risk-scoring.md](./risk-scoring.md) | [model-evaluation.md](./model-evaluation.md)*

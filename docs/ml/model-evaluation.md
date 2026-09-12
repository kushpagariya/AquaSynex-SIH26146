# Model Evaluation

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Evaluation Philosophy

Model evaluation has two purposes:

1. **Internal validation** — Confirm the model performs at a level suitable for deployment.
2. **Investigator communication** — Provide honest performance metrics so investigators understand system limitations.

**Do not present optimistic metrics without methodology transparency.**

---

## 2. Evaluation Metrics

### For Supervised Classification (when labels available)

| Metric | Priority | Rationale |
|---|---|---|
| AUPRC (Area Under Precision-Recall Curve) | **Primary** | Best metric for imbalanced datasets |
| AUROC (Area Under ROC Curve) | Secondary | Discrimination ability |
| F1 Score (at optimal threshold) | Secondary | Harmonic balance of precision/recall |
| Precision at K | Tertiary | Top-K recall for investigation prioritization |
| Recall at chosen threshold | Required | Miss rate for illicit entities |
| Precision at chosen threshold | Required | False positive rate |

**Target thresholds** (`DECISION REQUIRED`):
- AUPRC > 0.80 for Phase 1
- Precision > 0.75 at recall > 0.70 for operational deployment

### For Unsupervised Anomaly Detection (no labels)

| Metric | Notes |
|---|---|
| Contamination rate | Expected fraction of anomalies; set as hyperparameter |
| Silhouette score (CANDIDATE) | Cluster quality if clustering is applied |
| Distribution analysis | Histogram of anomaly scores; expected bimodal for effective detector |
| Manual validation | Random sample of top-K anomalies reviewed by investigator |

---

## 3. Evaluation Protocol

### Supervised Protocol

```
Full labeled dataset
        │
        ▼
Stratified train/test split (80% / 20%)
        │
        ├── Training set → Fit model + scaler
        │
        └── Test set → Evaluate
              │
              ├── Compute metrics
              ├── Plot Precision-Recall curve
              ├── Plot ROC curve
              ├── Plot confusion matrix at chosen threshold
              └── Record in model metadata
```

### Cross-Validation

For hyperparameter tuning, use **5-fold stratified cross-validation** on the training set.

```python
from sklearn.model_selection import StratifiedKFold
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
```

---

## 4. Evaluation Artifacts

After training, the following artifacts must be saved alongside the model:

| Artifact | Format | Purpose |
|---|---|---|
| `evaluation_report.json` | JSON | All computed metrics |
| `pr_curve.png` | PNG | Precision-Recall curve |
| `roc_curve.png` | PNG | ROC curve |
| `feature_importance.json` | JSON | SHAP-based global feature importance |

---

## 5. Evaluation on New Datasets (Inference)

After inference on a new dataset:

| Check | Condition | Action |
|---|---|---|
| Score distribution | Anomaly scores are not all clustered at 0 or 1 | Warn about degenerate model |
| Top-K entities | Manual spot-check of top 5 flagged entities | Qualitative validation |
| Feature coverage | >50% of required features are available | Warn if coverage is low |

---

## 6. Minimum Acceptance Criteria

Before deploying a model to the `/models/` directory for inference:

| Criterion | Requirement |
|---|---|
| Labeled evaluation | If labels available: AUPRC > 0.75 |
| Feature coverage | Model was trained on ≥ 70% of planned features |
| Evaluation report | `evaluation_report.json` exists |
| Model metadata | `model_metadata.json` exists with all required fields |
| No data leakage | Test set was not used during training or hyperparameter tuning |

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: ML Owner*
*References: [anomaly-detection.md](./anomaly-detection.md) | [model-versioning.md](./model-versioning.md)*

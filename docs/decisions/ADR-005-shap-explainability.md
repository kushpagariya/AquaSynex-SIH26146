# ADR-005: Use SHAP for ML Explainability

**Status**: ACCEPTED

**Date**: 2026-09-11

**Decision Makers**: All subsystem owners

---

## Context

Forensic tools must explain why an entity is flagged. "Black box" ML output is insufficient for investigation use. The explainability method must:
- Work with tree-based models (Isolation Forest, XGBoost)
- Be computationally feasible
- Produce per-feature contributions per entity
- Be available offline (Python library)

## Decision

**Use the `shap` Python library with `TreeExplainer` for per-entity feature importance.**

## Rationale

- **TreeExplainer**: Efficiently computes exact SHAP values for tree-based models in polynomial time
- **Theoretical foundation**: SHAP values are grounded in cooperative game theory (Shapley values)
- **Investigator interpretability**: Directional contribution per feature is understandable without ML expertise
- **Library support**: `shap` is well-maintained, widely used, and fully installable offline

## Alternatives Evaluated

| Method | Eliminated for |
|---|---|
| LIME | Approximation; can be unstable; slower |
| Feature importance (Gini) | Global only; not per-entity |
| Permutation importance | Slow; not per-entity |
| Attention weights | Only for neural networks; not applicable |
| **SHAP** | **Selected** |

## Consequences

### Positive
- Consistent, mathematically sound per-entity explanations
- Works for Isolation Forest and XGBoost
- Output can be visualized as waterfall/bar charts

### Negative / Constraints
- SHAP can be slow for very large datasets (use sampling if needed)
- `KernelExplainer` (for non-tree models) is significantly slower
- SHAP interpretability still requires investigator training

---

*Owner: ML Owner | Status: ACCEPTED*

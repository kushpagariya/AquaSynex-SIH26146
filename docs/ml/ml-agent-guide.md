# ML Agent Guide

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This document is written for the AI coding agent responsible for the ML subsystem.**
> Read this before writing any code.

---

## 1. Your Subsystem

You own the **ML / Data / Graph subsystem**. This includes:

- Data ingestion pipeline (`pipeline/data/` or `src/data/`)
- Data normalization and canonical record production
- Feature engineering
- Graph construction and analysis (NetworkX)
- ML model training and inference (Scikit-learn, XGBoost)
- Risk scoring
- SHAP explainability
- ML result production (output contract)

---

## 2. Mandatory Reading Before Coding

Read these documents **in order** before writing any code:

1. [`docs/README.md`](../README.md) — Project overview and source-of-truth hierarchy
2. [`docs/data/canonical-schema.md`](../data/canonical-schema.md) — Your input format
3. [`docs/data/data-dictionary.md`](../data/data-dictionary.md) — Authoritative field definitions
4. [`docs/ml/feature-specification.md`](./feature-specification.md) — Authoritative feature definitions
5. [`docs/ml/model-input-contract.md`](./model-input-contract.md) — What you must produce as input to model
6. [`docs/ml/model-output-contract.md`](./model-output-contract.md) — **What you must produce as output**
7. [`docs/graph/graph-schema.md`](../graph/graph-schema.md) — Graph node/edge schema
8. [`docs/development/naming-conventions.md`](../development/naming-conventions.md) — Naming rules
9. [`docs/development/agent-development-rules.md`](../development/agent-development-rules.md) — Agent rules

---

## 3. Your Responsibilities

You are responsible for:

| Responsibility | Document |
|---|---|
| Ingesting raw dataset files | [data-sources.md](../data/data-sources.md) |
| Normalizing to canonical schema | [data-normalization.md](../data/data-normalization.md) |
| Writing canonical records to DuckDB/Parquet | [canonical-schema.md](../data/canonical-schema.md) |
| Engineering features | [feature-specification.md](./feature-specification.md) |
| Building the NetworkX graph | [graph-construction.md](../graph/graph-construction.md) |
| Extracting graph features | [graph-features.md](../graph/graph-features.md) |
| Training ML models | [ml-architecture.md](./ml-architecture.md) |
| Running inference | [model-input-contract.md](./model-input-contract.md) |
| Producing risk scores | [risk-scoring.md](./risk-scoring.md) |
| Producing SHAP explanations | [explainability.md](./explainability.md) |
| Producing `MLResult` objects | [model-output-contract.md](./model-output-contract.md) |
| Saving/loading model artifacts | [model-versioning.md](./model-versioning.md) |

---

## 4. What You Must NOT Do

| Forbidden | Why |
|---|---|
| Modify `backend/` source code | Backend is owned by the Backend Owner |
| Define new API routes | API is owned by the Backend Owner |
| Directly query the backend's DuckDB tables | You write Parquet; backend reads via DuckDB |
| Render any UI | Frontend is owned by the Frontend Owner |
| Change the canonical schema without updating the documentation | Schema changes affect all subsystems |
| Change the ML output contract schema without notifying the Backend Owner | Backend depends on this contract |
| Add new Python dependencies without updating `requirements.txt` and checking Docker compatibility | Dependency changes affect deployment |
| Call external APIs at runtime | Offline constraint (ADR-002) |

---

## 5. Files You Own

```
pipeline/
├── data/
│   ├── loader.py          # File ingestion
│   ├── validator.py       # Dataset validation
│   ├── normalizer.py      # Normalization to canonical schema
│   └── duckdb_writer.py   # Write canonical records to DuckDB/Parquet
├── graph/
│   ├── graph_builder.py   # NetworkX graph construction
│   ├── graph_features.py  # Graph feature extraction
│   └── graph_exporter.py  # Serialize graph for API
└── ml/
    ├── feature_engineering.py  # Tabular feature computation
    ├── model_trainer.py         # Training
    ├── model_inference.py       # Inference entry point
    ├── risk_scorer.py           # Risk score computation
    ├── explainer.py             # SHAP explanation
    └── result_builder.py        # Assemble MLResult objects
```

> **Status**: Directory structure is `PLANNED`. Create it when implementation begins.

---

## 6. Files You May Read (But Must Not Modify)

```
backend/        # Read to understand how your output is consumed
docs/           # All documentation (read freely, modify with care)
```

---

## 7. Files You Must Not Modify Without Coordination

| File/Dir | Owner | Why |
|---|---|---|
| `backend/` | Backend Owner | API and database |
| `frontend/` | Frontend Owner | UI |
| `docs/data/canonical-schema.md` | All owners | Shared contract |
| `docs/ml/model-output-contract.md` | ML + Backend | Shared contract |
| `docs/graph/graph-schema.md` | ML + Backend + Frontend | Shared contract |

---

## 8. Upstream Dependencies

| Dependency | Source |
|---|---|
| Raw dataset files | Uploaded by investigator via backend API |
| DuckDB canonical records | Written by your data pipeline |
| Feature schema version | Defined in [feature-specification.md](./feature-specification.md) |

---

## 9. Downstream Consumers

| Consumer | What they receive | Document |
|---|---|---|
| Backend | `List[MLResult]` — structured prediction results | [model-output-contract.md](./model-output-contract.md) |
| Backend | Parquet files in `/data/` | [canonical-schema.md](../data/canonical-schema.md) |
| Backend | Graph topology JSON (via `graph_exporter.py`) | [graph-schema.md](../graph/graph-schema.md) |

---

## 10. Common Mistakes to Avoid

| Mistake | What to do instead |
|---|---|
| Inventing a new field name for a concept already in the data dictionary | Check [data-dictionary.md](../data/data-dictionary.md) first |
| Returning BTC float values | Always use satoshis (integer) internally |
| Returning raw SHAP values without structuring | Use the `FeatureExplanation` contract |
| Assuming all canonical fields are always available | Check `available_fields` in dataset metadata |
| Storing model artifacts as raw pickle without metadata sidecar | Always save `model_metadata.json` alongside |
| Training the scaler on inference data | Scaler is always fit on training data only |
| Using NaN values in the feature matrix | Impute all missing values before passing to model |

---

## 11. Integration Checklist

Before declaring your ML component ready for integration:

- [ ] Data pipeline writes canonical records to DuckDB (all required fields populated or null)
- [ ] Graph is constructed from canonical data (no errors for missing address fields)
- [ ] Feature engineering produces all `PLANNED` features from [feature-specification.md](./feature-specification.md)
- [ ] All features are imputed (no NaN in feature matrix)
- [ ] Model inference runs without error on sample dataset
- [ ] `MLResult` objects pass schema validation against [model-output-contract.md](./model-output-contract.md)
- [ ] SHAP explanations use canonical feature names
- [ ] Display labels are set from [feature-specification.md](./feature-specification.md)
- [ ] Model metadata JSON is saved alongside artifact
- [ ] All value fields use satoshis (integer), not BTC float
- [ ] No external API calls
- [ ] Tests exist for feature engineering, model inference, and result schema
- [ ] Docker compatibility confirmed (requirements.txt updated)

---

*Last updated: 2026-09-11 | Owner: ML Owner*

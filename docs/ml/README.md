# ML Subsystem

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the ML subsystem entry point.**
> If you are the ML agent, start by reading `docs/README.md`, then follow the reading sequence in [ml-agent-guide.md](./ml-agent-guide.md).

---

## Subsystem Overview

The ML subsystem owns the analytical intelligence of the platform. It is responsible for:

1. **Feature engineering** — deriving analytical features from canonical transaction and graph data.
2. **Graph construction & analysis** — building and analyzing the transaction graph using NetworkX.
3. **Anomaly detection** — identifying statistically unusual entities using ML models.
4. **Risk scoring** — converting model output to a calibrated, investigator-interpretable risk score.
5. **Explainability** — using SHAP to explain which features drove each risk score.

## Owner

**ML Owner** — responsible for all code in `pipeline/` or `src/ml/`, `src/graph/`, `src/data/`.

## Branches

| Branch | Purpose |
|---|---|
| `ml` | ML model code, training, inference, SHAP |
| `graph_analysis` | Graph construction and analytics |
| `data_pipeline` | Data ingestion, normalization |

## Key Contracts (Must Read Before Coding)

| Document | Purpose |
|---|---|
| [model-input-contract.md](./model-input-contract.md) | What the ML model receives as input |
| [model-output-contract.md](./model-output-contract.md) | **What the ML model produces** — consumed by Backend |
| [feature-specification.md](./feature-specification.md) | All features: definition, type, formula |
| [../graph/graph-schema.md](../graph/graph-schema.md) | Graph node/edge representation |
| [../data/canonical-schema.md](../data/canonical-schema.md) | Input data format from data pipeline |

## Documents in This Directory

| Document | Status | Purpose |
|---|---|---|
| [ml-architecture.md](./ml-architecture.md) | `PLANNED` | Pipeline architecture |
| [feature-specification.md](./feature-specification.md) | `IN PROGRESS` | Feature definitions |
| [anomaly-detection.md](./anomaly-detection.md) | `PLANNED` | Detection approach |
| [risk-scoring.md](./risk-scoring.md) | `DECISION REQUIRED` | Risk score formula |
| [explainability.md](./explainability.md) | `PLANNED` | SHAP contract |
| [model-input-contract.md](./model-input-contract.md) | `IN PROGRESS` | Input contract |
| [model-output-contract.md](./model-output-contract.md) | `IN PROGRESS` | **Output contract** |
| [model-evaluation.md](./model-evaluation.md) | `PLANNED` | Evaluation metrics |
| [model-versioning.md](./model-versioning.md) | `PLANNED` | Version tracking |
| [ml-agent-guide.md](./ml-agent-guide.md) | `IN PROGRESS` | Agent guide |

---

*Last updated: 2026-09-11 | Owner: ML Owner*

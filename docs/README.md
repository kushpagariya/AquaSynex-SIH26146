# SIH26146 – Documentation Index

**AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **For AI Coding Agents**: Before writing any code, read this document in full, then follow the
> "Mandatory Reading" sequence for your subsystem listed in the [Agent Start Guide](#agent-start-guide).

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture Summary](#2-system-architecture-summary)
3. [Technology Stack](#3-technology-stack)
4. [Subsystem Ownership](#4-subsystem-ownership)
5. [Documentation Hierarchy & Source-of-Truth Rules](#5-documentation-hierarchy--source-of-truth-rules)
6. [Documentation Map](#6-documentation-map)
7. [Agent Start Guide](#7-agent-start-guide)
8. [Integration Contracts Summary](#8-integration-contracts-summary)
9. [Implementation Status](#9-implementation-status)
10. [How Documentation Changes Must Be Made](#10-how-documentation-changes-must-be-made)

---

## 1. Project Overview

**SIH Problem Statement**: SIH26146  
**Team**: AquaSynex  
**Category**: Bitcoin Transaction Forensic Analysis  

This system is an **offline, AI-powered Bitcoin transaction investigation and forensic analysis platform**. It is designed to help law-enforcement investigators and financial analysts:

1. Understand what happened in a set of Bitcoin transactions.
2. Identify which addresses/entities are connected.
3. Determine why an entity appears suspicious based on behavioral signals.
4. Explore transaction paths and behavioral patterns through an interactive graph.
5. Understand what features contributed to a risk score.
6. Assess system confidence in anomaly/risk predictions.
7. Conduct end-to-end investigations using a single integrated dashboard.

**This is ONE unified system.** It is not three independent applications. Every subsystem exists to serve the investigation workflow.

---

## 2. System Architecture Summary

```
Raw Bitcoin Transaction Dataset
            │
            ▼
      Data Ingestion  ──────────────────────────────────────────────[Data Layer]
            │
            ▼
   Cleaning / Normalization  ────────────────────────────────────────[Data Layer]
            │
            ▼
     Feature Engineering  ──────────────────────────────────────────[ML/Data Layer]
            │
   ┌────────┴────────┬────────────────────┐
   ▼                 ▼                    ▼
Tx Features    Address Features    Temporal Features
            │
            ▼
     Graph Construction  ─────────────────────────────────────────[Graph Layer]
            │
            ▼
     Graph Analysis (NetworkX)  ─────────────────────────────────[Graph Layer]
            │
            ▼
     ML / Anomaly Detection  ────────────────────────────────────[ML Layer]
            │
            ▼
       Risk Scoring  ───────────────────────────────────────────[ML Layer]
            │
            ▼
      Explainability (SHAP)  ─────────────────────────────────────[ML Layer]
            │
            ▼
        Backend API (FastAPI)  ──────────────────────────────────[Backend Layer]
            │
            ▼
   Investigation Dashboard (React)  ──────────────────────────────[Frontend Layer]
            │
            ▼
 Dockerized Offline Linux Deployment
```

**Key constraint**: Every component must function without internet access at runtime. See [ADR-002](./decisions/ADR-002-offline-first-architecture.md).

---

## 3. Technology Stack

| Layer | Technology | Version Constraint |
|---|---|---|
| Frontend Framework | React.js + Vite | Latest stable |
| Frontend Styling | Tailwind CSS | Latest stable |
| Frontend Charts | Recharts | Latest stable |
| Frontend Graph | Cytoscape.js | Latest stable |
| Backend Framework | FastAPI | Latest stable |
| Backend Language | Python | ≥ 3.10 |
| ML / Data | Pandas, NumPy | Latest stable |
| ML Models | Scikit-learn, XGBoost | Latest stable |
| Explainability | SHAP | Latest stable |
| Graph Analysis | NetworkX | Latest stable |
| Database | DuckDB | Latest stable |
| Deployment | Docker + Docker Compose | Latest stable |
| Target OS | Linux / Ubuntu | ≥ 22.04 |
| Dev OS | Windows (compatible) | — |

> **FORBIDDEN at runtime**: PostgreSQL, MongoDB, MySQL, Redis, Elasticsearch, Neo4j, cloud APIs, CDN resources, external authentication providers, remote LLMs.
>
> See [ADR-001](./decisions/ADR-001-duckdb-selection.md) for database decision and [ADR-002](./decisions/ADR-002-offline-first-architecture.md) for offline constraint.

---

## 4. Subsystem Ownership

| Phase | Subsystem | Owner Role | Branch |
|---|---|---|---|
| Phase 2 | ML / Data / Graph | ML Owner | `ml`, `graph_analysis`, `data_pipeline` |
| Phase 3 | Backend / API / Database | Backend Owner | `backend` |
| Phase 4 | Frontend / UI | Frontend Owner | `frontend` |
| Phase 5–8 | Integration, Deployment, Demo | All three jointly | `main` |

### Ownership Rules

- Each owner **writes code** for their subsystem.
- Each owner **maintains documentation** for their subsystem.
- **Shared contracts** (API schemas, ML output contract, graph schema) require agreement from all affected owners before change.
- `main` is the stable integration branch. All integration happens via Pull Request.
- Never force-push to `main`.

See [ADR-003](./decisions/ADR-003-three-subsystem-ownership.md) for the ownership model decision.

---

## 5. Documentation Hierarchy & Source-of-Truth Rules

When two documents disagree, the following precedence applies (higher = wins):

```
1. Architecture Decision Records (docs/decisions/)
        │
        ▼
2. Canonical Data Model (docs/data/canonical-schema.md + data-dictionary.md)
        │
        ├─────────────────────────────────────┐
        ▼                                     ▼
3a. ML Output Contract                  3b. API Contract
    (docs/ml/model-output-contract.md)       (docs/backend/api-specification.md)
        │                                     │
        ▼                                     ▼
4a. Graph Contract                      4b. Frontend-Backend Contract
    (docs/graph/graph-schema.md)             (docs/frontend/frontend-backend-contract.md)
        │
        ▼
5. Naming Conventions (docs/development/naming-conventions.md)
        │
        ▼
6. Validation Rules (docs/backend/validation-rules.md)
        │
        ▼
7. Implementation Documentation
        │
        ▼
8. Code
```

**The cardinal rule**:

> **Code must not silently redefine an established contract.**

If an implementation requires changing a contract, the process is:

```
Proposed change
      ↓
Update documentation (draft)
      ↓
Impact analysis across all affected subsystems
      ↓
All affected owners review and approve
      ↓
Implementation
      ↓
Integration tests pass
      ↓
Documentation finalized
```

---

## 6. Documentation Map

### Architecture

| Document | Purpose |
|---|---|
| [current-state-project-context.md](./current-state-project-context.md) | **Authoritative** current-state project context, verified implementation blueprint & ground truth |
| [system-architecture.md](./architecture/system-architecture.md) | Complete system architecture with component detail |
| [system-context.md](./architecture/system-context.md) | External context, actors, and system boundaries |
| [component-responsibilities.md](./architecture/component-responsibilities.md) | Component responsibility matrix |
| [architecture-decisions.md](./architecture/architecture-decisions.md) | Summary of all architecture decisions |
| [deployment-architecture.md](./architecture/deployment-architecture.md) | Docker and deployment topology |

### Data

| Document | Purpose |
|---|---|
| [data-sources.md](./data/data-sources.md) | Dataset sources, formats, and ingestion assumptions |
| [data-dictionary.md](./data/data-dictionary.md) | **Authoritative** field definitions for all data entities |
| [canonical-schema.md](./data/canonical-schema.md) | **Authoritative** canonical data model for internal processing |
| [data-validation.md](./data/data-validation.md) | Validation rules for all data fields |
| [data-normalization.md](./data/data-normalization.md) | Normalization and cleaning rules |
| [data-lineage.md](./data/data-lineage.md) | Data provenance tracking from source to prediction |
| [sample-dataset-format.md](./data/sample-dataset-format.md) | Sample format and field examples |

### ML

| Document | Purpose |
|---|---|
| [ml/README.md](./ml/README.md) | ML subsystem overview and agent entry point |
| [ml-architecture.md](./ml/ml-architecture.md) | ML pipeline architecture |
| [feature-specification.md](./ml/feature-specification.md) | **Authoritative** feature definitions |
| [anomaly-detection.md](./ml/anomaly-detection.md) | Anomaly detection approach and algorithms |
| [risk-scoring.md](./ml/risk-scoring.md) | Risk score definition, formula, and levels |
| [explainability.md](./ml/explainability.md) | SHAP-based explanation contract |
| [model-input-contract.md](./ml/model-input-contract.md) | **Contract**: What ML receives as input |
| [model-output-contract.md](./ml/model-output-contract.md) | **Contract**: What ML produces as output |
| [model-evaluation.md](./ml/model-evaluation.md) | Evaluation metrics and thresholds |
| [model-versioning.md](./ml/model-versioning.md) | Model version tracking and provenance |
| [ml-agent-guide.md](./ml/ml-agent-guide.md) | **Read this first** if you are the ML agent |

### Graph

| Document | Purpose |
|---|---|
| [graph-architecture.md](./graph/graph-architecture.md) | Graph subsystem architecture |
| [graph-schema.md](./graph/graph-schema.md) | **Authoritative** graph node/edge schema |
| [graph-construction.md](./graph/graph-construction.md) | How the graph is built from canonical data |
| [graph-features.md](./graph/graph-features.md) | Graph-derived features for ML |
| [graph-analysis.md](./graph/graph-analysis.md) | Graph algorithms and analytics |
| [graph-agent-guide.md](./graph/graph-agent-guide.md) | **Read this first** if you are the graph agent |

### Backend

| Document | Purpose |
|---|---|
| [backend/README.md](./backend/README.md) | Backend subsystem overview and agent entry point |
| [backend-architecture.md](./backend/backend-architecture.md) | FastAPI service architecture |
| [api-specification.md](./backend/api-specification.md) | **Authoritative** REST API specification |
| [api-reference.md](./backend/api-reference.md) | Quick-reference for all endpoints |
| [request-response-schemas.md](./backend/request-response-schemas.md) | **Contract**: All request/response schemas |
| [error-handling.md](./backend/error-handling.md) | **Authoritative** error codes and formats |
| [validation-rules.md](./backend/validation-rules.md) | **Authoritative** API input validation rules |
| [duckdb-schema.md](./backend/duckdb-schema.md) | DuckDB tables, columns, and query patterns |
| [backend-ml-contract.md](./backend/backend-ml-contract.md) | **Contract**: Backend ↔ ML layer interface |
| [backend-agent-guide.md](./backend/backend-agent-guide.md) | **Read this first** if you are the backend agent |
| [configuration.md](./backend/configuration.md) | Configuration and environment variables |

### Frontend

| Document | Purpose |
|---|---|
| [frontend/README.md](./frontend/README.md) | Frontend subsystem overview and agent entry point |
| [frontend-architecture.md](./frontend/frontend-architecture.md) | React application architecture |
| [ui-architecture.md](./frontend/ui-architecture.md) | UI layer design, layout, and navigation |
| [page-specification.md](./frontend/page-specification.md) | Page-level specifications and routes |
| [component-specification.md](./frontend/component-specification.md) | Component-level specifications |
| [visualization-specification.md](./frontend/visualization-specification.md) | Chart and graph visualization specs |
| [frontend-backend-contract.md](./frontend/frontend-backend-contract.md) | **Contract**: What the frontend receives from backend |
| [state-management.md](./frontend/state-management.md) | Application state management approach |
| [frontend-validation.md](./frontend/frontend-validation.md) | Client-side validation rules |
| [frontend-agent-guide.md](./frontend/frontend-agent-guide.md) | **Read this first** if you are the frontend agent |

### Integration

| Document | Purpose |
|---|---|
| [integration-architecture.md](./integration/integration-architecture.md) | End-to-end integration topology |
| [integration-contracts.md](./integration/integration-contracts.md) | All inter-subsystem contracts |
| [end-to-end-data-flow.md](./integration/end-to-end-data-flow.md) | Complete data flow from ingestion to UI |
| [interface-versioning.md](./integration/interface-versioning.md) | Interface version management |
| [integration-checklist.md](./integration/integration-checklist.md) | Integration validation checklist |
| [integration-agent-guide.md](./integration/integration-agent-guide.md) | Integration agent responsibilities |

### Development

| Document | Purpose |
|---|---|
| [project-structure.md](./development/project-structure.md) | Repository layout and directory conventions |
| [naming-conventions.md](./development/naming-conventions.md) | **Authoritative** naming rules for all layers |
| [development-workflow.md](./development/development-workflow.md) | Branch, PR, and review workflow |
| [coding-standards.md](./development/coding-standards.md) | Code quality and style standards |
| [testing-strategy.md](./development/testing-strategy.md) | Testing pyramid and test requirements |
| [test-data-strategy.md](./development/test-data-strategy.md) | Test data creation and management |
| [agent-development-rules.md](./development/agent-development-rules.md) | **Rules for AI coding agents** |

### Deployment

| Document | Purpose |
|---|---|
| [docker-architecture.md](./deployment/docker-architecture.md) | Docker service topology |
| [docker-compose.md](./deployment/docker-compose.md) | Docker Compose configuration guide |
| [offline-deployment.md](./deployment/offline-deployment.md) | Offline deployment requirements and procedure |
| [linux-deployment.md](./deployment/linux-deployment.md) | Linux/Ubuntu deployment steps |
| [environment-variables.md](./deployment/environment-variables.md) | All environment variables and defaults |
| [deployment-checklist.md](./deployment/deployment-checklist.md) | Pre-deployment validation checklist |

### Architecture Decision Records

| Document | Decision |
|---|---|
| [decisions/README.md](./decisions/README.md) | ADR index and process |
| [ADR-001](./decisions/ADR-001-duckdb-selection.md) | DuckDB as analytical database |
| [ADR-002](./decisions/ADR-002-offline-first-architecture.md) | Offline-first architecture |
| [ADR-003](./decisions/ADR-003-three-subsystem-ownership.md) | Three-subsystem ownership model |
| [ADR-004](./decisions/ADR-004-contract-first-integration.md) | Contract-first integration approach |

---

## 7. Agent Start Guide

### If you are the **ML Agent**

Read in this order:
1. This document (`docs/README.md`)
2. [`docs/ml/ml-agent-guide.md`](./ml/ml-agent-guide.md)
3. [`docs/data/canonical-schema.md`](./data/canonical-schema.md)
4. [`docs/data/data-dictionary.md`](./data/data-dictionary.md)
5. [`docs/ml/feature-specification.md`](./ml/feature-specification.md)
6. [`docs/ml/model-input-contract.md`](./ml/model-input-contract.md)
7. [`docs/ml/model-output-contract.md`](./ml/model-output-contract.md)
8. [`docs/graph/graph-schema.md`](./graph/graph-schema.md)
9. [`docs/development/naming-conventions.md`](./development/naming-conventions.md)
10. [`docs/development/agent-development-rules.md`](./development/agent-development-rules.md)

### If you are the **Backend Agent**

Read in this order:
1. This document (`docs/README.md`)
2. [`docs/backend/backend-agent-guide.md`](./backend/backend-agent-guide.md)
3. [`docs/backend/api-specification.md`](./backend/api-specification.md)
4. [`docs/backend/request-response-schemas.md`](./backend/request-response-schemas.md)
5. [`docs/backend/duckdb-schema.md`](./backend/duckdb-schema.md)
6. [`docs/backend/error-handling.md`](./backend/error-handling.md)
7. [`docs/ml/model-output-contract.md`](./ml/model-output-contract.md)
8. [`docs/backend/backend-ml-contract.md`](./backend/backend-ml-contract.md)
9. [`docs/data/canonical-schema.md`](./data/canonical-schema.md)
10. [`docs/development/naming-conventions.md`](./development/naming-conventions.md)
11. [`docs/development/agent-development-rules.md`](./development/agent-development-rules.md)

### If you are the **Frontend Agent**

Read in this order:
1. This document (`docs/README.md`)
2. [`docs/frontend/frontend-agent-guide.md`](./frontend/frontend-agent-guide.md)
3. [`docs/frontend/frontend-backend-contract.md`](./frontend/frontend-backend-contract.md)
4. [`docs/backend/api-specification.md`](./backend/api-specification.md)
5. [`docs/backend/request-response-schemas.md`](./backend/request-response-schemas.md)
6. [`docs/backend/error-handling.md`](./backend/error-handling.md)
7. [`docs/frontend/page-specification.md`](./frontend/page-specification.md)
8. [`docs/frontend/component-specification.md`](./frontend/component-specification.md)
9. [`docs/frontend/visualization-specification.md`](./frontend/visualization-specification.md)
10. [`docs/development/naming-conventions.md`](./development/naming-conventions.md)
11. [`docs/development/agent-development-rules.md`](./development/agent-development-rules.md)

### If you are the **Integration Agent**

Read in this order:
1. This document (`docs/README.md`)
2. [`docs/integration/integration-agent-guide.md`](./integration/integration-agent-guide.md)
3. [`docs/integration/integration-contracts.md`](./integration/integration-contracts.md)
4. [`docs/integration/end-to-end-data-flow.md`](./integration/end-to-end-data-flow.md)
5. [`docs/integration/integration-checklist.md`](./integration/integration-checklist.md)
6. All subsystem-specific contracts (ML output, API spec, frontend-backend contract)

---

## 8. Integration Contracts Summary

The following are the **mandatory inter-subsystem contracts**. Changing any of these requires review from all affected owners.

| Contract | Location | Producers | Consumers |
|---|---|---|---|
| Canonical Data Schema | [`data/canonical-schema.md`](./data/canonical-schema.md) | Data Pipeline | ML, Graph, Backend |
| Feature Specification | [`ml/feature-specification.md`](./ml/feature-specification.md) | ML (feature eng.) | ML model, Graph |
| Graph Schema | [`graph/graph-schema.md`](./graph/graph-schema.md) | Graph Layer | ML, Backend, Frontend |
| ML Input Contract | [`ml/model-input-contract.md`](./ml/model-input-contract.md) | Backend / Orchestration | ML Model |
| ML Output Contract | [`ml/model-output-contract.md`](./ml/model-output-contract.md) | ML Layer | Backend |
| API Specification | [`backend/api-specification.md`](./backend/api-specification.md) | Backend | Frontend |
| Request/Response Schemas | [`backend/request-response-schemas.md`](./backend/request-response-schemas.md) | Backend | Frontend |
| Frontend-Backend Contract | [`frontend/frontend-backend-contract.md`](./frontend/frontend-backend-contract.md) | Backend | Frontend |
| Error Contract | [`backend/error-handling.md`](./backend/error-handling.md) | Backend | Frontend |
| Cytoscape Graph Contract | [`frontend/visualization-specification.md`](./frontend/visualization-specification.md) | Backend | Frontend (Cytoscape.js) |

---

## 9. Implementation Status

> **Status Labels Used Throughout Documentation**:
> - `IMPLEMENTED` – Code exists and is tested.
> - `IN PROGRESS` – Actively being developed.
> - `PLANNED` – Agreed and will be built.
> - `PROPOSED` – Suggested but not yet approved.
> - `DECISION REQUIRED` – A decision must be made before implementation.
> - `FUTURE` – May be added in a later phase.

| Component | Status |
|---|---|
| Repository structure | `IN PROGRESS` |
| Documentation foundation | `IN PROGRESS` |
| Data ingestion pipeline | `PLANNED` |
| Data normalization | `PLANNED` |
| Feature engineering | `PLANNED` |
| Graph construction (NetworkX) | `PLANNED` |
| Graph analysis | `PLANNED` |
| Anomaly detection (ML) | `PLANNED` |
| Risk scoring | `PLANNED` |
| Explainability (SHAP) | `PLANNED` |
| FastAPI backend | `PLANNED` |
| DuckDB integration | `PLANNED` |
| React frontend | `PLANNED` |
| Cytoscape.js graph explorer | `PLANNED` |
| Docker deployment | `PLANNED` |
| Offline Linux deployment | `PLANNED` |
| Integration tests | `PLANNED` |

---

## 10. How Documentation Changes Must Be Made

### Minor documentation changes (typo, clarification, non-contract)

1. Update the document directly.
2. Commit on the relevant branch.
3. Include `docs:` prefix in commit message.

### Contract changes (API, schema, ML output, naming, error codes)

```
1. Create a draft update to the relevant contract document.
2. Open a discussion (GitHub Issue or PR comment) tagging all affected owners.
3. Perform impact analysis: list all documents and code files that reference the changed contract.
4. All affected owners approve the change.
5. Implement corresponding code change.
6. Update ALL documents that reference the changed field/schema/endpoint.
7. Run integration tests.
8. Merge to main only after tests pass.
```

### New ADR

If a significant architectural decision is being made:
1. Create a new `ADR-NNN-title.md` in `docs/decisions/`.
2. Reference it from `docs/decisions/README.md` and `docs/architecture/architecture-decisions.md`.
3. Link to it from affected subsystem documentation.

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: All*

# System Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Source of Truth**: This document defines the authoritative system architecture.
> All subsystem documentation must be consistent with this document.
> See [docs/README.md](../README.md) for the source-of-truth hierarchy.

---

## 1. Architecture Overview

The system is a **single unified offline forensic analysis platform**. It processes Bitcoin transaction data through a multi-stage analytical pipeline and exposes results through a REST API consumed by an investigation dashboard.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OFFLINE DEPLOYMENT                           │
│                   (Docker Compose on Linux)                         │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Frontend   │    │   Backend    │    │     ML / Graph       │  │
│  │  React+Vite  │◄──►│   FastAPI    │◄──►│  Python Pipeline     │  │
│  │  Tailwind    │    │   DuckDB     │    │  NetworkX + SHAP     │  │
│  │  Cytoscape   │    │   Python     │    │  Scikit-learn/XGB    │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                              │                                      │
│                    ┌─────────▼─────────┐                           │
│                    │      DuckDB       │                           │
│                    │  (Analytical DB)  │                           │
│                    │  + Parquet files  │                           │
│                    └───────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layered Architecture

The system is organized into six logical layers. Each layer has a strict set of responsibilities, inputs, outputs, and forbidden actions.

### Layer 1: Data Layer

**Responsibility**: Ingest raw Bitcoin transaction data, validate, clean, normalize, and produce the canonical internal representation.

**Inputs**:
- Raw dataset files (CSV, JSON, Parquet format variants)
- Dataset manifest/metadata

**Outputs**:
- Canonical transaction records (see [canonical-schema.md](../data/canonical-schema.md))
- Canonical address records
- Validation error reports

**Technologies**: Python, Pandas, NumPy, DuckDB (for loading Parquet/CSV), file I/O

**Forbidden responsibilities**:
- Building the graph
- Running ML models
- Serving API responses
- Rendering UI

**Owned by**: ML Owner (data pipeline sub-task, `data_pipeline` branch)

---

### Layer 2: Graph Layer

**Responsibility**: Construct a directed transaction graph from canonical data, run graph algorithms, and produce graph-derived features for ML.

**Inputs**:
- Canonical transaction records (from Layer 1)
- Canonical address records

**Outputs**:
- In-memory NetworkX graph (DiGraph)
- Graph feature vectors per entity (see [graph-features.md](../graph/graph-features.md))
- Graph topology data for API export (see [graph-schema.md](../graph/graph-schema.md))

**Technologies**: Python, NetworkX, Pandas

**Forbidden responsibilities**:
- Data ingestion or cleaning
- ML model training/inference
- Database storage
- API routing
- UI rendering

**Owned by**: ML Owner (`graph_analysis` branch)

---

### Layer 3: ML Layer

**Responsibility**: Train and apply anomaly detection and risk scoring models. Produce structured, explainable ML results for each entity.

**Inputs**:
- Feature vectors (transaction-level + address-level + graph features)
- Trained model artifacts

**Outputs**:
- Structured ML result per entity (see [model-output-contract.md](../ml/model-output-contract.md))
  - Anomaly/risk prediction
  - Risk score (0.0–1.0)
  - Risk level (low/medium/high/critical)
  - SHAP-based explanations
  - Model provenance metadata

**Technologies**: Python, Scikit-learn, XGBoost, SHAP, Pandas, NumPy

**Forbidden responsibilities**:
- Data ingestion
- Graph construction
- Database persistence
- API routing
- UI rendering

**Owned by**: ML Owner (`ml` branch)

---

### Layer 4: Backend Layer

**Responsibility**: Orchestrate the analytical pipeline, persist data to DuckDB, serve a REST API to the frontend, and mediate all communication between the ML layer and frontend.

**Inputs**:
- Dataset upload (file via API)
- ML layer output (structured result)
- DuckDB queries

**Outputs**:
- REST API responses (see [api-specification.md](../backend/api-specification.md))
- Structured JSON responses with standardized error format

**Technologies**: Python, FastAPI, DuckDB, Pydantic

**Forbidden responsibilities**:
- ML model training or inference
- Graph construction
- Raw data cleaning
- UI rendering

**Owned by**: Backend Owner (`backend` branch)

---

### Layer 5: Frontend Layer

**Responsibility**: Provide the investigation dashboard. Consume Backend API responses and render an interactive visualization for investigators.

**Inputs**:
- REST API responses (JSON)

**Outputs**:
- Interactive investigation UI
- Cytoscape.js graph visualization
- Risk analysis views
- Explanation cards

**Technologies**: React, Vite, Tailwind CSS, Recharts, Cytoscape.js

**Forbidden responsibilities**:
- Direct database access
- ML inference
- Data ingestion
- Graph construction
- Business logic beyond display and navigation

**Owned by**: Frontend Owner (`frontend` branch)

---

### Layer 6: Storage Layer

**Responsibility**: Provide analytical query capability and durable storage for processed data, analysis results, and model outputs.

**Technologies**: DuckDB, Parquet files (read/written by DuckDB)

**Access pattern**: Backend layer only. ML layer may write Parquet; Backend reads via DuckDB.

**Forbidden access**: Frontend may never access DuckDB directly.

---

## 3. Component Communication

```
Frontend (React)
    │
    │  HTTP REST (JSON)
    │
    ▼
Backend (FastAPI)
    │
    ├──► DuckDB (SQL queries)
    │
    └──► ML Pipeline (Python function call / subprocess)
              │
              ├──► Feature Engineering (Pandas)
              │
              ├──► Graph Layer (NetworkX)
              │
              └──► Model Inference (Scikit-learn / XGBoost + SHAP)
```

**Key architectural principle**: The frontend has exactly one communication channel — the Backend REST API. The frontend never calls ML code, graph code, or DuckDB directly.

**Backend-ML communication**: The backend invokes ML pipeline functions via Python module imports (same Docker service) or as a subprocess. The communication contract is defined in [backend-ml-contract.md](../backend/backend-ml-contract.md).

---

## 4. Data Flow Summary

```
1. Investigator uploads dataset file via frontend UI
2. Frontend POSTs file to /api/datasets/upload
3. Backend validates, saves file, registers dataset in DuckDB
4. Backend triggers analysis pipeline (ML + Graph)
5. Data pipeline reads file → canonical records → DuckDB
6. Graph layer builds NetworkX graph → computes graph features
7. ML layer: feature engineering → model inference → SHAP explanations
8. Structured ML results saved to DuckDB
9. Backend API serves results to frontend
10. Frontend renders: transactions, risk scores, graph, explanations
```

See [end-to-end-data-flow.md](../integration/end-to-end-data-flow.md) for the complete field-level trace.

---

## 5. Deployment Architecture

All components run as Docker containers orchestrated by Docker Compose.

```
docker-compose.yml
    │
    ├── frontend  (port 3000 → Nginx serving Vite build)
    ├── backend   (port 8000 → FastAPI via Uvicorn)
    └── (shared volume for DuckDB file and Parquet data)
```

The ML pipeline runs **within the backend container** (Python imports), not as a separate service. This simplifies offline operation and eliminates network calls between analytical components.

See [deployment-architecture.md](./deployment-architecture.md) for full details.

---

## 6. Subsystem Boundaries (What Each Subsystem Must NOT Do)

| Subsystem | Explicitly Forbidden |
|---|---|
| Data Pipeline | ML inference, API endpoints, UI rendering, graph algorithms |
| Graph Layer | Data ingestion, ML inference, API endpoints, UI rendering |
| ML Layer | Data ingestion, graph construction, API endpoints, database queries, UI rendering |
| Backend | ML model training, raw file parsing, graph construction, UI rendering |
| Frontend | Direct DuckDB access, ML inference, graph construction, file system access |

---

## 7. Offline-First Architecture

**Hard requirement**: The system must function without internet access at runtime.

Implications:
- All ML models are trained offline and serialized to disk (`models/` directory).
- All Python packages are installed during Docker image build (no runtime pip install).
- Frontend assets are bundled during Docker image build (no CDN).
- No external API calls during analysis (no blockchain explorers, no cloud ML).
- DuckDB is embedded — no database server process required.
- All Docker images must be built before going offline, or pre-built images must be available.

See [ADR-002](../decisions/ADR-002-offline-first-architecture.md) and [offline-deployment.md](../deployment/offline-deployment.md).

---

## 8. Security Considerations

> **Note**: This is an internal forensic analysis tool deployed in a controlled environment.
> It is not designed as a public-facing web service.

- No authentication system is implemented in Phase 1. `DECISION REQUIRED` for multi-user scenarios.
- Backend API is assumed to be accessible only within the Docker network + host.
- Frontend is served by Nginx within the same Docker network.
- No external network access is made at runtime.
- Dataset files are stored locally within the Docker volume.

---

## 9. Scalability Assumptions

The system is designed for:
- Single investigator or small team usage.
- Dataset sizes: up to ~10 million transactions (DuckDB handles this efficiently).
- Single-node deployment (no clustering).

**Not designed for**:
- Multi-tenant use
- Real-time blockchain streaming
- Horizontal scaling

These are `FUTURE` considerations and must not be implemented in the current phase without an explicit ADR.

---

*Last updated: 2026-09-11 | Owner: All | Branch: main*
*References: [canonical-schema.md](../data/canonical-schema.md) | [api-specification.md](../backend/api-specification.md) | [model-output-contract.md](../ml/model-output-contract.md)*

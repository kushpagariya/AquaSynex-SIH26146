# Component Responsibility Matrix

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This is the authoritative reference for what each component is and is not responsible for.
> When in doubt about ownership, this document takes precedence.

---

## 1. Component Responsibility Matrix

| Component | Owns | Consumes | Produces | Must NOT |
|---|---|---|---|---|
| **Data Pipeline** | Ingestion, validation, cleaning, normalization, canonical record creation | Raw dataset files (CSV/JSON/Parquet) | Canonical transaction records, canonical address records, Parquet files in DuckDB | Build graph, run ML, serve API, render UI, access frontend |
| **Graph Layer** | Graph construction from canonical data, graph algorithm execution, graph feature computation | Canonical transaction records, canonical address records | NetworkX DiGraph, graph feature vectors, graph topology export (node/edge JSON) | Ingest raw data, run ML models, serve API, persist to DuckDB, render UI |
| **ML Layer** | Feature engineering (non-graph), model training, model inference, risk scoring, SHAP explainability, ML result production | Feature vectors (tabular + graph features) + trained model artifacts | Structured ML result per entity (prediction, risk score, explanation, model metadata) | Ingest raw data, build graph, serve API, persist to database, render UI |
| **Backend** | API routing, request validation, response serialization, pipeline orchestration, DuckDB queries, ML invocation, error handling, configuration | ML layer output (structured result), DuckDB (stored data), file uploads | REST API JSON responses, DuckDB records, analysis pipeline trigger | ML training/inference, graph construction, raw file parsing, UI rendering, direct frontend state management |
| **DuckDB / Storage** | Durable analytical storage of canonical records, analysis results, graph summaries, model metadata | Parquet files from data pipeline; SQL queries from backend | Query results (relations, aggregates, time-series) | Business logic, ML inference, API routing, rendering |
| **Frontend** | Investigation UI, page routing, API consumption, graph visualization (Cytoscape.js), chart rendering (Recharts), user interaction handling, client-side filtering/search | Backend REST API JSON responses | User interactions, visual investigation interface | Direct DuckDB access, ML inference, graph construction, business logic beyond display |

---

## 2. Detailed Component Responsibilities

### 2.1 Data Pipeline

**Owner**: ML Owner  
**Branch**: `data_pipeline`  
**Primary files**: `src/data/` or `pipeline/data/`

| Responsibility | Description |
|---|---|
| File ingestion | Read CSV, JSON, Parquet from configured path |
| Schema detection | Detect available columns in the dataset |
| Validation | Check required fields, types, ranges (see [data-validation.md](../data/data-validation.md)) |
| Cleaning | Handle nulls, duplicates, format inconsistencies |
| Normalization | Standardize timestamps to UTC, values to satoshis internally |
| Canonical mapping | Produce canonical records (see [canonical-schema.md](../data/canonical-schema.md)) |
| Parquet export | Write canonical records to Parquet for DuckDB consumption |
| Error reporting | Produce structured validation error reports |

---

### 2.2 Graph Layer

**Owner**: ML Owner  
**Branch**: `graph_analysis`  
**Primary files**: `src/graph/` or `pipeline/graph/`

| Responsibility | Description |
|---|---|
| Graph construction | Build directed graph: addresses as nodes, transactions as edges (see [graph-construction.md](../graph/graph-construction.md)) |
| Graph storage | Maintain in-memory NetworkX DiGraph |
| Degree computation | Compute in-degree, out-degree, weighted variants |
| PageRank | Compute PageRank scores per node |
| Connected components | Identify weakly/strongly connected components |
| Centrality metrics | Compute betweenness, closeness centrality (PLANNED) |
| Feature export | Produce graph feature DataFrame for ML consumption |
| Topology export | Produce serializable node/edge JSON for backend (see [graph-schema.md](../graph/graph-schema.md)) |
| Temporal analysis | Analyze activity patterns over time (PLANNED) |

---

### 2.3 ML Layer

**Owner**: ML Owner  
**Branch**: `ml`  
**Primary files**: `src/ml/` or `pipeline/ml/`

| Responsibility | Description |
|---|---|
| Feature engineering | Create derived features from canonical + graph data |
| Feature normalization | Scale/normalize features for model input |
| Model training | Train anomaly detection / classification models |
| Model persistence | Save/load trained models to/from disk |
| Model inference | Run predictions on new data |
| Anomaly scoring | Compute anomaly scores per entity |
| Risk scoring | Convert model output to calibrated risk score 0.0–1.0 |
| Risk level assignment | Map risk score to LOW/MEDIUM/HIGH/CRITICAL |
| SHAP explanation | Compute SHAP values and produce structured explanation |
| Result serialization | Produce ML output contract-compliant result |

---

### 2.4 Backend Layer

**Owner**: Backend Owner  
**Branch**: `backend`  
**Primary files**: `backend/`

| Responsibility | Description |
|---|---|
| API routing | Define and serve all `/api/*` routes (see [api-specification.md](../backend/api-specification.md)) |
| Request validation | Validate all incoming API requests (see [validation-rules.md](../backend/validation-rules.md)) |
| Response serialization | Format all responses per the standard schema |
| Pipeline orchestration | Trigger data pipeline → graph → ML on dataset upload/analysis |
| DuckDB integration | Execute analytical queries, store results |
| ML invocation | Call ML pipeline functions, receive structured output |
| Error handling | Catch and return structured error responses (see [error-handling.md](../backend/error-handling.md)) |
| Dataset management | Register, list, delete datasets |
| Analysis management | Trigger, track, retrieve analysis runs |
| Configuration | Load and apply environment-based configuration |

---

### 2.5 Frontend Layer

**Owner**: Frontend Owner  
**Branch**: `frontend`  
**Primary files**: `frontend/`

| Responsibility | Description |
|---|---|
| Page routing | Define and navigate investigation pages |
| API client | Abstract all backend calls (see [frontend-backend-contract.md](../frontend/frontend-backend-contract.md)) |
| Dataset management UI | Upload, select, manage datasets |
| Transaction explorer | Display, filter, search transactions |
| Address/entity explorer | Display entity risk profiles |
| Graph explorer | Render Cytoscape.js graph, handle user interactions |
| Risk visualization | Render risk scores, charts, risk level indicators |
| Explanation view | Render SHAP-derived feature contribution cards |
| Loading states | Show appropriate loading indicators during analysis |
| Error states | Display structured error messages from API |
| Client-side filtering | Filter/search displayed data without additional API calls (where appropriate) |

---

## 3. Cross-Component Communication Rules

| From | To | Mechanism | Allowed? |
|---|---|---|---|
| Frontend | Backend | HTTP REST (JSON) | ✅ Yes |
| Frontend | DuckDB | Direct SQL | ❌ No |
| Frontend | ML | Direct Python call | ❌ No |
| Frontend | Graph | Direct Python call | ❌ No |
| Backend | DuckDB | Python DuckDB client (SQL) | ✅ Yes |
| Backend | ML | Python function call / subprocess | ✅ Yes |
| Backend | Graph | Python function call / subprocess | ✅ Yes |
| ML | DuckDB | Direct write (Parquet output only) | ✅ Yes (write Parquet only) |
| ML | Backend | Python return value / file | ✅ Yes |
| Graph | ML | Python DataFrame pass | ✅ Yes |
| Graph | DuckDB | Direct SQL | ❌ No (backend mediates) |
| Data Pipeline | DuckDB | Write Parquet | ✅ Yes |
| Data Pipeline | Backend | Pipeline function return | ✅ Yes |

---

## 4. Interface Boundaries

These are the **contract boundaries** — changing them requires multi-owner review.

| Interface | Contract Document |
|---|---|
| Frontend ↔ Backend | [frontend-backend-contract.md](../frontend/frontend-backend-contract.md) + [api-specification.md](../backend/api-specification.md) |
| Backend ↔ ML | [backend-ml-contract.md](../backend/backend-ml-contract.md) + [model-output-contract.md](../ml/model-output-contract.md) |
| Data Pipeline → Graph/ML | [canonical-schema.md](../data/canonical-schema.md) + [model-input-contract.md](../ml/model-input-contract.md) |
| Graph → ML | [graph-features.md](../graph/graph-features.md) |
| Backend → DuckDB | [duckdb-schema.md](../backend/duckdb-schema.md) |
| Backend → Frontend (Graph) | [graph-schema.md](../graph/graph-schema.md) + [visualization-specification.md](../frontend/visualization-specification.md) |

---

*Last updated: 2026-09-11 | Owner: All*
*References: [system-architecture.md](./system-architecture.md)*

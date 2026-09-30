# AquaSynex: Complete Current-State Technical Context & Implementation Blueprint

---

## 1. Executive Summary & Verification Methodology

This technical context document represents the **authoritative, single source of truth** for the current state of the **AquaSynex** repository (Smart India Hackathon project ID: `SIH26146`).

This document was generated via direct inspection of the codebase, abstract syntax trees, schema definitions, model artifact binaries, configuration files, Docker orchestrations, test suites, and documentation.

### Key Grounding Rules Applied During Inspection:
1. **Codebase Over Documentation**: Where architecture markdown files describe planned designs (e.g., PostgreSQL or Polars), the active implementation (FastAPI, DuckDB, Pandas, Scikit-Learn, XGBoost, CatBoost, React 19, Cytoscape.js) is recorded as the ground truth.
2. **Zero Fabrication**: Unimplemented concepts (e.g., live RPC nodes, user authentication, PDF export) are explicitly categorized as **Missing** or **Planned**.
3. **No Heuristic Hallucination**: AI/ML components are audited down to their serialized model weights, JSON booster definitions, and TreeSHAP matrix transformations.

---

## 2. Project Identity

### 2.1 Core Mission & Problem Statement
Bitcoin transaction traffic presents law enforcement and forensic compliance investigators with significant analytical challenges:
- High pseudo-anonymity across billions of UTXO state transitions.
- Complex money laundering and obfuscation topologies (peeling chains, high-fan-in aggregations, mixing services, rapid multi-hop layering, burst dispersion).
- Lack of explainable, machine-learning-driven triage: investigators face overwhelming volumes of transaction telemetry without automated risk attribution or mathematical feature importance ranking.

**AquaSynex** solves this by delivering an end-to-end, offline, containerized investigative intelligence workstation that parses raw Bitcoin ledger transactions and network telemetry, computes 46 canonical behavioral and topological graph features, executes dual-engine supervised machine learning (XGBoost binary risk probability + CatBoost 11-class typology attribution), computes local TreeSHAP feature importance attributions, and projects interactive bipartite subgraphs in an investigative dashboard.

### 2.2 Target Users & Use Cases
- **Primary Users**: Financial crime analysts, law enforcement cybercrime units, blockchain forensic compliance officers.
- **Primary Use Case**: Triage and forensic reconstruction of suspicious Bitcoin transaction clusters, discovering money-laundering patterns, identifying suspect counterparties, and isolating high-risk transaction subgraphs.
- **Secondary Use Cases**:
  - Offline forensic auditing of historical transaction batches (e.g., seized node dumps, exchange audit records).
  - Validation of heuristic clustering rules (Multi-Input and Change heuristics) against adversarial transaction structures.
  - Typology classification: categorizing illicit funds into specific typologies (e.g., peeling chains vs. mixer-like flows).

### 2.3 Differentiation from a Standard Blockchain Explorer
| Capability | Standard Blockchain Explorer (e.g., mempool.space, Blockchain.com) | AquaSynex Forensic Workstation |
|---|---|---|
| **Primary Goal** | Raw block/transaction inspection and confirmation status | Forensic risk attribution and laundering detection |
| **Data Scope** | Single transaction / address lookup | Multi-hop bipartite graph topologies, address clusters, and telemetry |
| **Risk Scoring** | None (purely informational) | Calibrated ML risk probability $P(\text{illicit}) \in [0.0, 1.0]$ |
| **Typology Attribution**| None | 11-class ML classification (peeling chain, burst, mixer, etc.) |
| **Explainability** | None | Local TreeSHAP contribution values for top risk-driving features |
| **Deployment** | Hosted cloud service requiring internet | Fully offline, containerized, zero-cloud/zero-external-API runtime |

### 2.4 Explaining AquaSynex

#### In Technical Terms:
> "AquaSynex is an on-premises, containerized forensic analytics system for Bitcoin UTXO transaction traffic. It implements a multi-stage data pipeline using DuckDB as an embedded columnar analytical engine, extracts 46 canonical features spanning transaction metrics, historical address velocity, temporal rolling windows, network layer telemetry, and streaming bipartite graph metrics. It executes supervised machine learning inference using a 71-dimensional transformed feature space across a frozen XGBoost binary detector and an 11-class CatBoost typology classifier, producing exact additive TreeSHAP feature attributions and exporting interactive Cytoscape.js topological graphs over a React 19 single-page application."

#### In Simple Terms (For Non-Technical Judges / Teammates):
> "AquaSynex is an intelligent investigation workstation for tracking Bitcoin criminal activity. Instead of manually clicking through hundreds of Bitcoin transactions, an investigator simply uploads a transaction log file. The software automatically maps out the financial network, uses artificial intelligence to flag high-risk transactions, identifies the specific money-laundering technique being used (like a peeling chain or a mixing service), explains exactly why it flagged the transaction using mathematical evidence, and draws an interactive visual network map of all linked suspect addresses."

---

## 3. Current System Architecture

Reconstructed directly from active repository code, the system comprises six interacting layers:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT / INVESTIGATOR                                │
│                            Web Browser (Port 3000)                               │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ HTTP (JSON / Static Assets)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND REVERSE PROXY & SPA RUNNER CONTAINER                  │
│                             (aquasynex_frontend)                                 │
│  - Nginx Alpine Runner (:80 mapped to :3000)                                     │
│  - Static compiled React 19 / Vite / TailwindCSS SPA (/usr/share/nginx/html)    │
│  - Reverse Proxy: /api/* -> http://backend:8000 (300s timeout, 2048M body limit)│
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ HTTP Proxy (:8000)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND API & ENGINE CONTAINER                            │
│                             (aquasynex_backend)                                  │
│  - FastAPI REST Application (uvicorn backend.main:app, Python 3.11-slim)        │
│  - Pydantic Settings & Request/Response Validation Envelopes                     │
│  - Lifespan Manager: DuckDB connection initialization & migration runner         │
│  - Routers: /health, /datasets, /analyses, /transactions, /addresses, /graph, /alerts, /models │
│  - BackgroundTasks: Asynchronous analysis execution worker                       │
└───────────────────┬───────────────────────────────┬──────────────────────────────┘
                    │                               │
       SQL / In-Process Reads/Writes                │ Python In-Process Calls
                    │                               │
                    ▼                               ▼
┌────────────────────────────────────────┐ ┌───────────────────────────────────────┐
│        EMBEDDED COLUMNAR STORAGE       │ │          ML / FORENSIC SUBSYSTEM      │
│         (Named Volume: /app/data)      │ │           (pipeline/ml, ml/)          │
│  - DuckDB Engine (aquasynex.db)        │ │  - Ingestion, Cleaning, Normalization │
│  - RLock Thread-Safe Cursor Proxy      │ │  - 46-Feature Extraction Pipeline     │
│  - 9 Relational Tables (ACID)          │ │  - GraphFeatureExtractor & UnionFind  │
│  - Raw uploaded CSV/Parquet archives   │ │  - Preprocessor (RobustScaler + OHE)  │
│  - Dynamic Analytical Scanners         │ │  - XGBoost Binary Model (TreeSHAP)    │
│    (read_csv_auto, read_parquet)       │ │  - CatBoost 11-Class Typology Model   │
└────────────────────────────────────────┘ └───────────────────────────────────────┘
```

### Component Breakdown
1. **Frontend Presentation**: React 19, Vite, TypeScript, TailwindCSS v4, Lucide React, Cytoscape.js. Fully responsive, dark-mode forensic UI.
2. **Reverse Proxy & Delivery**: Nginx (Alpine), handles client routing fallback (`try_files $uri $uri/ /index.html`), 2GB upload streams, and proxies `/api` requests to backend.
3. **Application API Layer**: FastAPI on Uvicorn. Validates requests via Pydantic v2 schemas, manages cross-cutting request IDs, execution timing headers, and wraps responses in canonical API envelopes.
4. **Data Management & Ingestion**: `DatasetService` dynamically scans CSV, Parquet, JSON, and JSONL uploads using DuckDB's internal C++ vectorized scanner, normalizing varying field naming variations into strict canonical relational tables.
5. **Analytical Storage**: Embedded DuckDB (`data/aquasynex.db`). Thread-safe write synchronization via Python `threading.RLock`.
6. **ML Inference & Graph Topology**: `pipeline.ml.model_inference` loads serialized models (`models/`), extracts 46 features per transaction, normalizes into 71-dimensional arrays, computes inference and TreeSHAP values, and yields structured results persisted to DuckDB.

---

## 4. Complete End-to-End Data Flow

Tracing an investigation lifecycle from clean launch to result visualization:

```text
[Investigator Browser]
        │
        │ 1. POST /api/datasets/upload (Multipart CSV file + name)
        ▼
[Nginx Proxy (:80)] ──> passes stream up to 2048MB ──> [FastAPI Backend (:8000)]
                                                                │
                                                                ▼
                                                    [DatasetService.upload_dataset]
                                                                │
        ┌───────────────────────────────────────────────────────┴───────────────────────────────┐
        │ Writes raw bytes to /app/data/{dataset_id}/{filename}                                 │
        │ Registers dataset record in DuckDB 'datasets' table (status='processing')             │
        │ Creates DuckDB temporary view: CREATE VIEW temp_upload AS SELECT * FROM read_csv_auto │
        │ Normalizes timestamps, Satoshis, addresses, and network telemetry                     │
        │ Executes bulk SQL INSERTs into: transactions, transaction_inputs,                      │
        │                                 transaction_outputs, network_events, addresses        │
        │ Updates dataset record in DuckDB (status='ready', row_count, canonical_tx_count)      │
        └───────────────────────────────────────────────────────┬───────────────────────────────┘
                                                                │
[Investigator UI: Dataset Page] <── Polling GET /api/datasets/{id} returns status='ready'
        │
        │ 2. POST /api/datasets/{dataset_id}/analyses (model_id='aquasynex_xgb_binary_v1')
        ▼
[AnalysisService.trigger_analysis]
        │
        │ Inserts analysis_run record (status='pending')
        │ Dispatches _execute_analysis_run via FastAPI BackgroundTasks (Asynchronous)
        ▼
[Background Worker: _execute_analysis_run]
        │
        │ Updates analysis_run (status='running')
        │ Invokes PipelineService.run_analysis()
        ▼
[ML Subsystem: pipeline.ml.model_inference.run_analysis]
        │
        ├─ [A] Query DuckDB: Extracts transactions, inputs, outputs, network_events for dataset_id
        ├─ [B] DataValidationEngine: Checks dust thresholds, hex formats, UTXO balance conservation
        ├─ [C] DataCleaningEngine: Deduplicates, standardizes casing, imputes missing fees
        ├─ [D] DataNormalizationEngine: Normalizes epochs, satoshis, port numbers, country codes
        ├─ [E] FeatureEngineeringPipeline: Computes 40 tabular features (tx, addr, time, net, rel)
        ├─ [F] GraphFeatureExtractor & TemporalEntityClusterer: Computes 6 historical graph metrics
        │      (UnionFind multi-input clustering, component sizes, degree averages strictly t < T_tx)
        ├─ [G] Feature Merge: Merges tabular + graph features on transaction_id (46 canonical columns)
        ├─ [H] Preprocessor (preprocessor_v1.joblib):
        │      - RobustScaler on 44 numeric features
        │      - OneHotEncoder on 'net_country' and 'net_asn' -> Produces 71-dim feature vector
        ├─ [I] XGBoost (aquasynex_xgb_binary_v1.json):
        │      - Predicts continuous risk probability P(illicit) in [0.0, 1.0]
        │      - Computes TreeSHAP feature contributions (pred_contribs=True)
        ├─ [J] CatBoost (aquasynex_catboost_multiclass_v1.cbm):
        │      - Predicts 11-class typology probability distribution & multi-class label
        ├─ [K] Envelope Packaging:
        │      - Maps continuous risk to 'low', 'medium', 'high', 'critical'
        │      - Ranks top-K SHAP features with direction, importance, and readable units
        │      - Attaches graph evidence items
        └─ [L] DuckDB Bulk Transaction:
               - Validates schema conformance
               - Inserts all results into 'ml_results' table
               - Updates 'analysis_runs' (status='completed', entity_count, high_risk_count, critical_risk_count)
                                │
[Investigator UI] <─────────────┴────── Polling GET /api/analyses/{id} detects status='completed'
        │
        ├─ 3. GET /api/analyses/{id}/results  ──> Populates Alerts, Behaviors, and Transactions tables
        ├─ 4. GET /api/analyses/{id}/graph    ──> Renders Cytoscape.js network topology
        └─ 5. GET /api/addresses/{id}         ──> Renders forensic dossier, TreeSHAP chart & timeline
```

---

## 5. User / Investigator Workflow

| Step | Workflow Action | Implementation Status | Code Location & Behavior |
|---|---|---|---|
| 1 | **Upload / Select Dataset** | ✅ Implemented | `frontend/src/pages/dataset.tsx`, `backend/api/datasets.py`. Drag-and-drop CSV/Parquet upload with live status polling. |
| 2 | **Trigger Analysis** | ✅ Implemented | `frontend/src/pages/dataset.tsx`, `backend/services/analysis_service.py`. Dispatches background ML job with selected model. |
| 3 | **Monitor System Dashboard** | ✅ Implemented | `frontend/src/pages/dashboard.tsx`. Displays total volume, high-risk entity counts, risk breakdown, and temporal activity. |
| 4 | **Global Search** | ✅ Implemented | `frontend/src/components/layout/global-search.tsx`, `frontend/src/data/service.ts:search()`. Instant lookup by txid or address with deep-link navigation. |
| 5 | **Triage Alerts** | ✅ Implemented | `frontend/src/pages/alerts.tsx`. Filter alerts by severity (Critical, High, Medium, Low), typology, or date range. |
| 6 | **Inspect Transaction Detail** | ✅ Implemented | `frontend/src/pages/transaction.tsx`, `backend/api/transactions.py:get_transaction_detail()`. Full breakdown of inputs, outputs, fees, sat/byte rate, and ML prediction. |
| 7 | **Investigate Address Profile** | ✅ Implemented | `frontend/src/pages/investigation.tsx`, `backend/api/addresses.py:get_address_profile()`. Complete forensic dossier: balance history, first/last seen, counterparty counts. |
| 8 | **Inspect TreeSHAP Risk Drivers** | ✅ Implemented | `frontend/src/components/investigation/risk-factors.tsx`. Visual bar charts showing exact features increasing or decreasing risk. |
| 9 | **Interactive Graph Exploration** | ✅ Implemented | `frontend/src/pages/graph-explorer.tsx`. Full Cytoscape bipartite graph: zoom, pan, neighbor highlighting, node/edge inspection panel. |
| 10| **N-Hop Neighborhood Subgraph** | ✅ Implemented | `backend/api/graph.py:get_address_subgraph()`, `frontend/src/components/investigation/graph-viewer.tsx`. 1 to 3 hops BFS expansion around suspect address. |
| 11| **Network Telemetry Intelligence** | ✅ Implemented | `frontend/src/pages/network.tsx`. IP distribution, standard Bitcoin port (8333) adherence, ASNs, and country geography. |
| 12| **Typology Behavior Analysis** | ✅ Implemented | `frontend/src/pages/behaviors.tsx`. Clusters transactions into 11 typologies (peeling chains, mixers, bursts, fan-in/out). |
| 13| **Model Performance Insights** | ✅ Implemented | `frontend/src/pages/model.tsx`. Displays model metadata, confusion matrices, ROC/PR curves, and operating thresholds. |
| 14| **Generate / Export Dossier Report (PDF/CSV)** | ❌ Missing | No backend or frontend PDF/CSV export engine exists. Only Cytoscape JSON graph export is supported. |

---

## 6. Frontend Architecture

### 6.1 Technology Stack
- **Framework**: React 19 (`react: ^19`, `react-dom: ^19`)
- **Language**: TypeScript 5.7.3 (`tsc -b`)
- **Build Tool**: Vite 8.3.0 (`@vitejs/plugin-react`)
- **Styling**: TailwindCSS v4 (`tailwindcss: ^4.3.3`, `@tailwindcss/vite: ^4.3.3`), `clsx`, `tailwind-merge`, `class-variance-authority`
- **Routing**: React Router DOM v7 (`react-router-dom: ^7.18.3`)
- **Icons**: Lucide React (`lucide-react: ^1.16.0`)
- **Graph Visualization**: Cytoscape.js (`cytoscape: ^3.34.3`)
- **Charting**: Pure CSS/SVG bar graphs and progress indicators (no external heavy charting dependencies).
- **HTTP Client**: Native browser `fetch` wrapped in a centralized typed client (`frontend/src/api/client.ts`).

### 6.2 Application Pages
1. **Dashboard** (`/dashboard`): Global high-risk metrics, system status flags, temporal activity distribution, quick action shortcuts.
2. **Dataset Management** (`/dataset`): File drag-and-drop ingestion, field validation status, dataset switching, analysis trigger controls.
3. **Alerts Triage** (`/alerts`): Filterable alerts grid sorted by risk severity with direct investigation links.
4. **Transactions Ledger** (`/transactions`): Paginated transaction data table with sorting, value formatting (BTC/Satoshis), and risk badges.
5. **Entities Directory** (`/entities`): Discovered address entities with balances, transaction frequencies, and risk levels.
6. **Graph Explorer** (`/graph`): Full-canvas Cytoscape.js environment with search, hop expansion, filter toggles, and inspector drawers.
7. **Network Intelligence** (`/network`): Telemetry inspection (IP subnets, ASN distributions, country flags, non-standard peer ports).
8. **Behavioral Typologies** (`/behaviors`): 11-class typology classification cards, entity counts, and forensic pattern descriptions.
9. **Model Performance & Registry** (`/model`): Frozen model specs, operating threshold benchmarks ($\tau = 0.32, 0.50, 0.67$), precision/recall metrics.
10. **Investigation Dossier** (`/investigation`, `/investigation/:entityId`): Complete investigative workbench: risk gauge, TreeSHAP factor bars, N-hop graph viewer, timeline, evidence cards, and transaction list.
11. **Transaction Inspector** (`/transaction/:txid`): Deep forensic breakdown of a single transaction: inputs, outputs, script types, fee rates, and ML attributions.

### 6.3 State Management & API Integration Seam
State management is handled via React hooks (`useState`, `useEffect`, `useMemo`, `useRef`) paired with a centralized domain adapter: `frontend/src/data/service.ts`.
- **Active Context Provider**: `getActiveContext()` resolves and caches the active `datasetId` and `analysisId` across pages, ensuring seamless navigation without state loss.
- **Envelope Unwrapping**: `apiFetch<T>` in `client.ts` automatically unwraps the backend's standard `{ success, data, error, meta }` response envelope, re-raising backend errors as typed `ApiErrorClass` instances.

---

## 7. Backend Architecture

### 7.1 Framework & Core Structure
- **Framework**: FastAPI (Python 3.11).
- **Entry Point**: `backend.main:app`.
- **Server**: Uvicorn running on `0.0.0.0:8000`.
- **Lifespan Management**: `lifespan` context manager calls `init_db()` on boot (applying schema migrations) and `close_db()` on shutdown.

### 7.2 Middleware Stack
1. **CORS Middleware**: Configured via `settings.ALLOWED_ORIGINS` (supports `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`).
2. **Request Context Middleware**: Intercepts every HTTP request, assigns or propagates `X-Request-ID` (UUID4), measures elapsed time, and injects `X-Request-ID` and `X-Process-Time` response headers.

### 7.3 Exception Handling & Canonical Error Envelopes
All exceptions are mapped to a standardized JSON error envelope:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR | NOT_FOUND | MODEL_LOAD_ERROR | DATASET_ERROR | INTERNAL_ERROR",
    "message": "Human readable error description",
    "details": {}
  },
  "meta": {
    "timestamp": "2026-09-13T06:54:15Z",
    "requestId": "e7c653f2-8f1d-4d74-b52e-c5db6c24388e"
  }
}
```

### 7.4 Major API Endpoints
| HTTP Method | Route | Purpose | Internal Service Called | DB Interaction | ML Interaction |
|---|---|---|---|---|---|
| `GET` | `/api/health` | Docker & readiness healthcheck | Direct SQL | `SELECT 1` | None |
| `GET` | `/api/models` | List available ML models | `model_service.get_available_models()` | None | Reads `models/model_metadata.json` |
| `GET` | `/api/datasets` | Paginated dataset listings | `DatasetService.list_datasets()` | `SELECT FROM datasets` | None |
| `POST` | `/api/datasets/upload` | Upload & ingest CSV/Parquet | `DatasetService.upload_dataset()` | Bulk INSERT into 5 tables | None |
| `GET` | `/api/datasets/{id}` | Ingestion metadata & stats | `DatasetService.get_dataset()` | `SELECT FROM datasets` | None |
| `DELETE` | `/api/datasets/{id}` | Purge dataset & all child data | `DatasetService.delete_dataset()` | Cascading DELETE on 6 tables | None |
| `POST` | `/api/datasets/{id}/analyses`| Trigger ML analysis run | `AnalysisService.trigger_analysis()` | INSERT into `analysis_runs` | Dispatches background ML pipeline |
| `GET` | `/api/analyses/{id}` | Check analysis run status | `AnalysisService.get_analysis()` | `SELECT FROM analysis_runs` | None |
| `GET` | `/api/datasets/{id}/transactions`| Paginated transactions + risk | `TransactionService.list_transactions()`| SELECT `transactions` + `ml_results` | None |
| `GET` | `/api/transactions/{id}` | Detail: inputs, outputs, risk | `TransactionService.get_transaction()` | SELECT inputs, outputs, ML result | Reads SHAP JSON |
| `GET` | `/api/datasets/{id}/addresses`| Paginated addresses + balance | `AddressService.list_addresses()` | SELECT `addresses` + `ml_results` | None |
| `GET` | `/api/addresses/{id}` | Address profile + evidence | `AddressService.get_address()` | SELECT addresses, txs, ML result | Reads graph evidence JSON |
| `GET` | `/api/analyses/{id}/graph` | Cytoscape graph export | `GraphService.get_analysis_graph()` | SELECT addresses + input/output joins | Joins ML risk scores |
| `GET` | `/api/addresses/{id}/graph`| N-hop BFS neighborhood subgraph | `GraphService.get_address_subgraph()` | Multi-hop BFS on inputs/outputs | Subgraph risk scoring |
| `GET` | `/api/analyses/{id}/results` | Paginated ML predictions | `ResultService.list_results()` | `SELECT FROM ml_results` | None |
| `GET` | `/api/analyses/{id}/results/{entityId}` | Deep ML explanations | `ResultService.get_result()` | `SELECT FROM ml_results` | Returns TreeSHAP & feature array |

---

## 8. Database and Storage Architecture

### 8.1 Technology Choice & Rationale (ADR-001)
As formally documented in `docs/decisions/ADR-001-duckdb-selection.md`, **DuckDB** is the sole persistent analytical engine.
- **Why DuckDB**: Embedded (no external database daemon or container), columnar (vectorized aggregations across millions of financial records), zero-network latency, native C++ Parquet/CSV scanning, and ACID transactional integrity.
- **Why NOT PostgreSQL**: Eliminated during architectural design to maintain zero external dependencies, simplify container orchestration, and enable true offline operation.

### 8.2 Database File & Connection Management
- **File Location**: Configurable via `DB_PATH` (defaults to `data/aquasynex.db` locally; `/app/data/aquasynex.db` in Docker).
- **Concurrency Management**: DuckDB natively permits multiple read connections but strictly one write connection per database file. To ensure thread safety in FastAPI's asynchronous/multi-threaded environment:
  - Global connection reference managed by `backend/db/connection.py`.
  - Re-entrant thread lock (`threading.RLock`) guards all write executions and cursor allocations.
  - Generational tracking (`_connection_generation`) ensures thread-local cursors are invalidated and safely recreated whenever the database connection is cycled.

### 8.3 Relational Schema (9 Tables)
```sql
-- 1. Datasets Table
CREATE TABLE datasets (
    dataset_id          VARCHAR PRIMARY KEY,
    name                VARCHAR NOT NULL,
    file_name           VARCHAR NOT NULL,
    file_path           VARCHAR NOT NULL,
    format              VARCHAR NOT NULL,
    size_bytes          BIGINT,
    row_count           INTEGER,
    canonical_tx_count  INTEGER,
    uploaded_at         TIMESTAMPTZ NOT NULL,
    status              VARCHAR NOT NULL,
    available_fields    VARCHAR[],
    canonical_field_map JSON,
    validation_summary  JSON,
    error_message       VARCHAR
);

-- 2. Transactions Table
CREATE TABLE transactions (
    transaction_id              VARCHAR NOT NULL,
    dataset_id                  VARCHAR NOT NULL,
    block_hash                  VARCHAR,
    block_height                INTEGER,
    timestamp                   TIMESTAMPTZ,
    input_count                 INTEGER,
    output_count                INTEGER,
    total_input_value_satoshi   BIGINT,
    total_output_value_satoshi  BIGINT,
    fee_satoshi                 BIGINT,
    transaction_size_bytes      INTEGER,
    label                       VARCHAR,
    ingested_at                 TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (transaction_id, dataset_id)
);
CREATE INDEX idx_transactions_dataset ON transactions(dataset_id);
CREATE INDEX idx_transactions_timestamp ON transactions(dataset_id, timestamp);

-- 3. Transaction Inputs Table
CREATE TABLE transaction_inputs (
    input_id                VARCHAR PRIMARY KEY,
    transaction_id          VARCHAR NOT NULL,
    dataset_id              VARCHAR NOT NULL,
    input_index             INTEGER NOT NULL,
    input_address           VARCHAR,
    input_value_satoshi     BIGINT,
    sequence_number         BIGINT,
    previous_transaction_id VARCHAR,
    previous_output_index   INTEGER
);
CREATE INDEX idx_tx_inputs_address ON transaction_inputs(input_address);

-- 4. Transaction Outputs Table
CREATE TABLE transaction_outputs (
    output_id               VARCHAR PRIMARY KEY,
    transaction_id          VARCHAR NOT NULL,
    dataset_id              VARCHAR NOT NULL,
    output_index            INTEGER NOT NULL,
    output_address          VARCHAR,
    output_value_satoshi    BIGINT,
    script_type             VARCHAR,
    is_spent                BOOLEAN
);
CREATE INDEX idx_tx_outputs_address ON transaction_outputs(output_address);

-- 5. Derived Addresses Table
CREATE TABLE addresses (
    address_id                  VARCHAR NOT NULL,
    dataset_id                  VARCHAR NOT NULL,
    address_type                VARCHAR,
    first_seen_timestamp        TIMESTAMPTZ,
    last_seen_timestamp         TIMESTAMPTZ,
    total_received_satoshi      BIGINT,
    total_sent_satoshi          BIGINT,
    transaction_count           INTEGER,
    output_count                INTEGER,
    input_count                 INTEGER,
    PRIMARY KEY (address_id, dataset_id)
);
CREATE INDEX idx_addresses_dataset ON addresses(dataset_id);

-- 6. Analysis Runs Table
CREATE TABLE analysis_runs (
    analysis_id             VARCHAR PRIMARY KEY,
    dataset_id              VARCHAR NOT NULL,
    status                  VARCHAR NOT NULL,
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    model_id                VARCHAR,
    model_version           VARCHAR,
    feature_schema_version  VARCHAR,
    entity_count            INTEGER,
    high_risk_count         INTEGER,
    critical_risk_count     INTEGER,
    error_message           VARCHAR,
    config                  JSON,
    graph_summary           JSON
);
CREATE INDEX idx_analysis_dataset ON analysis_runs(dataset_id);

-- 7. ML Results & Explanations Table
CREATE TABLE ml_results (
    result_id           VARCHAR PRIMARY KEY,
    analysis_id         VARCHAR NOT NULL,
    dataset_id          VARCHAR NOT NULL,
    entity_id           VARCHAR NOT NULL,
    entity_type         VARCHAR NOT NULL,
    anomaly_score       DOUBLE NOT NULL,
    risk_score          DOUBLE NOT NULL,
    risk_level          VARCHAR NOT NULL,
    prediction_label    VARCHAR,
    confidence          DOUBLE,
    explanation_json    JSON,
    features_json       JSON,
    graph_evidence_json JSON,
    model_id            VARCHAR NOT NULL,
    model_version       VARCHAR NOT NULL,
    predicted_at        TIMESTAMPTZ NOT NULL,
    UNIQUE (analysis_id, entity_id, entity_type)
);
CREATE INDEX idx_ml_results_analysis ON ml_results(analysis_id);
CREATE INDEX idx_ml_results_entity ON ml_results(entity_id, dataset_id);
CREATE INDEX idx_ml_results_risk ON ml_results(analysis_id, risk_score);

-- 8. Network Telemetry Events Table
CREATE TABLE network_events (
    event_id            VARCHAR PRIMARY KEY,
    transaction_id      VARCHAR NOT NULL,
    dataset_id          VARCHAR NOT NULL,
    timestamp           TIMESTAMPTZ,
    timestamp_epoch_sec BIGINT,
    src_ip              VARCHAR,
    src_port            INTEGER,
    dst_ip              VARCHAR,
    dst_port            INTEGER,
    country             VARCHAR,
    asn                 BIGINT
);
CREATE INDEX idx_network_events_dataset ON network_events(dataset_id);
CREATE INDEX idx_network_events_tx ON network_events(transaction_id);

-- 9. Anomaly Alerts Table
CREATE TABLE alerts (
    alert_id            VARCHAR PRIMARY KEY,
    analysis_id         VARCHAR NOT NULL,
    dataset_id          VARCHAR NOT NULL,
    fingerprint         VARCHAR NOT NULL,
    grouping_key        VARCHAR NOT NULL,
    transaction_id      VARCHAR,
    entity_id           VARCHAR NOT NULL,
    entity_type         VARCHAR NOT NULL,
    alert_type          VARCHAR NOT NULL,
    severity            VARCHAR NOT NULL,
    priority            VARCHAR NOT NULL,
    risk_score          DOUBLE NOT NULL,
    behavior_type       VARCHAR,
    trigger_source      VARCHAR NOT NULL,
    trigger_reason      VARCHAR NOT NULL,
    status              VARCHAR NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    first_seen_at       TIMESTAMPTZ,
    last_seen_at        TIMESTAMPTZ,
    acknowledged_at     TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    assigned_to         VARCHAR,
    metadata_json       JSON,
    UNIQUE (analysis_id, fingerprint)
);
CREATE INDEX idx_alerts_analysis ON alerts(analysis_id);
CREATE INDEX idx_alerts_dataset ON alerts(dataset_id);
CREATE INDEX idx_alerts_status ON alerts(analysis_id, status);
CREATE INDEX idx_alerts_severity ON alerts(analysis_id, severity);
CREATE INDEX idx_alerts_type ON alerts(analysis_id, alert_type);
CREATE INDEX idx_alerts_entity ON alerts(entity_id);
CREATE INDEX idx_alerts_tx ON alerts(transaction_id);
```

#### Alert Subsystem Lifecycle & Evidence Traceability:
- **Status Progression**: `NEW` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `RESOLVED` (or `DISMISSED` / `ESCALATED`).
- **Severity & Priority**: Severity levels `critical`, `high`, `medium`, `low` mapped to operational priorities `P1`, `P2`, `P3`, `P4`.
- **Generation & Deduplication**: Deterministically generated post-analysis by `AlertEngine` evaluating cross-category anomaly signals (XGBoost ML risk, CatBoost typology, temporal velocity burst, graph topology, network telemetry). Grouped and deduplicated by SHA-256 fingerprint `(analysis_id, alert_type, grouping_key)` with atomic write protection under DuckDB `get_db_lock()`.
- **Query & Mutation**: Served via `backend/api/alerts.py` (`/api/alerts`, `/api/alerts/summary`, `/api/alerts/{id}/status`, `/api/alerts/{id}/priority`) backed by `AlertService`.

---

## 9. Investigation of Polars

A strict search across the repository confirms:
- `import polars` / `import pl`: **0 occurrences**.
- `polars` in `requirements.txt`, `backend/requirements.txt`, or `Dockerfile`: **0 occurrences**.

### Polars Status: Planned / Conceptual Only
While early design notes mentioned Polars for in-memory streaming transforms, the **actual implementation relies exclusively on DuckDB and Pandas**:
- **Data Ingestion & Filtering**: Executed directly inside DuckDB via C++ vectorized SQL (`read_csv_auto`, `read_parquet`, `fetchdf()`).
- **Feature Engineering & Matrix Manipulations**: Executed in-memory via **Pandas 2.2.0** and **NumPy 1.26.0**.
- **Model Training & Benchmarking**: Executed using **Pandas** and **DuckDB**.

Any claim that the current system actively runs on Polars is factually incorrect regarding the present codebase.

---

## 10. Blockchain Data Pipeline

### 10.1 Ingestion Sources
Data enters AquaSynex through two offline mechanisms:
1. **Multipart File Upload** (`POST /api/datasets/upload`): Accepts CSV, Parquet, JSON, and JSONL formats up to 2GB.
2. **Synthetic Data Generator Script** (`scripts/generate_synthetic_dataset.py`): Generates synthetic Bitcoin UTXO transaction datasets with controlled laundering scenarios.

### 10.2 Normalization & Precision Standards
To prevent floating-point rounding errors on financial values, AquaSynex enforces strict satoshi-level integer arithmetic:
- $1 \text{ BTC} = 100{,}000{,}000 \text{ Satoshis}$.
- All database columns (`total_input_value_satoshi`, `output_value_satoshi`, `fee_satoshi`) are typed as `BIGINT`.
- Bitcoin floating strings from CSVs are scaled via `CAST(ROUND(TRY_CAST(val AS DOUBLE) * 100000000) AS BIGINT)`.
- Timestamps support ISO 8601 strings and Unix epochs (seconds and milliseconds), normalized to UTC `TIMESTAMPTZ`.

---

## 11. Transaction Analysis

AquaSynex decomposes Bitcoin transactions into a bipartite relational graph:
- **Transaction Lookup**: Indexed by `(transaction_id, dataset_id)`.
- **Fund Flow Tracing**: Links input spending addresses to output destination addresses.
- **UTXO Balance Conservation**: Verified during ingestion and validation:
  $$\sum \text{Input Satoshi} = \sum \text{Output Satoshi} + \text{Fee Satoshi}$$
- **Multi-Hop Traversal**: Implemented via recursive breadth-first search (BFS) across `transaction_inputs` and `transaction_outputs`.

---

## 12. Entity & Address Clustering

### 12.1 Methodology: Chronological Streaming Union-Find
The clustering engine is implemented in `ml/graph_analysis/entity_clustering.py`:
1. **Multi-Input (Common Spending) Heuristic**: All input addresses co-spent within the same transaction are inferred to be controlled by the same behavioral entity.
2. **Change Address Heuristic**: Unspent change outputs returning to the spender are clustered with the input entity.

### 12.2 Strict Anti-Leakage Temporal Invariant
To ensure historical integrity and prevent temporal data leakage during ML feature generation:
- Transactions are processed strictly in chronological order ($t_0 \le t_1 \le \dots \le t_n$).
- For each transaction $T_i$ at time $t_i$, the entity state is inspected **strictly prior to $t_i$** ($t < t_i$).
- Cluster size (`hist_cluster_size`) and transaction frequency (`hist_cluster_tx_count`) reflect only past activity.
- The Union-Find structure is updated **after** extracting features for $T_i$.

---

## 13. Machine Learning & Artificial Intelligence System

AquaSynex implements a dual-model supervised learning and explainability pipeline:

```text
46 Canonical Features (44 Numeric + 2 Categorical)
          │
          ▼
[preprocessor_v1.joblib]
  - RobustScaler (44 numeric features)
  - OneHotEncoder (16 countries + 11 ASNs)
          │
          ▼
71-Dimensional Dense Transformed Array (X_transformed)
          │
          ├────────────────────────────────────────┬────────────────────────────────────────┐
          ▼                                        ▼                                        ▼
[aquasynex_xgb_binary_v1.json]           [aquasynex_catboost_multiclass_v1.cbm]   [TreeSHAP Contributions]
  - Algorithm: XGBoost 2.1.4               - Algorithm: CatBoost 1.2.7              - Method: pred_contribs=True
  - Target: Suspicious Probability         - Target: 11-Class Typology Attribution   - Additive Feature Attributions
  - Output: P(illicit) in [0.0, 1.0]       - Output: Multi-class probabilities      - Produces top-K risk factors
```

### 13.1 XGBoost Binary Detector
- **Model Artifact**: `models/aquasynex_xgb_binary_v1.json` (SHA256: `80994bb2...`).
- **Objective**: Detects suspicious or illicit transaction patterns.
- **Operating Thresholds (from Model Card)**:
  - Default ($\tau = 0.50$): Test F1 = 0.9700, Recall = 0.9677, Precision = 0.9724.
  - F1-Optimal ($\tau = 0.32$): Test F1 = 0.9691, Recall = 0.9871, Precision = 0.9517.
  - High-Precision ($\tau = 0.67$): Test F1 = 0.9663, Recall = 0.9499, Precision = 0.9833.

### 13.2 CatBoost Multiclass Typology Classifier
- **Model Artifact**: `models/aquasynex_catboost_multiclass_v1.cbm` (SHA256: `31a16f6d...`).
- **Objective**: Categorizes suspicious transactions into 11 typologies:
  1. `amount_anomaly`
  2. `benign_high_volume`
  3. `coordinated_activity`
  4. `high_fan_in`
  5. `high_fan_out`
  6. `mixing_like`
  7. `normal` (Index 6)
  8. `peeling_chain`
  9. `rapid_multihop`
  10. `temporal_anomaly`
  11. `transaction_burst`
- **Performance**: Test Macro-F1 = 0.9469, Multiclass Accuracy = 0.9673.

### 13.3 TreeSHAP Local Explainability
- Evaluated via native tree traversal (`booster.predict(dmat, pred_contribs=True)`).
- Produces exact additive local explanations:
  $$\text{Margin}(x) = \phi_0 + \sum_{j=1}^{71} \phi_j(x)$$
- Serialized in `ml_results.explanation_json` with normalized importance, direction (`increases_risk` / `decreases_risk`), rank, and user-friendly units.

---

## 14. Feature Engineering: 46 Canonical Features

The feature pipeline (`ml/feature_engineering/` and `ml/graph_analysis/`) extracts 46 features per transaction:

### 1. Transaction-Level Metrics (15 Features)
1. `tx_input_count`: Number of inputs.
2. `tx_output_count`: Number of outputs.
3. `tx_input_output_ratio`: Input count divided by output count.
4. `tx_total_input_sats`: Sum of all input values in Satoshis.
5. `tx_total_output_sats`: Sum of all output values in Satoshis.
6. `tx_fee_sats`: Transaction fee ($\text{Input} - \text{Output}$).
7. `tx_size_bytes`: Serialized transaction size in bytes.
8. `tx_fee_rate_sat_per_byte`: Fee in satoshis divided by transaction byte size.
9. `tx_value_balance_ratio`: Ratio of output value to input value.
10. `tx_avg_input_value_sats`: Mean input value in Satoshis.
11. `tx_max_input_value_sats`: Maximum input value in Satoshis.
12. `tx_avg_output_value_sats`: Mean output value in Satoshis.
13. `tx_max_output_value_sats`: Maximum output value in Satoshis.
14. `tx_log_total_value`: $\log_{10}(\text{Total Output Satoshis} + 1)$.
15. `tx_log_fee`: $\log_{10}(\text{Fee Satoshis} + 1)$.

### 2. Historical Address Lookback ($t < T_{tx}$, 8 Features)
16. `addr_hist_tx_count`: Historical transaction count of spending address.
17. `addr_hist_total_sent_sats`: Historical cumulative satoshis sent.
18. `addr_hist_total_received_sats`: Historical cumulative satoshis received.
19. `addr_hist_avg_tx_val_sats`: Historical mean transaction value.
20. `addr_hist_unique_counterparties`: Distinct destination addresses interacted with.
21. `addr_hist_active_days`: Days between first and last seen timestamps.
22. `addr_hist_tx_per_day`: Transaction velocity (transactions per active day).
23. `addr_reuse_count`: Number of times the address has been reused as an output.

### 3. Temporal Activity Features (7 Features)
24. `time_hour_of_day`: UTC hour of transaction execution ($0 \dots 23$).
25. `time_day_of_week`: Day of week ($0 \dots 6$).
26. `time_since_prev_global_tx_sec`: Elapsed seconds since previous transaction in dataset.
27. `time_txs_last_1m`: Global transaction frequency in preceding 60 seconds.
28. `time_txs_last_5m`: Global transaction frequency in preceding 300 seconds.
29. `time_txs_last_1h`: Global transaction frequency in preceding 3600 seconds.
30. `time_since_prev_addr_tx_sec`: Seconds since previous transaction by same address.

### 4. Network Telemetry Features (4 Numeric + 2 Categorical)
31. `net_src_port`: Source network port.
32. `net_dst_port`: Destination network port.
33. `net_is_standard_bitcoin_port`: Boolean flag indicating standard Bitcoin peer port (8333).
34. `net_hist_unique_ips_for_addr`: Historical distinct IP addresses observed for address.
35. `net_country`: 2-letter ISO country code (categorical -> 16 one-hot encoded columns).
36. `net_asn`: Autonomous System Number (categorical -> 11 one-hot encoded columns).

### 5. Relational Topological Features (4 Features)
37. `rel_fan_in`: Distinct input address count.
38. `rel_fan_out`: Distinct output address count.
39. `rel_has_change_output`: Boolean flag indicating likely change output.
40. `rel_change_value_ratio`: Ratio of change output value to total output value.

### 6. Historical Graph Topological Metrics ($t < T_{tx}$, 6 Features)
41. `hist_in_mean_neighbor_degree`: Mean degree of incoming address nodes strictly prior to $T_{tx}$.
42. `hist_out_mean_neighbor_degree`: Mean degree of outgoing address nodes strictly prior to $T_{tx}$.
43. `hist_component_size`: Weakly connected component size in bipartite graph snapshot $G_t$.
44. `hist_address_reuse_ratio`: Proportion of input addresses previously observed.
45. `hist_cluster_size`: Disjoint-set inferred entity cluster size prior to $T_{tx}$.
46. `hist_cluster_tx_count`: Entity cluster transaction count prior to $T_{tx}$.

---

## 15. Risk Scoring & Mapping Logic

Risk probability $P(\text{illicit}) \in [0.0, 1.0]$ produced by XGBoost is mapped to standardized forensic severity tiers:
- **Critical Risk**: $[0.67, 1.00]$ (High probability of structured laundering, mixing, or burst dispersion).
- **High Risk**: $[0.50, 0.67)$ (Elevated anomaly score exceeding standard operational threshold).
- **Medium Risk**: $[0.32, 0.50)$ (Borderline anomaly or high velocity requiring manual review).
- **Low Risk**: $[0.00, 0.32)$ (Standard licit transaction traffic).

---

## 16. Graph / Visual Forensics

### 16.1 Graph Representation
- **Engine**: Cytoscape.js (`cytoscape: ^3.34.3`).
- **Data Model**: Bipartite graph composed of:
  - **Address Nodes**: Rendered as ellipses; color-coded by risk severity (`#ef4444` Critical, `#f97316` High, `#f59e0b` Medium, `#22c55e` Low).
  - **Transaction Nodes**: Rendered as rounded rectangles (`#a78bfa`).
  - **Directed Edges**: Directed arrows representing value transfer, weighted by Satoshi volume with hover tooltips.

### 16.2 Interactive Capabilities
- **Neighborhood Subgraph (N-Hop Expansion)**: Querying 1 to 3 hops outward from any selected node.
- **Node Inspection**: Clicking any node opens a slide-over panel showing balance, first/last seen, transaction count, and risk factors.
- **Edge Inspection**: Displays underlying transaction IDs, timestamps, and transfer values.
- **Filtering**: Live client-side filtering by node type, minimum risk threshold, and entity search query.

---

## 17. Reporting & Evidence

### 17.1 Present Implementation
- **Cytoscape JSON Export**: Endpoints `/api/analyses/{id}/graph` and `/api/addresses/{id}/graph` return complete node and edge topologies conforming to `docs/graph/graph-schema.md`.
- **UI Evidence Cards**: `frontend/src/components/investigation/evidence-panel.tsx` visualizes graph-derived evidence (cluster size, component size, fan-in/out degrees, and address reuse ratios).

### 17.2 Missing / Planned
- No PDF case dossier generator.
- No CSV batch export of forensic findings.
- No cryptographic audit signing of investigation exports.

---

## 18. Authentication & Security Audit

### 18.1 Current Authentication State: Unauthenticated (Public API)
- **Authentication Mechanism**: None.
- **User Models / Roles**: None.
- **Tokens / API Keys**: None.
- **Evaluation**: The current system operates as a single-analyst local/internal workstation. All `/api/*` routes are completely open.

### 18.2 Security Strengths
- **Parameterized SQL Queries**: All dynamic DuckDB queries in `backend/db/queries/` use parameterized arguments (`?` placeholders), preventing SQL injection.
- **Path Traversal Guards**: Filenames are sanitized via `Path(filename).name`, rejecting `..` and quotes. `dataset_id` values are validated against strict regex (`^[a-zA-Z0-9_-]+$`).
- **File Upload Limits**: Enforces a strict 2GB limit (`MAX_UPLOAD_SIZE_BYTES = 2_147_483_648`), enforced in both Nginx (`client_max_body_size 2048M`) and Python stream chunk readers.
- **Stack Trace Suppression**: Global FastAPI exception handlers intercept raw errors, returning structured error codes and logging stack traces internally rather than exposing them to clients.

### 18.3 Identified Vulnerabilities & Technical Debt
1. **Unrestricted API Access**: Any network entity reaching port 8000 (or port 3000 via proxy) can upload files, trigger analyses, or delete datasets.
2. **Missing Rate Limiting**: No rate limiting on `/api/datasets/upload` or `/api/datasets/{id}/analyses`.
3. **In-Memory Resource Exhaustion**: Uploading an extremely large dataset with millions of transactions could exhaust container memory during Pandas feature matrix construction.

---

## 19. Docker & Container Architecture

### 19.1 Container Composition
The runtime orchestrates two Docker containers via `docker-compose.yml`:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: aquasynex_backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DB_PATH=/app/data/aquasynex.db
      - DATA_DIR=/app/data
      - MODELS_DIR=/app/models
      - PYTHONUNBUFFERED=1
    volumes:
      - aquasynex_data:/app/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
      interval: 30s
      timeout: 30s
      retries: 5
      start_period: 30s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: aquasynex_frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy

volumes:
  aquasynex_data:
    name: aquasynex_data
```

### 19.2 Container Details
- **Backend Container (`aquasynex_backend`)**:
  - Base Image: `python:3.11-slim`.
  - OS Dependencies: `curl` (for healthchecks), `libgomp1` (required for OpenMP multithreading in XGBoost and CatBoost).
  - Mounts: Named volume `aquasynex_data` mapped to `/app/data`.
  - Healthcheck: Polls `http://localhost:8000/api/health`.
- **Frontend Container (`aquasynex_frontend`)**:
  - Multi-stage build:
    - Stage 1 (`builder`): `node:20-alpine`, installs `pnpm@12.3.4`, compiles production bundle via `pnpm run build`.
    - Stage 2 (`runner`): `nginx:alpine`, copies compiled `/app/dist` to `/usr/share/nginx/html`, configures reverse proxy.
  - Startup Dependency: Waits for `backend` to pass health checks before serving traffic.

### 19.3 Data Persistence Lifecycle
| Docker Command | Effect on DuckDB (`aquasynex.db`) & Uploaded Files |
|---|---|
| `docker compose stop` | Containers pause. **Data is 100% preserved.** |
| `docker compose start`| Containers resume. **Data is 100% preserved.** |
| `docker compose down` | Containers and network are destroyed; named volume `aquasynex_data` remains intact. **Data is 100% preserved.** |
| `docker compose up -d`| New containers re-attach to `aquasynex_data`. **Existing database state is retained.** |
| `docker compose down -v` | Containers, network, **and named volume are completely destroyed**. **Database resets to empty state.** |

---

## 20. Nginx / Reverse Proxy Architecture

The frontend Nginx configuration (`frontend/nginx.conf`) handles reverse proxying:
```text
Client (Browser)
      │
      ├─ HTTP GET /                  ──> Serves compiled React index.html
      ├─ HTTP GET /assets/*          ──> Serves compiled JS/CSS static bundles
      ├─ HTTP GET /investigation/*   ──> try_files falls back to /index.html (SPA Routing)
      │
      └─ HTTP ANY /api/*             ──> Proxy Pass to http://backend:8000
                                          - client_max_body_size: 2048M
                                          - proxy_read_timeout: 300s (supports long ML runs)
                                          - forwards Host, X-Real-IP, X-Forwarded-For
```

---

## 21. Testing Architecture

AquaSynex maintains a unified test suite rooted in `tests/`:

```text
tests/
├── conftest.py             # Pytest fixtures: DuckDB isolation, FastAPI TestClient, ML sample paths
├── fixtures/               # Sample CSV and deterministic Parquet fixtures
├── api/                    # REST endpoint boundaries (Health, Datasets, Analyses, Transactions, Addresses, Graph, Results)
├── integration/            # Multi-step investigator user journeys, contract checks, Vite proxy tests
└── ml/                     # ML pipeline, feature extraction, UnionFind clustering, TreeSHAP, model loading
```

### Execution Commands:
- **Run Complete Test Suite**:
  ```bash
  pytest tests/ -v
  ```
- **Run Only ML Tests**:
  ```bash
  pytest tests/ml/ -v
  ```
- **Run Only API Tests**:
  ```bash
  pytest tests/api/ -v
  ```
- **Run Integration Regression Tests**:
  ```bash
  pytest tests/integration/ -v
  ```
- **Run Docker E2E Verification**:
  ```bash
  python scripts/test_docker_e2e.py
  ```

---

## 22. External Dependencies

| Dependency | Scope | Mandatory? | Credentials Required? | Fallback if Unavailable |
|---|---|---|---|---|
| **Python 3.11** | Backend Runtime | Yes | No | None (Application will not run) |
| **DuckDB (0.10.x - 1.2.x)**| Analytical Database | Yes | No | None (System halts with `DatabaseUnavailableError`) |
| **XGBoost (2.1.4)** | ML Binary Classifier | Yes | No | System halts with `ModelLoadError` |
| **CatBoost (1.2.7)** | ML Typology Classifier | Yes | No | System halts with `ModelLoadError` |
| **Scikit-Learn / Joblib** | Preprocessor Pipeline | Yes | No | System halts with `ModelLoadError` |
| **Node 20 / Pnpm** | Frontend Build Stage | Yes (build only) | No | Required only during container image compilation |
| **Live Blockchain APIs** | External Integrations | **No (Zero dependency)** | No | System operates 100% offline from local files |
| **Cloud Services** | Infrastructure | **No (Zero dependency)** | No | Operates entirely on local hardware / Docker |

---

## 23. Environment Variables

| Variable | Purpose | Used By | Required? | Default Value / Format | Secret? |
|---|---|---|---|---|---|
| `DB_PATH` | Path to persistent DuckDB database file | Backend (`config.py`) | No | `data/aquasynex.db` (local) or `/app/data/aquasynex.db` (Docker) | No |
| `DATA_DIR` | Path to dataset file storage root | Backend (`config.py`) | No | `data` (local) or `/app/data` (Docker) | No |
| `MODELS_DIR` | Directory containing frozen model artifacts | Backend (`config.py`) | No | `models` (local) or `/app/models` (Docker) | No |
| `ALLOWED_ORIGINS`| CORS permitted client origins | Backend (`config.py`) | No | `["http://localhost:3000", "http://127.0.0.1:3000"]` | No |
| `MAX_UPLOAD_SIZE_BYTES` | Maximum upload file size in bytes | Backend (`config.py`) | No | `2147483648` (2 GB) | No |
| `LOG_LEVEL` | Application logging verbosity | Backend (`config.py`) | No | `INFO` | No |
| `DEFAULT_MODEL_ID`| Model identifier used if unspecified | Backend (`config.py`) | No | `aquasynex_xgb_binary_v1` | No |
| `VITE_API_BASE_URL`| Custom backend base URL override | Frontend (`client.ts`) | No | `/api` | No |

---

## 24. Complete Annotated Repository Tree

```text
AquaSynex-SIH26146/
├── .dockerignore                     # Docker build exclusion rules (root context)
├── .env.example                      # Reference environment variable template
├── .gitignore                        # Git ignore patterns (virtualenvs, DuckDB binaries, node_modules)
├── README.md                         # Quick-start instructions, architecture diagram, port mappings
├── docker-compose.yml                # Multi-container orchestrator (backend + frontend + named volume)
├── requirements.txt                  # Root Python dependencies manifest (fastapi, duckdb, xgboost, catboost)
│
├── backend/                          # FastAPI Backend Application Root
│   ├── Dockerfile                    # Production Python 3.11-slim container definition
│   ├── config.py                     # Pydantic BaseSettings and runtime directory resolution
│   ├── dependencies.py               # FastAPI dependency injection providers (db, services)
│   ├── main.py                       # FastAPI entrypoint, lifespan manager, CORS, routers, exception handlers
│   ├── requirements.txt              # Backend-specific Python requirements
│   ├── api/                          # REST API endpoint route handlers
│   │   ├── addresses.py              # Address profiles, listings, balances, risk filters
│   │   ├── analyses.py               # Analysis dispatch, status polling, run summaries
│   │   ├── datasets.py               # Dataset multipart upload, validation, metadata, deletion
│   │   ├── graph.py                  # Cytoscape graph export and N-hop neighborhood subgraphs
│   │   ├── health.py                 # System healthcheck endpoint for Docker readiness checks
│   │   ├── models.py                 # Available model registry discovery
│   │   ├── results.py                # ML prediction listings and TreeSHAP entity explanations
│   │   └── transactions.py           # Paginated transactions, filtering, and deep inspection
│   ├── db/                           # Database access layer
│   │   ├── connection.py             # DuckDB connection factory, thread lock, generational tracking
│   │   ├── migrations.py             # Idempotent DDL migration statements for 8 DuckDB tables
│   │   └── queries/                  # Parameterized SQL query modules (datasets, txs, addrs, results, analyses)
│   ├── schemas/                      # Pydantic validation models (request/response DTOs)
│   ├── services/                     # Business logic layer
│   │   ├── address_service.py        # Address aggregations and profiling
│   │   ├── analysis_service.py       # Asynchronous background analysis run orchestration
│   │   ├── dataset_service.py        # Upload processing, DuckDB scanning, table normalization
│   │   ├── graph_service.py          # Cytoscape JSON graph formatting and BFS subgraphs
│   │   ├── model_service.py          # Model availability checking and metadata reading
│   │   ├── pipeline_service.py       # ML contract boundary adapter and DuckDB persistence
│   │   ├── result_service.py         # ML result retrieval and entity SHAP extraction
│   │   └── transaction_service.py    # Transaction queries and detail cross-referencing
│   └── utils/                        # Logging, custom exception classes, pagination helpers, converters
│
├── data/                             # Persistent runtime data directory (mounted to volume in Docker)
│   ├── aquasynex.db                  # Local DuckDB database file
│   ├── sample/                       # Synthetic test benchmark data (Parquet, CSV)
│   └── sample_v2/                    # Hardened v2 synthetic development benchmark
│
├── datasets/                         # Showcase transaction CSVs for testing and demonstration
│   ├── showcase_burst_network.csv    # High-velocity transaction burst demonstration
│   ├── showcase_peeling_mixing.csv   # Peeling chain and mixing topology demonstration
│   ├── showcase_typology_mix.csv     # Multi-typology mix dataset
│   └── test_smoke_50.csv             # 50-transaction smoke test fixture
│
├── frontend/                         # React 19 / Vite Investigative Analyst SPA
│   ├── Dockerfile                    # Multi-stage build (Node 20 builder -> Nginx Alpine runner)
│   ├── nginx.conf                    # Nginx reverse proxy configuration, SPA fallback, upload limits
│   ├── package.json                  # Frontend dependencies (react 19, cytoscape, tailwindcss v4)
│   ├── vite.config.ts                # Vite config with path aliases and dev proxy
│   └── src/
│       ├── App.tsx                   # Route definitions (11 pages)
│       ├── main.tsx                  # React entry point
│       ├── api/                      # Typed backend API client (addresses, analyses, datasets, graph, etc.)
│       ├── components/               # Reusable UI widgets, panels, badges, data tables
│       │   ├── investigation/        # Dossier components (graph-viewer, timeline, evidence-panel, risk-factors)
│       │   └── layout/               # App layout, responsive sidebar, global search modal
│       ├── data/
│       │   ├── service.ts            # Centralized domain integration seam connecting UI to API
│       │   └── types.ts              # TypeScript domain types (Investigation, Entity, Transaction, Alert)
│       └── pages/                    # 11 forensic workbench views (Dashboard, Graph, Investigation, etc.)
│
├── ml/                               # Standalone Machine Learning Subsystem
│   ├── data_pipeline/                # Ingestion, validation, cleaning, and canonical normalization engines
│   ├── feature_engineering/          # 40-feature extraction pipeline (tx, addr, temporal, network, relational)
│   ├── graph_analysis/               # Graph feature extractor, NetworkX builder, UnionFind clustering
│   ├── modeling_dataset/             # 10k synthetic benchmark dataset builder
│   └── modeling_experimentation/     # Training scripts, ablation audits, frozen model specs
│
├── models/                           # Serialized Production ML Artifacts
│   ├── aquasynex_xgb_binary_v1.json  # Frozen XGBoost binary risk model (1.04 MB)
│   ├── aquasynex_catboost_multiclass_v1.cbm # Frozen CatBoost 11-class typology model (2.18 MB)
│   ├── preprocessor_v1.joblib        # Scikit-Learn RobustScaler + OneHotEncoder pipeline
│   └── model_metadata.json           # Model card: SHA-256 hashes, thresholds, feature manifest
│
├── pipeline/                         # Production Integration Seam
│   └── ml/
│       └── model_inference.py        # End-to-end inference orchestrator called by backend
│
├── scripts/                          # Utility & Verification Scripts
│   ├── generate_synthetic_dataset.py # Comprehensive synthetic Bitcoin dataset generator
│   ├── load_dataset_to_duckdb.py     # CLI loader for bulk database seeding
│   ├── test_docker_e2e.py            # Automated 9-step integration verification script for Docker
│   └── validate_synthetic_dataset.py # Integrity auditor for synthetic datasets
│
└── tests/                            # Unified Test Suite (api, integration, ml, fixtures)
```

---

## 25. Current Implementation Status Matrix

| Component | Status | Verification Evidence | Notes |
|---|---|---|---|
| **Frontend SPA** | ✅ Implemented | `frontend/src/` (11 active pages, React 19, TypeScript) | Complete analyst dashboard; no broken navigation. |
| **Backend REST API** | ✅ Implemented | `backend/main.py`, `backend/api/` (8 routers) | Full CRUD, async background tasks, error envelopes. |
| **Embedded DuckDB** | ✅ Implemented | `backend/db/connection.py`, `migrations.py` | 8 relational tables, indexed, thread-safe write locks. |
| **Data Ingestion** | ✅ Implemented | `backend/services/dataset_service.py` | Scans CSV, Parquet, JSON, JSONL via vectorized engine. |
| **Polars Engine** | ❌ Missing | 0 occurrences in codebase or requirements | Code uses DuckDB + Pandas. Planned only. |
| **Supervised ML** | ✅ Implemented | `models/` (XGBoost + CatBoost + Preprocessor) | Real frozen binary model weights and tree structures. |
| **TreeSHAP Explanations**| ✅ Implemented | `pipeline/ml/model_inference.py:497` | Native TreeSHAP attribution ranking per transaction. |
| **Risk Scoring** | ✅ Implemented | `pipeline/ml/model_inference.py:116` | Continuous $[0, 1]$ mapped to 4 severity categories. |
| **Graph / Subgraphs** | ✅ Implemented | `backend/services/graph_service.py`, Cytoscape.js | Full network export and N-hop BFS neighborhood trees. |
| **Entity Clustering** | ✅ Implemented | `ml/graph_analysis/entity_clustering.py` | Multi-input & change heuristics via Disjoint-Set. |
| **Authentication & RBAC**| ❌ Missing | No auth routers, middleware, or user tables | Public local access only. |
| **Docker Deployment** | ✅ Implemented | `docker-compose.yml`, Dockerfiles, Nginx proxy | Fully verified container runtime with data persistence. |
| **Automated Testing** | ✅ Implemented | `tests/` (30+ test modules across api, integration, ml)| Comprehensive automated test coverage. |
| **PDF / CSV Report Export**| ❌ Missing | No PDF or report generation endpoints | Only Cytoscape JSON export currently exists. |

---

## 26. Actual vs. Planned Comparison

### Actually Implemented (Verified by Code):
- FastAPI backend with 8 modular routers and Pydantic v2 schemas.
- Embedded DuckDB database with 8 relational tables and generational thread cursor management.
- Dynamic analytical scanning of raw CSV and Parquet uploads into normalized tables.
- 46-feature extraction pipeline merging transaction, historical address, temporal, network, and relational metrics.
- Disjoint-Set Union-Find entity clustering enforcing zero temporal leakage.
- Production XGBoost binary classifier producing risk probabilities.
- Production CatBoost 11-class multiclass classifier attributing illicit typologies.
- Exact additive TreeSHAP explainability ranking risk-driving features.
- Cytoscape.js interactive bipartite graph visualizer with N-hop BFS expansion.
- Full React 19 single-page application with 11 forensic views and dark-mode styling.
- Multi-container Docker deployment with Nginx reverse proxy and DuckDB volume persistence.

### Planned / Conceptual (Not Implemented in Current Code):
- **Polars Dataframes**: Described in architectural notes; actual implementation uses DuckDB SQL and Pandas.
- **PostgreSQL Database**: Mentioned in early architectural drafts; rejected by ADR-001 in favor of DuckDB.
- **Live Bitcoin Node Integration**: No RPC connection to `bitcoind` or live mempool WebSocket listeners.
- **User Authentication / RBAC**: No JWT tokens, passwords, sessions, or user permission models.
- **PDF / Dossier Report Generator**: No report compilation engine to download case files or PDFs.

---

## 27. Architectural Inconsistencies & Corrections

1. **Documentation Claims PostgreSQL vs. Implementation Uses DuckDB**:
   - *Inconsistency*: Early architecture documents reference PostgreSQL schemas.
   - *Reality*: ADR-001 accepted DuckDB as the sole database. No PostgreSQL code or drivers exist.
   - *Impact*: Low (DuckDB is better suited for local analytical workloads). Documentation needs updating.
2. **Architecture Mentions Polars vs. Implementation Uses Pandas**:
   - *Inconsistency*: Concept documents cite Polars for high-throughput streaming feature extraction.
   - *Reality*: Polars is not installed. All transforms run in DuckDB and Pandas.
   - *Correction*: Either introduce Polars into `ml/` or formally document Pandas + DuckDB as the accepted baseline.
3. **Hardcoded Benchmark Disclaimer vs. Real-World Ledger Claims**:
   - *Inconsistency*: Marketing summaries may imply real-world Bitcoin criminal tracking.
   - *Reality*: Model card metadata explicitly clarifies that all models were trained and benchmarked on hardened synthetic development datasets (`v2.0.0`).

---

## 28. Current End-to-End Execution Guide

AquaSynex is fully operational out-of-the-box using Docker.

### Clean-Machine Execution:
```bash
# 1. Clone repository
git clone https://github.com/kushpagariya/AquaSynex-SIH26146.git
cd AquaSynex-SIH26146

# 2. Build and launch containers
docker compose up --build -d

# 3. Verify health status
curl http://localhost:8000/api/health
# Expected: {"success":true,"data":{"status":"healthy","databaseStatus":"connected",...}}

# 4. Access Analyst Dashboard
# Open http://localhost:3000 in your browser
```

### Investigation Execution Flow:
1. Navigate to **Dataset** (`http://localhost:3000/dataset`).
2. Upload `datasets/showcase_typology_mix.csv`.
3. Wait for status to transition to **Ready**.
4. Click **Run Analysis** (using model `aquasynex_xgb_binary_v1`).
5. Once complete, navigate to **Dashboard**, **Alerts**, or **Graph Explorer** to analyze the results.

---

## 29. Failure Modes & Behavioral Handlers

| Failure Scenario | Current System Behavior | Handling & Remediation |
|---|---|---|
| **Database File Locked** | `duckdb.connect()` blocks or raises exception. Handled by connection proxy with `DatabaseUnavailableError`. | FastAPI returns HTTP 503; thread locks prevent corruption. |
| **Invalid / Corrupt Upload**| DuckDB `read_csv_auto` fails. Partial records are rolled back. | Dataset status updated to `error`; HTTP 400 returned with details. |
| **Missing Network Telemetry**| ML pipeline detects missing `network_events` table required by 46-feature schema. | Raises `InvalidFeaturesError`; analysis status marked `failed`. |
| **Backend Container Down** | Nginx reverse proxy cannot connect to `http://backend:8000`. | Nginx returns HTTP 502 Bad Gateway; UI displays network error toast. |
| **Upload Exceeds 2GB** | Rejected by Nginx (`client_max_body_size 2048M`) or Python stream reader. | Returns HTTP 413 File Too Large before exhausting server memory. |

---

## 30. Performance Considerations

1. **DuckDB Write Concurrency**: Because DuckDB allows only one active write transaction per process, the backend synchronizes writes through a Python `threading.RLock`. While excellent for single-analyst workloads, high-concurrency multi-user writes would experience lock contention.
2. **In-Memory Feature Engineering**: The feature pipeline loads the dataset into Pandas memory. For datasets up to 100,000 transactions this completes in seconds, but datasets with tens of millions of rows would require out-of-core chunking.
3. **TreeSHAP Computational Overhead**: TreeSHAP calculation runs with $O(TLD^2)$ complexity (trees $\times$ leaves $\times$ depth$^2$). For large transaction sets, calculating TreeSHAP for all records can take several seconds; the config allows limiting top entities.
4. **Cytoscape DOM Rendering**: Rendering graphs with $>1{,}000$ active nodes in SVG/Canvas can degrade client browser frame rates. The backend defaults graph queries to `max_nodes=500`.

---

## 31. Logical Team Ownership Split

- **AI / ML Engineering**:
  - `ml/` (Data pipeline, feature engineering, graph analysis, model experimentation).
  - `models/` (Model artifacts, metadata, training benchmarks).
  - `pipeline/ml/model_inference.py` (Inference execution boundary).
- **Backend & Analytical Data Engineering**:
  - `backend/` (FastAPI routers, services, Pydantic schemas).
  - `backend/db/` (DuckDB connection, migrations, SQL query modules).
- **Frontend Engineering**:
  - `frontend/src/` (React 19 pages, UI components, Cytoscape graph viewer).
  - `frontend/src/data/service.ts` (API client adaptation).
- **DevOps & Infrastructure**:
  - `docker-compose.yml`, Dockerfiles, `frontend/nginx.conf`.
  - Deployment scripts and CI/CD testing pipelines.

---

## 32. Recommended Next Steps

### Critical (Near-Term Priority)
1. **Implement PDF / Dossier Export**: Add an endpoint (`/api/analyses/{id}/export/pdf`) using ReportLab or WeasyPrint to generate court-admissible forensic evidence reports.
2. **Network Telemetry Auto-Imputation**: When a raw Bitcoin CSV lacks network IP/port columns, automatically impute default neutral peer telemetry rather than raising `InvalidFeaturesError`.

### Important (Usability Enhancements)
3. **Client-Side Graph Export**: Add high-resolution PNG and Cytoscape JSON download buttons directly to `frontend/src/pages/graph-explorer.tsx`.
4. **Batch Comparison View**: Enable side-by-side comparison of two analysis runs on different datasets.

### Enhancements (Future Exploration)
5. **Polars Integration**: Migrate in-memory feature engineering from Pandas to Polars for higher throughput on large datasets.
6. **Authentication & Multi-Tenancy**: Introduce OAuth2 / JWT authentication with role-based case separation.

---

## 33. Final Architecture Summary

### A. Technical Architecture Summary
AquaSynex is an on-premises Bitcoin transaction forensic intelligence workstation built on FastAPI and React 19, orchestrated via Docker Compose with an Nginx reverse proxy. Data ingestion leverages DuckDB's vectorized analytical engine to parse and normalize transaction records into an 8-table relational schema. An integrated forensic ML pipeline computes 46 canonical features across transaction metrics, historical address velocity, temporal windows, network telemetry, and Union-Find graph clustering. Supervised risk scoring and 11-class typology attribution are executed via frozen XGBoost and CatBoost models with native TreeSHAP local explainability. Results, forensic evidence, and bipartite graph topologies are persisted in DuckDB and rendered via Cytoscape.js.

### B. Simple Architecture Summary
AquaSynex is an automated investigation workstation for detecting Bitcoin crime. An analyst uploads a transaction log file, and the software automatically scans every transaction, links related suspect addresses using financial heuristics, calculates a risk score using artificial intelligence, identifies the specific money laundering technique (such as a peeling chain or mixer), explains its reasoning using clear visual charts, and displays an interactive visual network map of all linked wallets.

### C. ASCII Architecture Diagram
```text
                            ┌───────────────────────────────────┐
                            │    INVESTIGATOR WEB BROWSER       │
                            │   React 19 SPA (Port 3000)        │
                            └─────────────────┬─────────────────┘
                                              │ HTTP Requests
                                              ▼
                            ┌───────────────────────────────────┐
                            │    NGINX REVERSE PROXY CONTAINER  │
                            │   - Serves static compiled SPA    │
                            │   - Proxies /api/* to :8000       │
                            │   - Enforces 2GB upload limit     │
                            └─────────────────┬─────────────────┘
                                              │ Proxy (:8000)
                                              ▼
                            ┌───────────────────────────────────┐
                            │    FASTAPI BACKEND API ENGINE     │
                            │   - Routers, Lifespan, Pydantic   │
                            │   - Async Background Worker       │
                            └────────┬─────────────────┬────────┘
                                     │                 │
            Parameterized SQL Writes │                 │ In-Process Orchestration
                                     ▼                 ▼
          ┌──────────────────────────────────┐ ┌──────────────────────────────────┐
          │     EMBEDDED DUCKDB DATABASE     │ │       ML FORENSIC SUBSYSTEM      │
          │   - 8 Relational Tables (ACID)   │ │  - 46-Feature Extraction         │
          │   - RLock Thread-Safe Cursors    │ │  - Union-Find Entity Clustering  │
          │   - Named Volume: /app/data      │ │  - RobustScaler + OneHotEncoder  │
          │   - Ingestion Scanning Engines   │ │  - XGBoost Binary Model (SHAP)   │
          └──────────────────────────────────┘ │  - CatBoost 11-Class Typology    │
                                               └──────────────────────────────────┘
```

---

## 34. Final Investigation Process Flow

```text
User uploads CSV/Parquet dataset via Web UI
                    ↓
Nginx validates body size (<= 2048MB) and streams to FastAPI
                    ↓
DatasetService writes file to disk and runs DuckDB vectorized scanner
                    ↓
Normalized records inserted into transactions, inputs, outputs, network_events, addresses
                    ↓
User selects model and clicks "Run Analysis"
                    ↓
FastAPI dispatches background execution worker
                    ↓
Pipeline extracts 40 tabular features + 6 historical graph topological metrics
                    ↓
Preprocessor transforms 46 canonical features into 71-dimensional vector
                    ↓
XGBoost predicts continuous risk score P(illicit) + CatBoost attributes typology
                    ↓
TreeSHAP computes exact local additive feature importance attributions
                    ↓
Results, explanations, and graph evidence persisted into DuckDB ml_results table
                    ↓
Analysis status marked "completed"
                    ↓
Frontend polls completion and updates Dashboard, Alerts, Typologies, and Cytoscape Graph
```

---

## 35. Machine-Readable Project Context

```text
PROJECT: AquaSynex (SIH26146)
PURPOSE: AI-Powered Monitoring & Forensic Risk Analysis of Bitcoin Transaction Traffic
TARGET USER: Law Enforcement Investigators, Financial Crime Analysts, Compliance Officers
FRONTEND: React 19, TypeScript 5.7, Vite 8.3, TailwindCSS v4, Cytoscape.js 3.34
BACKEND: FastAPI 0.110, Uvicorn, Pydantic v2, Python 3.11
DATABASE: DuckDB (Embedded columnar store, 8 tables, thread-safe RLock execution)
DATA PROCESSING: DuckDB C++ Vectorized Scanner + Pandas 2.2.0 + NumPy 1.26.0
BLOCKCHAIN DATA SOURCE: Offline File Upload (CSV, Parquet, JSON, JSONL); Zero Cloud/External API Dependencies
ML MODELS:
  - Binary Risk Detector: XGBoost 2.1.4 (models/aquasynex_xgb_binary_v1.json)
  - Typology Classifier: CatBoost 1.2.7 (models/aquasynex_catboost_multiclass_v1.cbm, 11 classes)
  - Preprocessor: Scikit-Learn 1.5.3 (models/preprocessor_v1.joblib, 46 -> 71 dimensions)
  - Explainability: Exact Additive TreeSHAP (pred_contribs=True)
GRAPH ENGINE: Cytoscape.js (Bipartite transaction/address graphs, N-hop BFS neighborhood subgraphs)
AUTHENTICATION: None (Open local API workstation)
DOCKER: 2 Containers (aquasynex_frontend, aquasynex_backend), Named Volume (aquasynex_data)
REVERSE PROXY: Nginx Alpine (SPA routing, /api proxy to backend:8000, 2048M body limit)
TESTING: Pytest (tests/api, tests/integration, tests/ml, scripts/test_docker_e2e.py)

CORE FLOW:
Dataset Upload -> DuckDB Normalization -> Async Trigger -> 46 Feature Extraction -> 
UnionFind Clustering -> XGBoost + CatBoost + TreeSHAP -> DuckDB Persistence -> Cytoscape Viz

IMPLEMENTED:
  - Full React 19 analyst dashboard across 11 functional views.
  - Asynchronous background ML analysis engine.
  - Frozen supervised models with verifiable SHA256 checksums and real weights.
  - Exact TreeSHAP feature attribution ranking.
  - Interactive Cytoscape.js bipartite graph exploration.
  - Multi-container Docker deployment with persistent named volumes.

PARTIAL:
  - Network telemetry auto-imputation (fails if network_events table is empty).

PLANNED / MISSING:
  - Polars engine (concept only; Pandas and DuckDB used in reality).
  - PostgreSQL database (concept only; DuckDB used in reality).
  - Live Bitcoin node RPC / mempool WebSocket listeners.
  - User authentication and role-based access controls.
  - PDF and CSV forensic dossier export generators.

KNOWN ISSUES:
  - DuckDB writes restricted to single-writer lock; multi-user concurrent writes will block.
  - Very large graphs (>1000 nodes) can cause DOM lag in client browser canvas.

NEXT PRIORITIES:
  1. Add PDF case evidence report generator.
  2. Implement network telemetry auto-imputation for raw Bitcoin CSVs lacking IP columns.
  3. Add client-side PNG/JSON graph download controls.
```

---

> `This document describes the repository's current state as inspected at the time of generation.`

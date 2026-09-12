# AquaSynex – Frontend ↔ Backend Integration Test Suite

Dedicated integration test suite for **AquaSynex – SIH26146** (AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic).

---

## 1. Purpose

This test suite validates the integration boundary between the React frontend client and the FastAPI backend:

```text
Browser / Frontend Client (TypeScript)
            ↓
       Vite Dev Server
            ↓
        /api Proxy
            ↓
     FastAPI Backend (Python)
            ↓
     DuckDB Analytical Store
```

The suite tests real communication, real multipart file uploads, real DuckDB table persistence, real API routing, and verified error propagation without mock data or fake heuristics.

---

## 2. Architecture & Invariants

1. **Strict Test Database Isolation**:
   - Tests run in an isolated temporary directory created via `tempfile.mkdtemp`.
   - The developer's primary database at `data/aquasynex.db` is **never** accessed, modified, or corrupted during test runs.
   - DuckDB connections are explicitly closed during teardown to avoid Windows file locks.

2. **Deterministic Bitcoin Dataset**:
   - Uses `tests/fixtures/sample_bitcoin_dataset.csv`, a deterministic fixture containing 5 valid Bitcoin transactions with real address formats (P2PKH, P2SH, SegWit), satoshi-level precision, timestamps, and connected graph topology.

3. **Controlled ML-Unavailable Boundary**:
   - Because ML and Graph analytics subsystems (`pipeline.ml.model_inference`) are under active development, the analysis flow asserts that the backend handles the absence of the ML module cleanly:
     ```text
     POST /api/datasets/{id}/analyses → Status: 202 Accepted (Pending)
             ↓
     Background execution encounters ModelLoadError
             ↓
     Controlled terminal state: status='failed', errorMessage populated
             ↓
     GET /api/analyses/{id}/results → [] (Zero fabricated predictions)
     ```
   - Tests ensure the backend does **not** crash, does **not** hang, and does **not** generate fake predictions.

4. **Zero Mock Data Enforcement**:
   - Static AST and regex inspection ensures `frontend/src/` contains zero application-level mock data or fake risk scores.

5. **Contract Verification**:
   - Validates all TypeScript client calls (`frontend/src/api/*`) against the FastAPI OpenAPI schema (`app.openapi()`).

---

## 3. Prerequisites & Setup

- Python 3.11 with project dependencies installed in `backend/.venv`:
  - `fastapi`, `duckdb`, `pytest`, `httpx`, `pydantic-settings`
- Node.js & npm (for frontend build verification)

---

## 4. Execution Commands

### Run Only the Integration Test Suite
```bash
backend\.venv\Scripts\python -m pytest tests/ -v
```

### Run Full Test Suite (Backend Unit + Integration Tests)
```bash
backend\.venv\Scripts\python -m pytest -v
```

### Run Specific Test Modules
```bash
# Health API
backend\.venv\Scripts\python -m pytest tests/api/test_health.py -v

# Dataset Upload & Persistence Flow
backend\.venv\Scripts\python -m pytest tests/integration/test_dataset_upload_flow.py -v

# Full Investigator User Journey
backend\.venv\Scripts\python -m pytest tests/integration/test_full_user_journey.py -v

# Frontend ↔ Backend Contract Check
backend\.venv\Scripts\python -m pytest tests/integration/test_frontend_backend_contract.py -v
```

### Start Servers Locally
```bash
# 1. Start FastAPI Backend
backend\.venv\Scripts\python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 2. Start Frontend Dev Server (in separate terminal)
cd frontend
npm run dev
```

---

## 5. Test Structure

```text
tests/
├── README.md                                # Suite documentation & execution guide
├── conftest.py                              # Pytest fixtures: isolated DuckDB, TestClient, dataset setup
├── fixtures/
│   └── sample_bitcoin_dataset.csv           # 5-transaction connected Bitcoin fixture
├── api/
│   ├── test_health.py                       # GET /api/health boundary verification
│   ├── test_datasets.py                     # Dataset upload, list, detail, delete endpoints
│   ├── test_analyses.py                     # Analysis dispatch and status polling endpoints
│   ├── test_transactions.py                 # Transaction list, filter, pagination, detail endpoints
│   ├── test_addresses.py                    # Address list, balance aggregation, profile endpoints
│   ├── test_graph.py                        # Cytoscape graph export and subgraph endpoints
│   └── test_results.py                      # ML results listing and entity explanation endpoints
└── integration/
    ├── test_dataset_upload_flow.py          # Multipart upload -> file storage -> DuckDB persistence
    ├── test_analysis_flow.py                # Analysis trigger -> background runner -> controlled failure
    ├── test_transaction_flow.py             # Transactions query, sorting, and detail cross-referencing
    ├── test_address_flow.py                 # Address derivation, multi-transaction balances
    ├── test_frontend_backend_contract.py    # TypeScript client routes vs FastAPI OpenAPI routes
    ├── test_vite_proxy.py                   # Vite proxy config and FastAPI CORS headers
    ├── test_error_handling.py               # Domain error codes, 404s, and validation envelopes
    ├── test_data_consistency.py             # Cross-layer ID and count consistency
    ├── test_no_mock_data.py                 # Automated scan verifying zero mock data in frontend/src
    └── test_full_user_journey.py            # Complete 14-step investigator user workflow
```

---

## 6. Integration Test Summary Matrix

Actual results from test execution:

```text
Frontend ↔ Backend Integration
--------------------------------
Health                        PASS
Dataset Upload                PASS
Dataset Listing               PASS
Dataset Detail                PASS
Analysis Creation             PASS
Analysis Failure Handling     PASS
Transactions                  PASS
Addresses                     PASS
Graph Contract                PASS
Results Contract              PASS
Error Handling                PASS
Vite Proxy                    PASS (Config & CORS: PASS, Live Probe: SKIPPED when dev server offline)
Data Consistency              PASS
Mock Data Check               PASS
Full User Journey             PASS
```

**Test Execution Stats**:
- Total Integration Tests: **37**
- Passed: **36**
- Skipped: **1** (`test_live_vite_proxy_if_running` skipped when Vite dev server is offline during CI)
- Failed: **0**

---

## 7. Known Limitations & Future Transitions

- **ML Pipeline**: The ML inference engine (`pipeline.ml.model_inference`) is currently under development. The suite expects and verifies controlled failure (`status='failed'`) without fake predictions. When ML is integrated, `tests/integration/test_analysis_flow.py` and `tests/integration/test_full_user_journey.py` should be updated to assert `status='completed'` and non-empty `ml_results`.
- **Graph Analytics**: Neighborhood subgraphs are built directly from ingested transaction records and DuckDB tables. Advanced graph centrality algorithms will be incorporated once the Graph subsystem is finalized.

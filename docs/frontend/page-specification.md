# Page Specification

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Dashboard Page (`/`)

**Purpose**: Investigation workspace entry point. Shows system status, available datasets, and recent analyses.

**Content**:
- System health indicator (green/red — from `/api/health`)
- Recent datasets list
- Quick-start: Upload dataset button
- Recent analysis summaries

**States**: Loading, no datasets yet (onboarding prompt), datasets available

---

## 2. Datasets Page (`/datasets`)

**Purpose**: Manage uploaded datasets.

**Content**:
- Upload zone (drag-and-drop or file picker)
- Dataset list table: name, format, status, row count, uploaded date
- Per-dataset actions: Analyze, View Transactions, View Addresses, Delete
- Dataset status badge (uploaded / processing / ready / error)

**API calls**: `GET /api/datasets`, `POST /api/datasets/upload`, `DELETE /api/datasets/{id}`

---

## 3. Analysis Page (`/datasets/:datasetId/analysis`)

**Purpose**: Trigger and monitor analysis run.

**Content**:
- Dataset summary header
- Analysis configuration (model selection, max entities)
- "Start Analysis" button
- Analysis status tracker (pending → running → completed/failed)
- On completion: navigation links to Transactions, Addresses, Graph
- On failure: error message display

**API calls**: `POST /api/datasets/{id}/analyses`, `GET /api/analyses/{analysisId}` (polling)

---

## 4. Transactions Page (`/datasets/:datasetId/transactions`)

**Purpose**: Browse and filter all transactions in a dataset.

**Content**:
- Filter bar: risk level, timestamp range, value range
- Sortable table: transaction ID, timestamp, value, input/output counts, risk score, risk level
- Risk level badge per row
- Row click → transaction detail modal or detail page

**API calls**: `GET /api/datasets/{id}/transactions` (paginated, filtered)

---

## 5. Addresses Page (`/datasets/:datasetId/addresses`)

**Purpose**: Browse and filter all addresses/entities.

**Content**:
- Filter bar: risk level, min risk score
- Sortable table: address (truncated), transaction count, total received, total sent, risk score, risk level
- Row click → Address Detail Page

**API calls**: `GET /api/datasets/{id}/addresses` (paginated, filtered)

---

## 6. Address Detail Page (`/addresses/:addressId`)

**Purpose**: Full investigation profile for a single address.

**Content**:
- Address header (full address, copy button, risk badge)
- Behavioral summary: tx count, total received/sent, first/last seen, active days
- Risk score gauge or bar
- Top SHAP explanations (explanation cards)
- Graph evidence list
- Graph view: neighborhood subgraph (Cytoscape.js, 2-hop)
- Recent transactions table

**API calls**: `GET /api/addresses/{addressId}`, `GET /api/addresses/{addressId}/graph`

---

## 7. Graph Page (`/datasets/:datasetId/graph`)

**Purpose**: Full transaction graph visualization for exploration.

**Content**:
- Cytoscape.js graph (full analysis graph, filtered to high-risk nodes by default)
- Controls: filter by risk level, max nodes slider, layout selector
- Click node → show address detail panel (side panel)
- Click edge → show transaction detail panel

**API calls**: `GET /api/analyses/{analysisId}/graph`

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Frontend Owner*

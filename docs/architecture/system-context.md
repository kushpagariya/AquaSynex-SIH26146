# System Context

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## 1. System Context Overview

This document defines the boundary of the SIH26146 system — what is inside it, what is outside it, and who/what interacts with it.

```
┌─────────────────────────────────────────────────────────────┐
│                  EXTERNAL ACTORS                            │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │   Investigator   │    │  Bitcoin Dataset Files       │  │
│  │   (Human User)   │    │  (CSV / JSON / Parquet)      │  │
│  └────────┬─────────┘    └─────────────┬────────────────┘  │
│           │                            │                   │
└───────────┼────────────────────────────┼───────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                     SIH26146 SYSTEM BOUNDARY                      │
│                                                                   │
│   ┌──────────────────────────────────────────────────────────┐    │
│   │            Investigation Dashboard (Frontend)            │    │
│   └──────────────────────────────────────────────────────────┘    │
│                          ▲         │                               │
│                          │  REST   │                               │
│                          │  API    │                               │
│   ┌──────────────────────┴─────────▼──────────────────────────┐   │
│   │                Backend (FastAPI + DuckDB)                  │   │
│   └─────────────────────────────────┬──────────────────────────┘   │
│                                     │                              │
│   ┌─────────────────────────────────▼──────────────────────────┐   │
│   │        ML / Graph / Data Pipeline (Python)                 │   │
│   └────────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
            │
            (No external runtime calls — OFFLINE system)
```

---

## 2. External Actors

### 2.1 Investigator (Primary User)

**Description**: A law-enforcement analyst, financial intelligence officer, or forensic researcher using the system to investigate Bitcoin transaction patterns.

**Goals**:
- Understand transaction patterns in a dataset.
- Identify suspicious addresses/entities.
- Explore the transaction graph interactively.
- Understand why the system flagged an entity as high-risk.
- Generate evidence to support an investigation.

**Interactions with the system**:
- Uploads Bitcoin transaction dataset via the web UI.
- Triggers analysis runs.
- Queries transactions, addresses, entities.
- Explores the graph visualization.
- Reviews risk scores and SHAP explanations.
- Applies filters to narrow investigation scope.
- Exports findings (FUTURE).

**Does NOT**:
- Interact directly with the database.
- Call ML model code directly.
- Modify the graph.

---

### 2.2 Bitcoin Dataset Files (External Data Source)

**Description**: Structured dataset files containing Bitcoin transaction data. These are not live blockchain API calls — they are pre-collected static datasets.

**Expected formats**:
- CSV (primary expected format)
- JSON
- Parquet (preferred for large datasets)

**Provenance**: Offline-collected datasets from blockchain explorers, research datasets (e.g., Elliptic dataset), or extracted data.

**Interaction**: Files are uploaded by the investigator via the web UI or placed in a configured data directory.

**What the system expects from these files**: See [data-sources.md](../data/data-sources.md).

---

## 3. What Is Inside the System Boundary

| Component | Technology | Description |
|---|---|---|
| Investigation Dashboard | React + Vite + Tailwind | Web-based UI for investigators |
| Graph Visualization | Cytoscape.js | Interactive transaction graph |
| Chart Visualization | Recharts | Risk and behavioral charts |
| Backend API | FastAPI | REST API orchestrating all services |
| Data Pipeline | Python + Pandas | Ingestion, cleaning, normalization |
| Graph Engine | NetworkX | Graph construction and analysis |
| ML Pipeline | Scikit-learn + XGBoost + SHAP | Anomaly detection and explainability |
| Analytical Storage | DuckDB + Parquet | Storing and querying processed data |

---

## 4. What Is Outside the System Boundary

| External System | Status | Notes |
|---|---|---|
| Bitcoin Blockchain (live) | **OUT** | Only pre-collected datasets are used |
| Blockchain explorer APIs | **OUT** | No runtime calls to Blockstream, Blockchain.info, etc. |
| Cloud ML APIs (OpenAI, etc.) | **OUT** | All models are local and offline |
| Cloud databases | **OUT** | DuckDB is embedded and local |
| Authentication providers | **OUT** | No OAuth, LDAP, or external auth |
| External graph databases | **OUT** | NetworkX is used, not Neo4j or ArangoDB |
| Internet (at runtime) | **OUT** | System is fully offline at runtime |

---

## 5. Constraints from Context

| Constraint | Source | Implication |
|---|---|---|
| Offline runtime | Deployment requirement | No external API calls in any service |
| Linux deployment target | Docker + Ubuntu | All code must be Linux-compatible |
| Single-node deployment | Demonstration context | No distributed systems complexity |
| Static dataset | No live blockchain API | Results are bounded to the uploaded dataset |
| Forensic investigation use case | SIH problem statement | Explainability and evidence traceability are critical |

---

## 6. Future Context Changes (FUTURE / DECISION REQUIRED)

The following context changes are not currently in scope but may be considered in future phases:

- **Live blockchain integration**: `FUTURE` – Would require a streaming data pipeline and remove the offline constraint.
- **Multi-user authentication**: `FUTURE` / `DECISION REQUIRED` – If multiple investigators use the system simultaneously, authentication and session isolation will be needed.
- **Federated datasets**: `FUTURE` – Combining multiple dataset sources into a unified graph.
- **Report export**: `FUTURE` – Generating PDF/JSON investigation reports.

None of these should be implemented in the current phase without an explicit ADR.

---

*Last updated: 2026-09-11 | Owner: All*
*References: [system-architecture.md](./system-architecture.md) | [deployment-architecture.md](./deployment-architecture.md)*

# AquaSynex (SIH26146)

**AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

AquaSynex is an end-to-end investigation and transaction risk attribution platform for Bitcoin transaction traffic. It integrates synthetic/live Bitcoin data pipelines, bipartite graph topology analysis, supervised Machine Learning (XGBoost binary detection, CatBoost multi-class typology attribution, and TreeSHAP explainability), an embedded DuckDB analytical store, and a React investigative analyst dashboard.

---

## Docker Quick Start

A teammate can clone this repository, ensure Docker & Docker Compose are installed, and run:

```bash
docker compose up --build
```

### Endpoints
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health) (or proxied via [http://localhost:3000/api/health](http://localhost:3000/api/health))

### Stop Containers
To stop the running application without losing data:
```bash
docker compose down
```

### Reset Persistent Runtime Data
Runtime DuckDB database state and uploaded datasets are persisted in the Docker named volume `aquasynex_data`. To perform a complete reset:
```bash
docker compose down -v
```

> **Network & Cloud Independence**: The first build requires internet access to download base container images (`python:3.11-slim`, `node:20-alpine`, `nginx:alpine`) and package dependencies. Once built, the container runtime operates completely locally without external APIs or cloud dependencies.

---

## Architecture Overview

```
                        ┌───────────────────────────────┐
                        │   Web Browser (Investigator)  │
                        └───────────────┬───────────────┘
                                        │
                         HTTP :3000     │
                                        ▼
                        ┌───────────────────────────────┐
                        │     Frontend (Nginx + SPA)    │
                        │   - Reverse proxies /api/     │
                        │   - Serves React/Vite build   │
                        └───────────────┬───────────────┘
                                        │
                         HTTP :8000     │  (internal docker network)
                                        ▼
                        ┌───────────────────────────────┐
                        │    Backend (FastAPI Engine)   │
                        │   - Dataset ingestion & ETL   │
                        │   - ML inference orchestration│
                        │   - Cytoscape graph analytics │
                        └───────┬───────────────┬───────┘
                                │               │
                                ▼               ▼
                 ┌──────────────────────┐ ┌──────────────────────┐
                 │     DuckDB Store     │ │  ML Model Artifacts  │
                 │ (Named Docker Volume)│ │   (Local /models)    │
                 │  - aquasynex.db      │ │ - XGBoost Binary     │
                 │  - raw uploads       │ │ - CatBoost Typology  │
                 └──────────────────────┘ └──────────────────────┘
```

---

## Key Capabilities
1. **Dataset Ingestion**: High-throughput parsing of SIH Bitcoin transaction CSV/Parquet datasets into canonical DuckDB schema with automated address and network event extraction.
2. **Feature Engineering**: 40 canonical features spanning transaction metrics, historical address velocity, temporal rolling windows, and relational graph degrees.
3. **ML Risk Attribution**: Pre-trained XGBoost and CatBoost models delivering transaction-level risk scores, multi-class typology classification, and TreeSHAP feature explanations.
4. **Interactive Graph Visualizer**: Bipartite address-to-transaction subgraph exploration and cluster analysis built for Cytoscape.js.
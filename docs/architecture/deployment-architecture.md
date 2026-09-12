# Deployment Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## 1. Deployment Overview

The system is deployed as a **multi-container Docker Compose application** on a single Linux host. It is designed for **fully offline operation** — no internet connectivity is required after Docker images are built and data is loaded.

```
Host Machine (Linux / Ubuntu ≥ 22.04)
│
└── docker-compose.yml
      │
      ├── [frontend]   Nginx serving Vite-built React app   → port 3000
      │
      ├── [backend]    Uvicorn serving FastAPI application  → port 8000
      │                  └── ML pipeline (Python, in-process)
      │                  └── DuckDB (embedded, file-based)
      │
      └── [shared volume]
              ├── /data/           Dataset files (Parquet, CSV, JSON)
              ├── /db/             DuckDB database files
              └── /models/         Trained ML model artifacts
```

---

## 2. Service Architecture

### 2.1 Frontend Service

| Property | Value |
|---|---|
| Container name | `aquasynex-frontend` |
| Base image | `node:20-alpine` (build), `nginx:alpine` (runtime) |
| Build context | `./frontend` |
| Exposed port | `3000` (host) → `80` (container) |
| Runtime dependencies | None (all assets bundled at build time) |
| Internet required | No (CDN resources bundled during build) |

**Build stages**:
1. `node:20-alpine` — install dependencies and run `npm run build`
2. `nginx:alpine` — serve the `dist/` directory

**Nginx configuration**: Must proxy API requests (`/api/`) to the backend service.

---

### 2.2 Backend Service

| Property | Value |
|---|---|
| Container name | `aquasynex-backend` |
| Base image | `python:3.11-slim` |
| Build context | `./backend` |
| Exposed port | `8000` (host) → `8000` (container) |
| Framework | FastAPI + Uvicorn |
| ML runtime | Python in-process (same container) |
| Database | DuckDB (embedded, file-based) |
| Internet required | No |

**Volume mounts**:
- `/data` — Dataset files read/written by the data pipeline and DuckDB
- `/db` — DuckDB `.db` files
- `/models` — Trained model artifacts (`.pkl`, `.json`, `.joblib`)

---

### 2.3 No Separate ML Service

The ML pipeline runs **within the backend container** as Python module imports. This design decision:
- Eliminates inter-service network calls for ML inference.
- Simplifies offline deployment (no ML service health-check needed).
- Reduces Docker resource overhead.

If the ML pipeline becomes computationally intensive enough to justify isolation, this can be revisited via an ADR. See [Q-002 in architecture-decisions.md](./architecture-decisions.md).

---

## 3. Volume Strategy

| Volume Name | Mount Path (Container) | Purpose |
|---|---|---|
| `aquasynex-data` | `/app/data` | Dataset files uploaded by investigator |
| `aquasynex-db` | `/app/db` | DuckDB database files |
| `aquasynex-models` | `/app/models` | Trained ML model artifacts |

All volumes are **local bind mounts** (not cloud volumes) to support offline operation.

---

## 4. Network Configuration

```
docker-compose network: aquasynex-net (bridge)
    │
    ├── frontend ──► backend (via http://backend:8000)
    └── backend  (internal only — not exposed directly except through frontend proxy)
```

The frontend Nginx proxy handles all `/api/*` requests and forwards them to the backend service. This means:
- The investigator's browser only talks to port 3000.
- The backend port 8000 is accessible on the host for development but should be restricted in production.

---

## 5. Environment Configuration

Environment variables are passed via `.env` files or Docker Compose `environment` sections.

See [environment-variables.md](../deployment/environment-variables.md) for the full variable reference.

**Key variables**:
| Variable | Service | Example |
|---|---|---|
| `BACKEND_HOST` | Frontend (Nginx proxy) | `backend` |
| `BACKEND_PORT` | Frontend (Nginx proxy) | `8000` |
| `DATA_DIR` | Backend | `/app/data` |
| `DB_PATH` | Backend | `/app/db/aquasynex.db` |
| `MODELS_DIR` | Backend | `/app/models` |
| `LOG_LEVEL` | Backend | `INFO` |

---

## 6. Docker Image Build Strategy

All images must be buildable offline after initial dependency download.

### Frontend Build

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci             # Requires internet during build
COPY . .
RUN npm run build      # Produces dist/

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Backend Build

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt   # Requires internet during build
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 7. Offline Operation Requirements

At runtime, the following must be available locally:
- Docker images (pre-built or loaded from tar archive)
- Dataset files (placed in the data volume before analysis)
- Trained ML model artifacts (placed in `/models` before inference)

The following must **not** be required at runtime:
- PyPI packages (installed during image build)
- npm packages (bundled during image build)
- External blockchain APIs
- Cloud storage services

See [offline-deployment.md](../deployment/offline-deployment.md) for the offline deployment procedure.

---

## 8. Health Checks

| Service | Health Check | Endpoint |
|---|---|---|
| Backend | HTTP GET `/api/health` returns 200 | `/api/health` |
| Frontend | Nginx serves static file | `/` |

Docker Compose `healthcheck` should be configured for the backend. Frontend depends on backend being healthy before accepting investigation actions.

---

## 9. Development vs Production

| Aspect | Development | Production |
|---|---|---|
| Frontend server | Vite dev server (`npm run dev`) | Nginx serving built bundle |
| Backend reloading | Uvicorn `--reload` | Uvicorn without reload |
| CORS | Permissive (all origins) | Restrict to frontend origin |
| Log level | `DEBUG` | `INFO` |
| Backend port exposure | Exposed on host | Optionally restricted |
| Volume mounts | Local directory mounts | Named volumes |

---

*Last updated: 2026-09-11 | Owner: Backend + ML + Frontend*
*References: [docker-architecture.md](../deployment/docker-architecture.md) | [offline-deployment.md](../deployment/offline-deployment.md)*

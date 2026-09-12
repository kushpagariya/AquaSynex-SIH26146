# Backend Subsystem

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Backend agent entry point.** Read [backend-agent-guide.md](./backend-agent-guide.md) next.

---

## Subsystem Overview

The backend is the stable API boundary between the investigation dashboard and all analytical services. It:

- Serves a REST API to the frontend
- Orchestrates the data pipeline, graph construction, and ML inference
- Persists all structured data to DuckDB
- Enforces API contracts and error handling

## Owner

**Backend Owner** — owns all code in `backend/`.

## Branch

`backend`

## Key Contracts

| Document | Purpose |
|---|---|
| [api-specification.md](./api-specification.md) | **All API routes and schemas** |
| [request-response-schemas.md](./request-response-schemas.md) | Exact request/response shapes |
| [error-handling.md](./error-handling.md) | Error codes and formats |
| [duckdb-schema.md](./duckdb-schema.md) | Database tables |
| [backend-ml-contract.md](./backend-ml-contract.md) | How backend calls ML pipeline |

## Status

| Component | Status |
|---|---|
| FastAPI application skeleton | `PLANNED` |
| Dataset management API | `PLANNED` |
| Analysis orchestration API | `PLANNED` |
| Transaction query API | `PLANNED` |
| Address/entity API | `PLANNED` |
| Graph API | `PLANNED` |
| Risk/ML results API | `PLANNED` |
| DuckDB integration | `PLANNED` |
| ML pipeline invocation | `PLANNED` |

---

*Last updated: 2026-09-11 | Owner: Backend Owner*

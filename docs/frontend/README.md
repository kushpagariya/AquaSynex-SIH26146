# Frontend Subsystem

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Frontend agent entry point.** Read [frontend-agent-guide.md](./frontend-agent-guide.md) next.

---

## Subsystem Overview

The frontend provides the investigation dashboard — a React web application that investigators use to upload datasets, trigger analysis, explore transactions, visualize the transaction graph, and review risk explanations.

## Owner

**Frontend Owner** — owns all code in `frontend/`.

## Branch

`frontend`

## Technology Stack

| Library | Purpose |
|---|---|
| React + Vite | Application framework |
| Tailwind CSS | Styling |
| Recharts | Statistical charts |
| Cytoscape.js | Graph visualization |

## Key Contracts (Read Before Coding)

| Document | Purpose |
|---|---|
| [frontend-backend-contract.md](./frontend-backend-contract.md) | What APIs exist and what they return |
| [api-specification.md](../backend/api-specification.md) | Full API documentation |
| [error-handling.md](../backend/error-handling.md) | All error codes and formats |
| [graph-schema.md](../graph/graph-schema.md) | Graph data format for Cytoscape.js |
| [visualization-specification.md](./visualization-specification.md) | Chart and graph specs |

## Status

| Component | Status |
|---|---|
| Vite + React application | `PLANNED` |
| Tailwind CSS configuration | `PLANNED` |
| API client layer | `PLANNED` |
| Dataset management page | `PLANNED` |
| Analysis dashboard | `PLANNED` |
| Transaction explorer | `PLANNED` |
| Address/entity explorer | `PLANNED` |
| Graph explorer (Cytoscape.js) | `PLANNED` |
| Risk visualization (Recharts) | `PLANNED` |
| Explanation cards | `PLANNED` |

---

*Last updated: 2026-09-11 | Owner: Frontend Owner*

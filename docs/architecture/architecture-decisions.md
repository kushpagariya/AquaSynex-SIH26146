# Architecture Decisions Summary

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This document is a summary index of all Architecture Decision Records (ADRs).
> Each ADR is the authoritative record for its specific decision.
> See `docs/decisions/` for full ADR documents.

---

## ADR Index

| ADR | Title | Status | Decision |
|---|---|---|---|
| [ADR-001](../decisions/ADR-001-duckdb-selection.md) | Database: DuckDB vs PostgreSQL | **Accepted** | Use DuckDB for analytical storage |
| [ADR-002](../decisions/ADR-002-offline-first-architecture.md) | Offline-First Architecture | **Accepted** | System must operate fully offline at runtime |
| [ADR-003](../decisions/ADR-003-three-subsystem-ownership.md) | Three-Subsystem Ownership Model | **Accepted** | ML / Backend / Frontend as independent subsystems |
| [ADR-004](../decisions/ADR-004-contract-first-integration.md) | Contract-First Integration | **Accepted** | Shared contracts defined before implementation |

---

## Open Architectural Questions

The following questions are **unresolved** and require team decisions before implementation proceeds:

| ID | Question | Impact | Priority |
|---|---|---|---|
| Q-001 | Authentication model: none / simple token / session | Backend + Frontend | Medium |
| Q-002 | ML pipeline execution: in-process vs subprocess | Backend + ML | High |
| Q-003 | Risk score formula: normalized probability vs composite weighted score | ML + Backend + Frontend | High |
| Q-004 | Model retraining strategy: retrain per dataset vs global model | ML | High |
| Q-005 | Graph persistence strategy: in-memory only vs DuckDB graph summary | Graph + Backend | Medium |
| Q-006 | Frontend state management library: React Context vs Zustand vs Redux | Frontend | Low |
| Q-007 | Wallet clustering: implement heuristic clustering or address-only analysis | ML + Graph | Medium |

---

## Architecture Principles (Non-Negotiable)

The following principles apply to all architectural decisions and cannot be overridden without an explicit ADR:

1. **Offline-First**: No runtime dependency on the internet.
2. **Contract-First**: Shared interfaces defined in documentation before code.
3. **Single Responsibility**: Each layer has clearly bounded responsibilities.
4. **Technology Stability**: No new technologies beyond the approved stack without an ADR.
5. **Traceability**: Every ML prediction must be traceable to a dataset, feature schema, model, and model version.
6. **Investigation-Driven**: UI and API design must serve the investigator's workflow.
7. **No Premature Generalization**: Implement what is needed; don't architect for imaginary future scale.

---

*Last updated: 2026-09-11 | Owner: All*
*References: [docs/decisions/](../decisions/README.md)*

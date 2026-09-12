# ADR Index

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## Architecture Decision Records

| ADR | Title | Status | Date |
|---|---|---|---|
| [ADR-001](./ADR-001-duckdb-selection.md) | Use DuckDB as Analytical Database | ACCEPTED | 2026-09-11 |
| [ADR-002](./ADR-002-offline-first-architecture.md) | Offline-First Architecture | ACCEPTED | 2026-09-11 |
| [ADR-003](./ADR-003-networkx-graph-library.md) | Use NetworkX for Graph Construction | ACCEPTED | 2026-09-11 |
| [ADR-004](./ADR-004-satoshi-value-representation.md) | Satoshi as Internal Value Representation | ACCEPTED | 2026-09-11 |
| [ADR-005](./ADR-005-shap-explainability.md) | Use SHAP for ML Explainability | ACCEPTED | 2026-09-11 |

## Open Questions (Pending ADRs)

| Q-ID | Question | Impact |
|---|---|---|
| Q-001 | Authentication mechanism? | Security |
| Q-002 | HTTP polling vs WebSocket for analysis status? | Frontend + Backend |
| Q-003 | State management: Zustand + React Query or alternatives? | Frontend |
| Q-004 | Edge aggregation strategy in graph (raw vs aggregated)? | Graph + Frontend |
| Q-005 | Risk score formula: composite vs direct ML probability? | ML |
| Q-006 | Size threshold for graph approximation algorithms? | ML + Graph |
| Q-007 | DuckDB vs Parquet threshold for large datasets? | Backend + Data |

---

*Last updated: 2026-09-11 | Owner: All*

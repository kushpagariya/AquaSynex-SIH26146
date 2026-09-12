# State Management

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `DECISION REQUIRED` (Q-006)

---

## Global Application State

| State Item | Type | Description |
|---|---|---|
| `selectedDatasetId` | `string \| null` | Currently active dataset |
| `selectedAnalysisId` | `string \| null` | Currently active analysis run |
| `currentFilters` | `FilterState` | Active filter state for tables |

## Server State (API data)

Managed with React Query or SWR (TBD):
- Dataset list
- Analysis status (auto-invalidated when analysis completes)
- Transaction list (paginated + filtered)
- Address list (paginated + filtered)
- ML results (paginated)
- Graph data

## Decision Required

`DECISION REQUIRED`: Zustand + React Query vs React Context + SWR vs Redux Toolkit Query.

Recommendation (pending approval): **Zustand** (lightweight, no boilerplate) + **React Query** (server state, caching, polling support).

---

*Last updated: 2026-09-11 | Status: DECISION REQUIRED | Owner: Frontend Owner*

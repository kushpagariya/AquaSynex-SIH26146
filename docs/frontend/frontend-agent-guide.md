# Frontend Agent Guide

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This document is for the AI agent responsible for the Frontend subsystem.

---

## 1. Mandatory Reading

1. [`docs/README.md`](../README.md)
2. This document
3. [`docs/frontend/frontend-backend-contract.md`](./frontend-backend-contract.md) — **Your primary contract**
4. [`docs/backend/api-specification.md`](../backend/api-specification.md)
5. [`docs/backend/request-response-schemas.md`](../backend/request-response-schemas.md)
6. [`docs/backend/error-handling.md`](../backend/error-handling.md)
7. [`docs/frontend/visualization-specification.md`](./visualization-specification.md)
8. [`docs/frontend/page-specification.md`](./page-specification.md)
9. [`docs/graph/graph-schema.md`](../graph/graph-schema.md)
10. [`docs/development/naming-conventions.md`](../development/naming-conventions.md)
11. [`docs/development/agent-development-rules.md`](../development/agent-development-rules.md)

---

## 2. Your Responsibilities

- Implement React application in `frontend/`
- Consume only endpoints in [api-specification.md](../backend/api-specification.md)
- Handle all loading, error, and empty states
- Transform graph export to Cytoscape.js format per [visualization-specification.md](./visualization-specification.md)
- Display BTC values using `formatBtc()` utility
- Display UTC timestamps in local timezone
- Show risk levels with color-coded badges
- Display SHAP explanations as feature cards

---

## 3. What You Must NOT Do

- Call backend endpoints not in [api-specification.md](../backend/api-specification.md)
- Access DuckDB directly (browser cannot)
- Perform ML inference in the browser
- Compute risk scores client-side
- Re-interpret SHAP values — use `direction` and `displayLabel` from the API
- Render raw satoshi integers as BTC without conversion
- Import backend Python code

---

## 4. Files You Own

```
frontend/
├── src/api/          # API client functions
├── src/pages/        # Page components
├── src/components/   # UI components
├── src/hooks/        # Custom React hooks
├── src/store/        # Application state
├── src/types/        # TypeScript interfaces
└── src/utils/        # Formatting utilities
```

---

## 5. Common Mistakes to Avoid

| Mistake | Correct approach |
|---|---|
| `parseFloat(btcString)` for arithmetic | Use Decimal library for calculations |
| Displaying raw ISO 8601 timestamps | Use `formatTimestamp()` → local timezone |
| Showing `null` directly | Use `"—"` placeholder for null values |
| Inventing API endpoints | Only use endpoints in api-specification.md |
| Polling indefinitely | Stop polling on `completed` or `failed` status |
| Assuming graph nodes always have riskScore | Check for null before rendering risk UI |
| Using inline styles | Use Tailwind CSS classes |

---

## 6. Integration Checklist

- [ ] API client reads base URL from `VITE_API_BASE_URL`
- [ ] All API calls check `response.success` before using `response.data`
- [ ] Network errors produce visible error states (not silent failures)
- [ ] Analysis polling stops on `completed` or `failed`
- [ ] Graph nodes colored by `riskLevel`
- [ ] Graph edges show `totalValueBtc` as tooltip
- [ ] SHAP explanation cards use `displayLabel` from API (not hardcoded labels)
- [ ] All BTC values displayed via `formatBtc()` utility
- [ ] All timestamps displayed in local timezone
- [ ] Risk badges colored by risk level
- [ ] Empty state components shown when data arrays are empty
- [ ] Build succeeds with `npm run build`
- [ ] No console errors in production build
- [ ] All pages accessible in offline Docker deployment

---

*Last updated: 2026-09-11 | Owner: Frontend Owner*

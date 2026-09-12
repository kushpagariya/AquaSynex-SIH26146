# Frontend ↔ Backend Contract

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the definitive contract between the frontend and backend.**
> The frontend agent must not make assumptions about API responses beyond what is defined here.
> The backend agent must not change any response field without updating this document and coordinating with the Frontend Owner.

---

## 1. API Base URL

| Environment | URL |
|---|---|
| Development | `http://localhost:8000/api` |
| Docker (via Nginx proxy) | `http://localhost:3000/api` (Nginx proxies to `http://backend:8000/api`) |

The frontend API client must use a configurable base URL (from environment variable `VITE_API_BASE_URL`).

---

## 2. Response Envelope (Always)

Every API response, success or failure, uses this envelope:

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;                  // Present when success = true
  error?: ApiError;          // Present when success = false
  meta: {
    timestamp: string;       // ISO 8601 UTC
    requestId: string;       // UUID
    pagination?: Pagination; // Present for paginated responses
  };
}

interface ApiError {
  code: string;              // See error-handling.md
  message: string;
  details?: Record<string, unknown>;
}

interface Pagination {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}
```

**The frontend MUST check `response.success` before accessing `response.data`.**

---

## 3. Data Types Across the Wire

| Data Type | JSON Type | Example |
|---|---|---|
| Bitcoin value (BTC) | `string` (8-decimal) | `"5.00000000"` |
| Bitcoin value (satoshis) | `number` (integer) | `500000000` |
| Risk score | `number` (float) | `0.82` |
| Risk level | `string` (enum) | `"high"` |
| UUID identifiers | `string` | `"550e8400-e29b-41d4-a716-446655440000"` |
| Bitcoin address | `string` | `"bc1qar0..."` |
| Transaction ID | `string` (hex) | `"a1075db5..."` |
| Timestamps | `string` (ISO 8601 UTC) | `"2026-09-11T16:30:00+00:00"` |
| Nullable fields | `value \| null` | `null` |
| Missing optional fields | **not present** or `null` | — |

**BTC value parsing**: The frontend must never use `parseFloat()` on BTC strings for arithmetic. Use a Decimal library if calculations are needed.

**Timestamp display**: The backend returns UTC timestamps. The frontend converts to the investigator's local timezone for display.

---

## 4. Guaranteed vs Optional Response Fields

### Dataset

| Field | Guaranteed | Notes |
|---|---|---|
| `datasetId` | ✅ | Always present |
| `name` | ✅ | Always present |
| `status` | ✅ | Always present |
| `uploadedAt` | ✅ | Always present |
| `rowCount` | ❌ | Null until ingestion complete |
| `availableFields` | ❌ | Null until ingestion complete |
| `validationSummary` | ❌ | Null until ingestion complete |

### Transaction

| Field | Guaranteed | Notes |
|---|---|---|
| `transactionId` | ✅ | Always present |
| `timestamp` | ❌ | Null if dataset doesn't have timestamps |
| `totalInputValueBtc` | ❌ | Null if not in dataset |
| `riskScore` | ❌ | Null if analysis hasn't run |
| `riskLevel` | ❌ | Null if analysis hasn't run |

### ML Result

| Field | Guaranteed | Notes |
|---|---|---|
| `entityId` | ✅ | Always present |
| `riskScore` | ✅ | Always present (post-analysis) |
| `riskLevel` | ✅ | Always present (post-analysis) |
| `predictionLabel` | ❌ | Null for unsupervised models |
| `confidence` | ❌ | Null if model doesn't compute it |
| `explanations` | ✅ | Always present (may be empty array) |
| `graphEvidence` | ✅ | Always present (may be empty array) |

---

## 5. Loading States

The frontend must handle three states for all data-driven views:

| State | When | UI Behavior |
|---|---|---|
| `loading` | Request in flight | Show skeleton or spinner |
| `success` | `response.success === true` | Render data |
| `error` | `response.success === false` OR network error | Show error component with `error.message` |

**Empty state**: When `data` is an empty array, show an "No results" component — not an error.

---

## 6. Processing State (Analysis Polling)

After triggering an analysis (`POST /api/datasets/{id}/analyses`), the frontend receives `202 Accepted`. The analysis runs asynchronously.

**Polling strategy**:
1. Store `analysisId` from the `202` response.
2. Poll `GET /api/analyses/{analysisId}` every 3 seconds.
3. Show `status` to the investigator: `"pending"` → `"running"` → `"completed"` or `"failed"`.
4. Stop polling when `status === "completed"` or `status === "failed"`.
5. On `"completed"`: navigate to results view.
6. On `"failed"`: show `errorMessage` from the analysis record.

`DECISION REQUIRED`: WebSocket vs polling. Current proposal is HTTP polling.

---

## 7. Graph Data Contract

Graph data is returned by:
- `GET /api/analyses/{analysisId}/graph`
- `GET /api/addresses/{addressId}/graph`

The response `data` field contains a graph export conforming to [graph-schema.md](../graph/graph-schema.md).

**Frontend responsibilities**:
- Transform graph export to Cytoscape.js elements format (see [visualization-specification.md](./visualization-specification.md))
- Color-code nodes by `riskLevel`
- Scale nodes by `riskScore` or `transactionCount`
- Display edge `totalValueBtc` as tooltip

**Frontend must NOT**:
- Compute risk scores from raw graph data
- Rebuild edges or nodes from transaction records
- Assume all nodes have `riskScore` (may be null)

---

## 8. Error Handling Contract

The frontend must handle these specific error codes with dedicated UX:

| Error Code | Frontend Action |
|---|---|
| `DATASET_NOT_FOUND` | Redirect to dataset selection page |
| `ANALYSIS_NOT_FOUND` | Show "Analysis not found" message |
| `DATASET_PROCESSING` | Show processing state; begin polling |
| `MODEL_NOT_FOUND` | Show model selection error; prompt to choose another model |
| `GRAPH_NOT_AVAILABLE` | Show "Graph analysis not available — address data required" |
| `DATABASE_UNAVAILABLE` | Show system unavailable banner |
| `MODEL_LOAD_ERROR` | Show "ML model unavailable" banner |
| `VALIDATION_ERROR` | Highlight the invalid form field with `error.details.errors[].field` |
| All others | Show generic error toast with `error.message` |

---

## 9. Pagination Contract

The frontend must use these parameters for all paginated endpoints:

| Parameter | Default | Notes |
|---|---|---|
| `page` | `1` | 1-indexed |
| `pageSize` | `50` | Can be increased by user (max 500) |
| `sortBy` | endpoint-specific | See [api-specification.md](../backend/api-specification.md) |
| `sortDir` | `desc` | Default descending (most recent/highest risk first) |

Pagination metadata in `meta.pagination` drives frontend pagination controls.

---

## 10. Filtering Contract

The frontend must construct filter query parameters exactly as defined in [api-specification.md](../backend/api-specification.md). No filtering is done client-side on paginated API results.

**Allowed client-side operations**:
- Sorting a small in-memory result set (e.g., top-5 explanations already returned by API)
- Text search on a small in-memory list of datasets

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: Frontend Owner + Backend Owner (joint)*
*References: [api-specification.md](../backend/api-specification.md) | [error-handling.md](../backend/error-handling.md) | [graph-schema.md](../graph/graph-schema.md)*

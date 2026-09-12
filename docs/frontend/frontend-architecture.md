# Frontend Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Application Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── package.json
├── public/
└── src/
    ├── main.tsx                    # Application entry point
    ├── App.tsx                     # Root component + router
    ├── api/
    │   ├── client.ts               # Axios/fetch wrapper with base URL + error handling
    │   ├── datasets.ts             # Dataset API calls
    │   ├── analyses.ts             # Analysis API calls
    │   ├── transactions.ts         # Transaction API calls
    │   ├── addresses.ts            # Address API calls
    │   ├── graph.ts                # Graph API calls
    │   └── models.ts               # Models API calls
    ├── pages/
    │   ├── DashboardPage.tsx       # Overview / welcome
    │   ├── DatasetsPage.tsx        # Dataset management
    │   ├── AnalysisPage.tsx        # Analysis run + status
    │   ├── TransactionsPage.tsx    # Transaction explorer
    │   ├── AddressesPage.tsx       # Address/entity explorer
    │   ├── AddressDetailPage.tsx   # Full address profile
    │   ├── GraphPage.tsx           # Graph visualization
    │   └── NotFoundPage.tsx        # 404
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.tsx
    │   │   ├── Header.tsx
    │   │   └── PageLayout.tsx
    │   ├── datasets/
    │   │   ├── DatasetCard.tsx
    │   │   ├── DatasetUpload.tsx
    │   │   └── DatasetSelector.tsx
    │   ├── analysis/
    │   │   ├── AnalysisStatus.tsx
    │   │   └── AnalysisConfig.tsx
    │   ├── transactions/
    │   │   ├── TransactionTable.tsx
    │   │   └── TransactionDetail.tsx
    │   ├── addresses/
    │   │   ├── AddressTable.tsx
    │   │   └── AddressDetail.tsx
    │   ├── graph/
    │   │   ├── GraphViewer.tsx     # Cytoscape.js container
    │   │   └── GraphControls.tsx
    │   ├── risk/
    │   │   ├── RiskBadge.tsx       # Color-coded risk level badge
    │   │   ├── RiskBar.tsx         # Risk score progress bar
    │   │   └── RiskDistribution.tsx  # Recharts risk histogram
    │   ├── explanation/
    │   │   └── ExplanationCard.tsx # SHAP feature explanation card
    │   └── common/
    │       ├── LoadingSpinner.tsx
    │       ├── ErrorMessage.tsx
    │       ├── EmptyState.tsx
    │       ├── Pagination.tsx
    │       └── FilterBar.tsx
    ├── hooks/
    │   ├── useDatasets.ts
    │   ├── useAnalysis.ts
    │   ├── useTransactions.ts
    │   ├── useAddresses.ts
    │   ├── useGraph.ts
    │   └── usePolling.ts           # Generic polling hook for async analysis
    ├── store/
    │   └── appStore.ts             # Application state (Zustand or React Context)
    ├── types/
    │   ├── api.ts                  # TypeScript types matching API schemas
    │   └── graph.ts                # Cytoscape-specific types
    └── utils/
        ├── btcFormatter.ts         # BTC value display formatting
        ├── dateFormatter.ts        # UTC → local timezone display
        └── riskColors.ts           # Risk level → Tailwind color mapping
```

---

## 2. Routing

```
/                           → DashboardPage
/datasets                   → DatasetsPage
/datasets/:datasetId/analysis → AnalysisPage
/datasets/:datasetId/transactions → TransactionsPage
/datasets/:datasetId/addresses    → AddressesPage
/addresses/:addressId       → AddressDetailPage
/datasets/:datasetId/graph  → GraphPage
```

Router: `react-router-dom` v6

---

## 3. API Client

The API client in `src/api/client.ts` handles:
- Base URL configuration (from `VITE_API_BASE_URL`)
- All requests include standard headers
- Response envelope unpacking (returns `data` or throws typed `ApiError`)
- Automatic `requestId` logging

```typescript
// Proposed pattern
async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { ... });
  const envelope: ApiResponse<T> = await response.json();
  if (!envelope.success) {
    throw new ApiError(envelope.error!);
  }
  return envelope.data!;
}
```

---

## 4. State Management

`DECISION REQUIRED` (Q-006): React Context vs Zustand vs Redux

**Proposed approach**: Zustand for global state (selected dataset, active analysis ID, current page filters). React Query or SWR for server state (cache, loading, error states).

**What needs global state**:
- Currently selected `datasetId`
- Currently active `analysisId`
- Active filter state (for transaction/address tables)

---

## 5. BTC Value Display

All BTC value display goes through `src/utils/btcFormatter.ts`:

```typescript
export function formatBtc(btcString: string | null | undefined): string {
  if (!btcString) return "—";
  const num = parseFloat(btcString); // OK for display only
  return `${num.toFixed(8)} BTC`;
}

export function formatSatoshi(satoshi: number | null | undefined): string {
  if (satoshi === null || satoshi === undefined) return "—";
  return `${satoshi.toLocaleString()} sat`;
}
```

**Never perform arithmetic on formatted display strings.**

---

## 6. Timestamp Display

All timestamp display goes through `src/utils/dateFormatter.ts`:

```typescript
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(); // Converts UTC → local browser timezone
}
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Frontend Owner*
*References: [frontend-backend-contract.md](./frontend-backend-contract.md) | [page-specification.md](./page-specification.md)*

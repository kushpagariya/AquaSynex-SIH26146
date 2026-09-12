# Component Specification

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## Key Components

### `RiskBadge`

- **Props**: `level: 'low' | 'medium' | 'high' | 'critical' | null`
- **Renders**: Color-coded pill label
- **Colors**: See [visualization-specification.md](./visualization-specification.md)

### `RiskBar`

- **Props**: `score: number | null`
- **Renders**: Horizontal bar filled to `score * 100%`, colored by risk level

### `ExplanationCard`

- **Props**: `explanation: FeatureExplanationSchema`
- **Renders**: Feature name (from `displayLabel`), direction indicator, feature value with unit, importance bar
- **Data source**: From API — never hardcode display labels

### `GraphViewer`

- **Props**: `nodes: NodeObject[], edges: EdgeObject[], isSubgraph: boolean`
- **Renders**: Cytoscape.js canvas with configured styles
- **Events**: `onNodeClick`, `onEdgeClick`

### `TransactionTable`

- **Props**: `datasetId, analysisId (optional), filters, pagination`
- **Renders**: Paginated, sortable transaction table
- **Includes**: Risk badge column if analysis has run

### `AddressTable`

- **Props**: `datasetId, analysisId (optional), filters, pagination`
- **Renders**: Paginated, sortable address table

### `DatasetUpload`

- **Props**: `onUploadSuccess: (dataset: DatasetSummary) => void`
- **Renders**: File input + name field + upload button
- **Behavior**: POST to `/api/datasets/upload`, show progress, handle errors

### `AnalysisStatus`

- **Props**: `analysisId`
- **Renders**: Status indicator that polls `GET /api/analyses/{id}` until terminal state
- **States**: pending, running (with elapsed time), completed, failed

### `LoadingSpinner`

- Generic loading state component

### `ErrorMessage`

- **Props**: `code: string, message: string`
- **Renders**: Error box with user-visible message
- **Must not**: Display raw stack traces or internal error details

### `EmptyState`

- **Props**: `message: string, actionLabel?: string, onAction?: () => void`
- **Renders**: Empty state illustration + message + optional CTA

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Frontend Owner*

# API Specification

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative REST API specification.**
> The frontend agent must not call any endpoint not defined here.
> The backend agent must implement every endpoint defined here.
> Changing this document requires review from both Backend Owner and Frontend Owner.

---

## 1. API Conventions

### Base URL

```
Development: http://localhost:8000/api
Production:  http://backend:8000/api  (via Nginx proxy at port 3000)
```

### Response Envelope

All API responses use a **standard envelope**:

#### Success Response

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-09-11T16:30:00+00:00",
    "requestId": "uuid-string"
  }
}
```

#### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  },
  "meta": {
    "timestamp": "2026-09-11T16:30:00+00:00",
    "requestId": "uuid-string"
  }
}
```

**The frontend must always check `success` before accessing `data`.** See [error-handling.md](./error-handling.md).

### Pagination

Paginated responses include pagination in `meta`:

```json
{
  "success": true,
  "data": [...],
  "meta": {
    "timestamp": "...",
    "requestId": "...",
    "pagination": {
      "page": 1,
      "pageSize": 50,
      "totalItems": 1243,
      "totalPages": 25,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

Default page size: `50`. Maximum page size: `500`.

### Common Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number (1-indexed) |
| `pageSize` | integer | Items per page (default: 50, max: 500) |
| `sortBy` | string | Field to sort by |
| `sortDir` | string | `asc` or `desc` |

### Authentication

`DECISION REQUIRED` — Authentication is not implemented in Phase 1. All endpoints are unauthenticated. This must be documented and the decision explicitly made before production deployment.

---

## 2. Health API

### `GET /api/health`

**Purpose**: System health check for Docker health checks and frontend readiness check.

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "databaseStatus": "connected",
    "modelsAvailable": ["isolation_forest_v1"],
    "uptime": 3600
  },
  "meta": { "timestamp": "...", "requestId": "..." }
}
```

**Error response** (`503 Service Unavailable`): If DuckDB is not accessible.

---

## 3. Dataset API

### `GET /api/datasets`

**Purpose**: List all registered datasets.

**Query parameters**: `page`, `pageSize`, `sortBy` (`uploadedAt`, `name`, `rowCount`), `sortDir`

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": [
    {
      "datasetId": "uuid",
      "name": "string",
      "fileName": "string",
      "format": "csv",
      "sizeBytes": 104857600,
      "rowCount": 500000,
      "status": "ready",
      "uploadedAt": "2026-09-11T10:00:00+00:00",
      "availableFields": ["transactionId", "timestamp", "outputAddress"]
    }
  ],
  "meta": { "timestamp": "...", "requestId": "...", "pagination": {...} }
}
```

---

### `POST /api/datasets/upload`

**Purpose**: Upload a dataset file.

**Request**: `multipart/form-data`
- `file` — Dataset file (CSV, JSON, JSONL, Parquet)
- `name` — User-provided dataset name (string, required)

**Response** (`202 Accepted`):
```json
{
  "success": true,
  "data": {
    "datasetId": "uuid",
    "name": "string",
    "status": "processing",
    "uploadedAt": "2026-09-11T10:00:00+00:00"
  },
  "meta": { ... }
}
```

**Error cases**:
- `400` / `VALIDATION_ERROR` — Missing file or name
- `400` / `DATASET_ERROR` — Unsupported file format
- `413` / `DATASET_ERROR` — File too large
- `500` / `INTERNAL_ERROR` — Storage error

---

### `GET /api/datasets/{datasetId}`

**Purpose**: Get dataset details and validation summary.

**Path params**: `datasetId` (UUID)

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "datasetId": "uuid",
    "name": "string",
    "fileName": "string",
    "format": "csv",
    "sizeBytes": 104857600,
    "rowCount": 500000,
    "canonicalTxCount": 499832,
    "status": "ready",
    "uploadedAt": "2026-09-11T10:00:00+00:00",
    "availableFields": ["transactionId", "timestamp", "outputAddress"],
    "validationSummary": {
      "rejectedRows": 168,
      "warnedRows": 4230,
      "fieldCoverage": { "transactionId": 1.0, "timestamp": 0.98 },
      "analysisCapability": {
        "graphAnalysis": true,
        "temporalAnalysis": true
      }
    }
  },
  "meta": { ... }
}
```

**Error cases**: `404` / `DATA_NOT_FOUND`

---

### `DELETE /api/datasets/{datasetId}`

**Purpose**: Delete a dataset and all associated analysis results.

**Response** (`200 OK`): `{ "success": true, "data": { "deleted": true } }`

**Error cases**: `404`, `400` if analysis is currently running on this dataset

---

## 4. Analysis API

### `POST /api/datasets/{datasetId}/analyses`

**Purpose**: Trigger a new analysis run on a dataset.

**Request body**:
```json
{
  "modelId": "isolation_forest_v1",
  "modelVersion": "1.0.0",
  "config": {
    "maxEntities": 10000,
    "topExplanations": 5
  }
}
```

All fields optional. If `modelId` omitted, uses the default configured model.

**Response** (`202 Accepted`):
```json
{
  "success": true,
  "data": {
    "analysisId": "uuid",
    "datasetId": "uuid",
    "status": "pending",
    "startedAt": "2026-09-11T16:00:00+00:00"
  },
  "meta": { ... }
}
```

---

### `GET /api/datasets/{datasetId}/analyses`

**Purpose**: List all analysis runs for a dataset.

**Response** (`200 OK`): List of analysis run summaries.

---

### `GET /api/analyses/{analysisId}`

**Purpose**: Get analysis run status and summary.

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "analysisId": "uuid",
    "datasetId": "uuid",
    "status": "completed",
    "startedAt": "...",
    "completedAt": "...",
    "modelId": "isolation_forest_v1",
    "modelVersion": "1.0.0",
    "entityCount": 45230,
    "highRiskCount": 142,
    "criticalRiskCount": 18
  },
  "meta": { ... }
}
```

---

## 5. Transaction API

### `GET /api/datasets/{datasetId}/transactions`

**Purpose**: List transactions in a dataset with filtering and pagination.

**Query parameters**:
| Parameter | Type | Description |
|---|---|---|
| `page` | integer | Page number |
| `pageSize` | integer | Page size |
| `sortBy` | string | `timestamp`, `totalValueSatoshi`, `inputCount`, `outputCount`, `riskScore` |
| `sortDir` | string | `asc` / `desc` |
| `riskLevel` | string | Filter: `low`, `medium`, `high`, `critical` |
| `minRiskScore` | float | Minimum risk score [0.0, 1.0] |
| `maxRiskScore` | float | Maximum risk score |
| `fromTimestamp` | string | ISO 8601 datetime |
| `toTimestamp` | string | ISO 8601 datetime |
| `minValueBtc` | string | Minimum total value (BTC decimal string) |
| `analysisId` | string | Filter to transactions with ML results from this analysis |
| `ip` | string | Filter transactions associated with this network IP (via network_events semi-join) |
| `address` | string | Filter transactions involving this Bitcoin address (inputs or outputs) |
| `txid` | string | Filter to specific transaction ID |

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": [
    {
      "transactionId": "string",
      "blockHeight": 170,
      "timestamp": "2009-01-12T03:30:25+00:00",
      "inputCount": 1,
      "outputCount": 2,
      "totalInputValueBtc": "50.00000000",
      "totalOutputValueBtc": "49.99900000",
      "feeBtc": "0.00100000",
      "riskScore": 0.82,
      "riskLevel": "high"
    }
  ],
  "meta": { "pagination": {...} }
}
```

---

### `GET /api/transactions/{transactionId}`

**Purpose**: Get full transaction detail.

**Response** includes transaction fields + ML result for this transaction (if available).

---

## 6. Address / Entity API

### `GET /api/datasets/{datasetId}/addresses`

**Purpose**: List addresses with risk scores and behavioral summary.

**Query parameters**: Same filtering pattern as transactions (`riskLevel`, `minRiskScore`, etc.)

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": [
    {
      "addressId": "bc1q...",
      "transactionCount": 142,
      "totalReceivedBtc": "5.00000000",
      "totalSentBtc": "4.99000000",
      "firstSeen": "2009-01-12T03:30:25+00:00",
      "lastSeen": "2009-03-14T12:00:00+00:00",
      "riskScore": 0.82,
      "riskLevel": "high"
    }
  ],
  "meta": { "pagination": {...} }
}
```

---

### `GET /api/addresses/{addressId}`

**Purpose**: Get full address profile including ML result and graph evidence.

**Query parameters**: `analysisId` (optional — specifies which analysis result to include)

**Response** includes: address summary + ML result + top explanations + graph evidence.

---

## 7. Graph API

### `GET /api/analyses/{analysisId}/graph`

**Purpose**: Return the full transaction graph (nodes + edges) for a Cytoscape.js visualization.

**Query parameters**:
| Parameter | Description |
|---|---|
| `minRiskScore` | Only include nodes with risk score ≥ this value |
| `maxNodes` | Limit to top N highest-risk nodes (default: 500) |
| `includeNeighbors` | Include 1-hop neighbors of filtered nodes |

**Response** (`200 OK`): Graph export JSON conforming to [graph-schema.md](../graph/graph-schema.md).

---

### `GET /api/addresses/{addressId}/graph`

**Purpose**: Return the N-hop neighborhood subgraph around a specific address.

**Query parameters**: `hops` (default: 2, max: 3), `analysisId`

**Response**: Neighborhood subgraph conforming to [graph-schema.md](../graph/graph-schema.md).

---

## 8. Risk / ML Results API

### `GET /api/analyses/{analysisId}/results`

**Purpose**: List all ML results for an analysis run.

**Query parameters**: `riskLevel`, `minRiskScore`, `entityType`, `page`, `pageSize`, `sortBy` (`riskScore`, `anomalyScore`)

**Response** (`200 OK`): List of ML result summaries (without full explanation detail).

---

### `GET /api/analyses/{analysisId}/results/{entityId}`

**Purpose**: Get full ML result for one entity, including explanations.

**Response** (`200 OK`): Full ML result conforming to [model-output-contract.md](../ml/model-output-contract.md).

---

## 9. Models API

### `GET /api/models`

**Purpose**: List available ML models.

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": [
    {
      "modelId": "isolation_forest_v1",
      "modelVersion": "1.0.0",
      "algorithm": "IsolationForest",
      "modelType": "anomaly_detection",
      "featureSchemaVersion": "1.0.0",
      "trainingCompletedAt": "2026-09-11T10:00:00+00:00"
    }
  ],
  "meta": { ... }
}
```

---

## 10. Network Intelligence & Offline GeoIP/ASN Map API

### `GET /api/datasets/{datasetId}/network/map`

**Alternative Route**: `GET /api/network/map?datasetId={datasetId}`

**Purpose**: Retrieve aggregated network endpoints enriched with offline GeoIP and ASN metadata from local MMDB databases (`datasets/GeoLite2-City.mmdb` and `datasets/ipinfo_lite.mmdb`).

**Query parameters**:
| Parameter | Type | Description |
|---|---|---|
| `datasetId` | string | **Required** for alternative route (`GET /api/network/map`). Target dataset identifier. |
| `analysisId` | string | *Optional*. Analysis ID context. |

**Response** (`200 OK`):
```json
{
  "success": true,
  "data": {
    "datasetId": "uuid",
    "analysisId": "uuid",
    "metrics": {
      "totalIps": 180,
      "mappedIps": 165,
      "unmappedIps": 15,
      "uniqueCountries": 28,
      "uniqueAsns": 42,
      "totalEvents": 520
    },
    "points": [
      {
        "ip": "104.26.184.134",
        "country": "United States",
        "countryCode": "US",
        "region": "California",
        "city": "San Francisco",
        "latitude": 37.751,
        "longitude": -97.822,
        "asn": "AS13335",
        "asName": "Cloudflare, Inc.",
        "asDomain": "cloudflare.com",
        "eventCount": 42,
        "transactionCount": 38,
        "sourceEventCount": 30,
        "destinationEventCount": 12,
        "firstSeen": "2026-09-11T10:00:00+00:00",
        "lastSeen": "2026-09-11T12:00:00+00:00",
        "isMapped": true
      }
    ],
    "edges": [
      {
        "srcIp": "104.26.184.134",
        "dstIp": "198.51.100.12",
        "eventCount": 24,
        "transactionCount": 18
      }
    ]
  },
  "meta": { "timestamp": "...", "requestId": "..." }
}
```

---

*Last updated: 2026-09-20 | Status: IMPLEMENTED | Owner: Backend Owner + Frontend Owner (joint)*
*References: [request-response-schemas.md](./request-response-schemas.md) | [error-handling.md](./error-handling.md) | [validation-rules.md](./validation-rules.md)*

# Error Handling

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative error contract.**
> All error codes and formats defined here must be used consistently across backend, frontend, and ML pipeline.
> Do not invent new error codes without updating this document.

---

## 1. Error Response Format

All API errors return the standard error envelope:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message for logging and debugging",
    "details": {
      "field": "relevant_field",
      "constraint": "what was violated",
      "provided": "what was provided"
    }
  },
  "meta": {
    "timestamp": "2026-09-11T16:30:00+00:00",
    "requestId": "uuid-string"
  }
}
```

| Field | Required | Description |
|---|---|---|
| `code` | Yes | Machine-readable error code (all caps, underscores) |
| `message` | Yes | Human-readable description |
| `details` | No | Additional context; schema varies by error type |

---

## 2. HTTP Status Codes

| HTTP Status | When Used |
|---|---|
| `200 OK` | Successful request |
| `202 Accepted` | Async operation started (e.g., analysis triggered) |
| `400 Bad Request` | Validation error, malformed request |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Resource conflict (e.g., analysis already running) |
| `413 Payload Too Large` | File upload exceeds size limit |
| `422 Unprocessable Entity` | Request is valid JSON but semantically invalid |
| `500 Internal Server Error` | Unexpected backend error |
| `503 Service Unavailable` | Database or ML pipeline unavailable |

---

## 3. Error Codes

### 3.1 Validation Errors (4xx)

| Code | HTTP | Description |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Request field failed validation. `details` includes `field`, `constraint`, `provided`. |
| `INVALID_FIELD_VALUE` | 400 | A field has an invalid value (e.g., negative risk score). |
| `MISSING_REQUIRED_FIELD` | 400 | A required request field is missing. |
| `INVALID_PAGINATION` | 400 | Page or pageSize out of allowed range. |
| `INVALID_SORT_FIELD` | 400 | `sortBy` field is not sortable or does not exist. |
| `INVALID_FILTER_VALUE` | 400 | A filter parameter has an invalid value. |
| `UNSUPPORTED_FILE_FORMAT` | 400 | Uploaded file format is not supported. |
| `FILE_TOO_LARGE` | 413 | Uploaded file exceeds size limit. |

### 3.2 Resource Errors (4xx)

| Code | HTTP | Description |
|---|---|---|
| `DATASET_NOT_FOUND` | 404 | No dataset with the given `datasetId`. |
| `ANALYSIS_NOT_FOUND` | 404 | No analysis with the given `analysisId`. |
| `ADDRESS_NOT_FOUND` | 404 | No address with the given `addressId` in the dataset. |
| `TRANSACTION_NOT_FOUND` | 404 | No transaction with the given `transactionId`. |
| `MODEL_NOT_FOUND` | 404 | No ML model with the given `modelId` / `modelVersion`. |
| `RESULT_NOT_FOUND` | 404 | No ML result for the given entity in the given analysis. |

### 3.3 Dataset / Pipeline Errors

| Code | HTTP | Description |
|---|---|---|
| `DATASET_ERROR` | 400 | Dataset cannot be processed (corrupt, invalid format, insufficient fields). |
| `DATASET_PROCESSING` | 409 | Dataset is currently being processed; retry later. |
| `DATASET_ANALYSIS_RUNNING` | 409 | An analysis is already running on this dataset; cannot delete or re-analyze. |
| `PIPELINE_ERROR` | 500 | Data ingestion or normalization pipeline failed unexpectedly. |

### 3.4 ML Errors

| Code | HTTP | Description |
|---|---|---|
| `ML_ERROR` | 500 | ML pipeline failed unexpectedly. |
| `INVALID_FEATURES` | 500 | Feature matrix missing required features for the model. |
| `MODEL_LOAD_ERROR` | 503 | Failed to load the ML model artifact from disk. |
| `FEATURE_SCHEMA_MISMATCH` | 500 | Feature schema version mismatch between model and current pipeline. |

### 3.5 Graph Errors

| Code | HTTP | Description |
|---|---|---|
| `GRAPH_ERROR` | 500 | Graph construction or analysis failed. |
| `GRAPH_NOT_AVAILABLE` | 404 | Graph has not been built for this analysis (may be due to missing address fields). |
| `GRAPH_TOO_LARGE` | 400 | Requested subgraph exceeds maximum allowed size. |

### 3.6 Database Errors

| Code | HTTP | Description |
|---|---|---|
| `DATABASE_ERROR` | 503 | DuckDB query failed unexpectedly. |
| `DATABASE_UNAVAILABLE` | 503 | DuckDB database file is not accessible. |

### 3.7 Internal Errors

| Code | HTTP | Description |
|---|---|---|
| `INTERNAL_ERROR` | 500 | Unexpected internal error. Check server logs. |
| `NOT_IMPLEMENTED` | 500 | Endpoint exists in specification but is not yet implemented. |

---

## 4. Error Detail Schemas

### VALIDATION_ERROR

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "details": {
    "errors": [
      {
        "field": "minRiskScore",
        "constraint": "must be between 0.0 and 1.0",
        "provided": -0.5
      }
    ]
  }
}
```

### DATASET_ERROR

```json
{
  "code": "DATASET_ERROR",
  "message": "Dataset cannot be processed",
  "details": {
    "reason": "No column mappable to transactionId found",
    "availableColumns": ["time", "value", "category"]
  }
}
```

### INVALID_FEATURES

```json
{
  "code": "INVALID_FEATURES",
  "message": "Feature matrix is missing features required by the model",
  "details": {
    "modelId": "isolation_forest_v1",
    "missingFeatures": ["addr_tx_per_day", "graph_pagerank"],
    "featureSchemaVersion": "1.0.0"
  }
}
```

---

## 5. Frontend Error Handling Requirements

The frontend must:

1. **Always check `success` field** before accessing `data`.
2. **Display `error.message`** in a user-visible error component for operational errors.
3. **Log `error.code` and `requestId`** to the browser console for debugging.
4. **Handle specific error codes** for actionable errors:
   - `DATASET_NOT_FOUND` → redirect to dataset selection
   - `ANALYSIS_NOT_FOUND` → show "Analysis not found" message
   - `DATASET_PROCESSING` → show processing state, poll for status
   - `DATABASE_UNAVAILABLE` / `MODEL_LOAD_ERROR` → show system unavailable banner
5. **Never expose raw stack traces** to the investigator UI.

---

## 6. ML Layer Error Handling

The ML pipeline communicates errors to the backend via Python exceptions:

| Exception Class | Maps to Backend Error Code |
|---|---|
| `DatasetError` | `DATASET_ERROR` or `PIPELINE_ERROR` |
| `InvalidFeaturesError` | `INVALID_FEATURES` |
| `FeatureSchemaMismatchError` | `FEATURE_SCHEMA_MISMATCH` |
| `ModelLoadError` | `MODEL_LOAD_ERROR` |
| `GraphError` | `GRAPH_ERROR` |
| `Exception` (uncaught) | `ML_ERROR` |

The backend catches all ML exceptions and wraps them in the standard error response.

---

*Last updated: 2026-09-11 | Status: IN PROGRESS | Owner: Backend Owner + Frontend Owner (joint)*
*References: [api-specification.md](./api-specification.md) | [validation-rules.md](./validation-rules.md)*

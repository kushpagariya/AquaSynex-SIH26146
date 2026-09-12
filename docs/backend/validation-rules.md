# Validation Rules

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **API input validation rules. These are authoritative.**
> Backend validation is the security boundary. Frontend validation improves UX but is not a substitute.

---

## 1. Validation Philosophy

| Layer | Role |
|---|---|
| Frontend | UX improvement — immediate feedback before API call |
| Backend | **Security boundary** — all inputs validated; errors returned via API error contract |
| Data pipeline | Data quality — validate dataset records during ingestion |
| ML pipeline | Feature quality — validate feature matrix before inference |

---

## 2. API Parameter Validation Rules

### Pagination

| Parameter | Type | Min | Max | Default |
|---|---|---|---|---|
| `page` | integer | 1 | — | 1 |
| `pageSize` | integer | 1 | 500 | 50 |

**Error**: `INVALID_PAGINATION`

### Sort Direction

| Parameter | Allowed values |
|---|---|
| `sortDir` | `asc`, `desc` |

**Error**: `VALIDATION_ERROR` with `field: "sortDir"`

### Risk Score Filter

| Parameter | Type | Range |
|---|---|---|
| `minRiskScore` | float | [0.0, 1.0] |
| `maxRiskScore` | float | [0.0, 1.0] |

Must satisfy `minRiskScore <= maxRiskScore` if both provided.

**Error**: `INVALID_FILTER_VALUE`

### Risk Level Filter

| Value | Valid |
|---|---|
| `low` | ✅ |
| `medium` | ✅ |
| `high` | ✅ |
| `critical` | ✅ |
| anything else | ❌ `INVALID_FILTER_VALUE` |

### Timestamp Filter

| Parameter | Format | Requirement |
|---|---|---|
| `fromTimestamp` | ISO 8601 | Must be parseable |
| `toTimestamp` | ISO 8601 | Must be parseable |

Must satisfy `fromTimestamp <= toTimestamp` if both provided.

---

## 3. Dataset Upload Validation

| Field | Rule | Error |
|---|---|---|
| `file` | Required; must be non-empty | `MISSING_REQUIRED_FIELD` |
| `file` extension | `.csv`, `.json`, `.jsonl`, `.parquet` | `UNSUPPORTED_FILE_FORMAT` |
| `file` size | ≤ `MAX_UPLOAD_SIZE_BYTES` (env var, default 2GB) | `FILE_TOO_LARGE` |
| `name` | Required; non-empty string; 1–200 chars | `MISSING_REQUIRED_FIELD` / `VALIDATION_ERROR` |

---

## 4. Analysis Request Validation

| Field | Rule |
|---|---|
| `modelId` | Optional; if provided, must exist in model registry |
| `modelVersion` | Optional; if provided with modelId, must match |
| `config.maxEntities` | Integer, ≥ 1, ≤ 1,000,000 (default: 10,000) |
| `config.topExplanations` | Integer, 1–20 (default: 5) |

**Error if dataset is not in `ready` status**: `DATASET_PROCESSING` or `DATASET_ERROR`

---

## 5. UUID Path Parameters

| Parameter | Rule |
|---|---|
| `datasetId` | Must be valid UUID v4 |
| `analysisId` | Must be valid UUID v4 |

**Error**: `VALIDATION_ERROR` if malformed; `DATA_NOT_FOUND` if not in DuckDB.

---

## 6. BTC Value Parameters

| Parameter | Format | Rule |
|---|---|---|
| `minValueBtc` | string or numeric | Non-negative; parseable as decimal |
| `maxValueBtc` | string or numeric | Non-negative; parseable as decimal |

Backend converts these to satoshis internally using `btc_str_to_satoshi()`.

---

## 7. Feature Matrix Validation (ML Layer)

These validations run within the ML pipeline before inference:

| Check | Rule | Error |
|---|---|---|
| No NaN values | All features imputed | `INVALID_FEATURES` |
| Correct columns | All model-required features present | `INVALID_FEATURES` |
| Feature schema version | Matches model artifact version | `FEATURE_SCHEMA_MISMATCH` |
| Risk score output | `0.0 ≤ risk_score ≤ 1.0` | `ML_ERROR` if violated |
| Risk level consistency | `risk_level` matches `risk_score` range | `ML_ERROR` if violated |

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner*
*References: [error-handling.md](./error-handling.md) | [api-specification.md](./api-specification.md)*

# API Reference (Quick Reference)

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> Quick reference for all API endpoints. See [api-specification.md](./api-specification.md) for full documentation.

---

## Endpoint Summary

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/api/health` | System health check | `PLANNED` |
| GET | `/api/datasets` | List all datasets | `PLANNED` |
| POST | `/api/datasets/upload` | Upload a dataset file | `PLANNED` |
| GET | `/api/datasets/{datasetId}` | Get dataset details | `PLANNED` |
| DELETE | `/api/datasets/{datasetId}` | Delete a dataset | `PLANNED` |
| POST | `/api/datasets/{datasetId}/analyses` | Trigger analysis | `PLANNED` |
| GET | `/api/datasets/{datasetId}/analyses` | List analyses for dataset | `PLANNED` |
| GET | `/api/analyses/{analysisId}` | Get analysis status/summary | `PLANNED` |
| GET | `/api/datasets/{datasetId}/transactions` | List transactions (filtered, paginated) | `PLANNED` |
| GET | `/api/transactions/{transactionId}` | Get transaction detail | `PLANNED` |
| GET | `/api/datasets/{datasetId}/addresses` | List addresses (filtered, paginated) | `PLANNED` |
| GET | `/api/addresses/{addressId}` | Get address profile | `PLANNED` |
| GET | `/api/analyses/{analysisId}/graph` | Get full analysis graph | `PLANNED` |
| GET | `/api/addresses/{addressId}/graph` | Get address neighborhood graph | `PLANNED` |
| GET | `/api/analyses/{analysisId}/results` | List ML results (paginated) | `PLANNED` |
| GET | `/api/analyses/{analysisId}/results/{entityId}` | Get ML result for entity | `PLANNED` |
| GET | `/api/models` | List available ML models | `PLANNED` |

---

## Common Response Codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 202 | Accepted (async operation started) |
| 400 | Bad request / validation error |
| 404 | Resource not found |
| 409 | Conflict |
| 500 | Internal error |
| 503 | Service unavailable |

---

*See [api-specification.md](./api-specification.md) for full detail.*

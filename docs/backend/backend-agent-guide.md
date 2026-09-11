# Backend Agent Guide

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This document is for the AI agent responsible for the Backend subsystem.

---

## 1. Mandatory Reading

1. [`docs/README.md`](../README.md)
2. This document
3. [`docs/backend/api-specification.md`](./api-specification.md) — **Your primary contract**
4. [`docs/backend/request-response-schemas.md`](./request-response-schemas.md)
5. [`docs/backend/error-handling.md`](./error-handling.md)
6. [`docs/backend/duckdb-schema.md`](./duckdb-schema.md)
7. [`docs/ml/model-output-contract.md`](../ml/model-output-contract.md)
8. [`docs/backend/backend-ml-contract.md`](./backend-ml-contract.md)
9. [`docs/data/canonical-schema.md`](../data/canonical-schema.md)
10. [`docs/development/naming-conventions.md`](../development/naming-conventions.md)
11. [`docs/development/agent-development-rules.md`](../development/agent-development-rules.md)

---

## 2. Your Responsibilities

- Implement FastAPI application in `backend/`
- Define all routes in [api-specification.md](./api-specification.md)
- Create DuckDB tables per [duckdb-schema.md](./duckdb-schema.md)
- Invoke ML pipeline per [backend-ml-contract.md](./backend-ml-contract.md)
- Validate inputs per [validation-rules.md](./validation-rules.md)
- Return errors per [error-handling.md](./error-handling.md)
- Serialize BTC values as 8-decimal strings (never as raw floats)
- Return UTC timestamps in ISO 8601

---

## 3. What You Must NOT Do

- Modify ML pipeline code (`pipeline/`)
- Modify frontend code (`frontend/`)
- Add new endpoints not in [api-specification.md](./api-specification.md) without documenting them
- Return raw satoshi integers as `totalValueBtc` — always use `satoshi_to_btc_str()`
- Access internet at runtime
- Change DuckDB table schemas without updating [duckdb-schema.md](./duckdb-schema.md)

---

## 4. Files You Own

```
backend/
├── main.py
├── config.py
├── dependencies.py
├── api/
├── services/
├── db/
├── schemas/
└── utils/
```

---

## 5. Common Mistakes to Avoid

| Mistake | Correct approach |
|---|---|
| Returning BTC as JSON float | Use `f"{satoshi / 1e8:.8f}"` as string |
| Returning naive datetime | Always use UTC timezone-aware datetime |
| Inventing new error codes | Use only codes from [error-handling.md](./error-handling.md) |
| Silently ignoring ML errors | Catch all ML exceptions; return structured error |
| Using `SELECT *` in production queries | Select only needed columns |
| Hardcoding paths | Use `settings.DATA_DIR`, `settings.DB_PATH`, etc. |

---

## 6. Integration Checklist

- [ ] All endpoints in [api-specification.md](./api-specification.md) are implemented
- [ ] All responses use standard envelope (`success`, `data`, `meta`)
- [ ] All BTC values are 8-decimal strings
- [ ] All timestamps are UTC ISO 8601
- [ ] DuckDB tables match [duckdb-schema.md](./duckdb-schema.md)
- [ ] ML pipeline invoked per [backend-ml-contract.md](./backend-ml-contract.md)
- [ ] All ML exceptions are caught and mapped to error codes
- [ ] `/api/health` returns 200 with database status
- [ ] All environment variables documented in [configuration.md](./configuration.md)
- [ ] `requirements.txt` is complete and Docker-compatible
- [ ] CORS is configured for development and production

---

*Last updated: 2026-09-11 | Owner: Backend Owner*

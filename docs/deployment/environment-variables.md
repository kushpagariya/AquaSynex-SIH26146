# Environment Variables

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> Never put real secrets into this document. Use `.env.example` for templates.

---

## Complete Variable Reference

| Variable | Required | Secret | Service | Default | Purpose |
|---|---|---|---|---|---|
| `DB_PATH` | Yes | No | backend | `/app/db/aquasynex.db` | Path to DuckDB database file |
| `DATA_DIR` | Yes | No | backend | `/app/data` | Directory for dataset files |
| `MODELS_DIR` | Yes | No | backend | `/app/models` | Directory for ML model artifacts |
| `ALLOWED_ORIGINS` | Yes | No | backend | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `MAX_UPLOAD_SIZE_BYTES` | No | No | backend | `2147483648` | Maximum file upload size (2GB) |
| `DEFAULT_MODEL_ID` | No | No | backend | `isolation_forest_v1` | Default ML model to use |
| `DEFAULT_MODEL_VERSION` | No | No | backend | `1.0.0` | Default model version |
| `DEFAULT_TOP_EXPLANATIONS` | No | No | backend | `5` | Max SHAP explanations per entity |
| `DEFAULT_MAX_ENTITIES` | No | No | backend | `10000` | Max entities per analysis run |
| `LOG_LEVEL` | No | No | backend | `INFO` | Python logging level |
| `VITE_API_BASE_URL` | Yes | No | frontend | `http://localhost:8000/api` | Backend API base URL (build-time) |
| `BACKEND_HOST` | No | No | frontend (Nginx) | `backend` | Backend hostname for Nginx proxy |
| `BACKEND_PORT` | No | No | frontend (Nginx) | `8000` | Backend port for Nginx proxy |

---

## `.env.example`

```bash
# ── Backend Configuration ──────────────────────────────────────

# Database
DB_PATH=/app/db/aquasynex.db

# Storage directories (mapped to Docker volumes)
DATA_DIR=/app/data
MODELS_DIR=/app/models

# API settings
ALLOWED_ORIGINS=http://localhost:3000
MAX_UPLOAD_SIZE_BYTES=2147483648

# ML settings
DEFAULT_MODEL_ID=isolation_forest_v1
DEFAULT_MODEL_VERSION=1.0.0
DEFAULT_TOP_EXPLANATIONS=5
DEFAULT_MAX_ENTITIES=10000

# Logging
LOG_LEVEL=INFO

# ── Frontend Build Configuration ───────────────────────────────

# Backend API URL (used at build time by Vite)
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## Environment Variable Rules

1. **Never commit `.env` files** — only `.env.example`.
2. **Frontend variables** prefixed with `VITE_` are embedded at build time (Vite convention). They are visible in the browser build — never put secrets there.
3. **Backend variables** are runtime configuration — loaded from environment or `.env` file.
4. **All paths** must work within Docker container filesystem layout.
5. **No secret values** in any of the above variables — authentication tokens, API keys, etc. would be added to a separate secrets section (`DECISION REQUIRED`).

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner + Frontend Owner*

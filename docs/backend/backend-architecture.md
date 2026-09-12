# Backend Architecture

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

**Status**: `PLANNED`

---

## 1. Application Structure

```
backend/
├── main.py                    # FastAPI app entry point
├── config.py                  # Settings from environment variables
├── dependencies.py            # Shared FastAPI dependencies (DuckDB connection, etc.)
├── api/
│   ├── __init__.py
│   ├── health.py              # GET /api/health
│   ├── datasets.py            # Dataset CRUD and upload
│   ├── analyses.py            # Analysis run management
│   ├── transactions.py        # Transaction queries
│   ├── addresses.py           # Address queries
│   ├── graph.py               # Graph export
│   ├── results.py             # ML result queries
│   └── models.py              # Available ML models
├── services/
│   ├── dataset_service.py     # Dataset management logic
│   ├── analysis_service.py    # Analysis orchestration
│   ├── pipeline_service.py    # ML pipeline invocation
│   ├── graph_service.py       # Graph query and export
│   └── result_service.py      # ML result retrieval
├── db/
│   ├── connection.py          # DuckDB connection management
│   ├── migrations.py          # Schema creation and migrations
│   └── queries/
│       ├── datasets.py
│       ├── transactions.py
│       ├── addresses.py
│       └── results.py
├── schemas/
│   ├── requests.py            # Pydantic request models
│   ├── responses.py           # Pydantic response models
│   └── ml_result.py           # ML result schema (from ML output contract)
└── utils/
    ├── errors.py              # Custom exception classes
    ├── pagination.py          # Pagination utilities
    └── converters.py          # BTC/satoshi converters, datetime formatters
```

> **Status**: Directory structure is `PLANNED`. Create it when implementation begins.

---

## 2. FastAPI Application

```python
# main.py (proposed)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AquaSynex Bitcoin Analysis API",
    version="1.0.0",
    description="SIH26146 – AI-Powered Bitcoin Transaction Analysis"
)

# CORS for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api")
app.include_router(datasets_router, prefix="/api/datasets")
app.include_router(analyses_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(addresses_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(results_router, prefix="/api")
app.include_router(models_router, prefix="/api")
```

---

## 3. Service Layer

Each API module delegates business logic to a service class. The service layer:
- Does not directly handle HTTP requests/responses
- Calls database queries
- Calls the ML pipeline
- Returns domain objects (Pydantic models)

The API module handles:
- Dependency injection
- Request validation
- Response serialization
- Error mapping

---

## 4. DuckDB Connection Management

DuckDB opens one connection per process. For FastAPI:

```python
# dependencies.py
import duckdb
from functools import lru_cache

@lru_cache(maxsize=1)
def get_db_connection():
    conn = duckdb.connect(database=settings.DB_PATH)
    # Create tables if not exists (on startup)
    run_migrations(conn)
    return conn

def get_db():
    return get_db_connection()
```

**Thread safety**: DuckDB is not thread-safe for parallel writes. Use a threading lock for write operations if the backend receives concurrent analysis requests. `DECISION REQUIRED`.

---

## 5. Error Handling Middleware

A global exception handler converts Python exceptions to the standard error envelope:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Map known exceptions to error codes
    # Return standardized error response
```

See [error-handling.md](./error-handling.md) for all error codes.

---

## 6. BTC Value Conversions

The backend `converters.py` module provides:

```python
def satoshi_to_btc_str(satoshi: int | None) -> str | None:
    """Convert satoshi integer to 8-decimal BTC string for API responses."""
    if satoshi is None:
        return None
    return f"{satoshi / 100_000_000:.8f}"

def btc_str_to_satoshi(btc_str: str) -> int:
    """Convert BTC string to satoshi integer for internal processing."""
    from decimal import Decimal
    return int(Decimal(btc_str) * 100_000_000)
```

All API responses must use `satoshi_to_btc_str()` for BTC value fields. **Never return raw satoshi integers as BTC float values.**

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner*
*References: [api-specification.md](./api-specification.md) | [duckdb-schema.md](./duckdb-schema.md)*

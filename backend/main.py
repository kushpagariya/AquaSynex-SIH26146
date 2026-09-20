"""FastAPI application entry point for AquaSynex Backend.

SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic.
Authoritative reference: docs/backend/backend-architecture.md
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import time
from typing import AsyncGenerator
import uuid
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.api.addresses import router as addresses_router
from backend.api.alerts import router as alerts_router
from backend.api.analyses import router as analyses_router
from backend.api.datasets import router as datasets_router
from backend.api.graph import router as graph_router
from backend.api.health import router as health_router
from backend.api.models import router as models_router
from backend.api.results import router as results_router
from backend.api.transactions import router as transactions_router
from backend.config import settings
from backend.db.connection import close_db, init_db
from backend.schemas.common import ApiError, ApiMeta, ApiResponse
from backend.utils.errors import AppError
from backend.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager initializing and cleaning up resources."""
    logger.info("Starting AquaSynex Backend API...")
    init_db()
    yield
    logger.info("Shutting down AquaSynex Backend API...")
    close_db()


app = FastAPI(
    title="AquaSynex Bitcoin Analysis API",
    version="1.0.0",
    description="SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID and timing middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


# ── Global Exception Handlers ──────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom application exceptions using canonical error envelope."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.warning(f"[{exc.code}] {exc.message} (requestId: {request_id})")

    error_response = ApiResponse(
        success=False,
        error=ApiError(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
        meta=ApiMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(by_alias=True),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic/FastAPI request validation errors."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "constraint": err.get("msg", "Validation failed"),
            "type": err.get("type", "value_error"),
        })

    logger.warning(f"[VALIDATION_ERROR] Request validation failed: {errors} (requestId: {request_id})")

    error_response = ApiResponse(
        success=False,
        error=ApiError(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        ),
        meta=ApiMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(by_alias=True),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    code_map = {
        404: "NOT_FOUND",
        400: "VALIDATION_ERROR",
        403: "FORBIDDEN",
        401: "UNAUTHORIZED",
        409: "CONFLICT",
        413: "FILE_TOO_LARGE",
        503: "SERVICE_UNAVAILABLE",
    }
    error_code = code_map.get(exc.status_code, "INTERNAL_ERROR")

    error_response = ApiResponse(
        success=False,
        error=ApiError(
            code=error_code,
            message=str(exc.detail),
        ),
        meta=ApiMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        ),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(by_alias=True),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler preventing raw stack traces from leaking to clients."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(f"Unhandled exception occurred (requestId: {request_id}): {exc}")

    error_response = ApiResponse(
        success=False,
        error=ApiError(
            code="INTERNAL_ERROR",
            message="An unexpected internal error occurred. Please check server logs.",
            details={},
        ),
        meta=ApiMeta(
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=request_id,
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(by_alias=True),
    )


# ── Register Routers ───────────────────────────────────────────

app.include_router(health_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(analyses_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(addresses_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(results_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(models_router, prefix="/api")

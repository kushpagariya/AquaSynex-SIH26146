"""System health check endpoint."""

import time
from typing import Any, Dict
from fastapi import APIRouter, Depends, Response, status
import duckdb
from backend.config import settings
from backend.db.connection import get_db_connection
from backend.dependencies import get_db
from backend.schemas.common import ApiMeta, ApiResponse


router = APIRouter(tags=["Health"])

START_TIME = time.time()


@router.get("/health", response_model=ApiResponse[Dict[str, Any]])
def get_health(response: Response, db: duckdb.DuckDBPyConnection = Depends(get_db)) -> ApiResponse[Dict[str, Any]]:
    """System health check endpoint for Docker health checks and readiness verification."""
    db_status = "connected"
    try:
        db.execute("SELECT 1").fetchone()
    except Exception:
        db_status = "disconnected"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    uptime_seconds = int(time.time() - START_TIME)

    health_data = {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "version": "1.0.0",
        "databaseStatus": db_status,
        "modelsAvailable": [settings.DEFAULT_MODEL_ID],
        "uptime": uptime_seconds,
    }

    return ApiResponse(
        success=(db_status == "connected"),
        data=health_data,
        meta=ApiMeta(),
    )

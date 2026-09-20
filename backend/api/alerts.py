"""Alert Management System API routes."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_alert_service
from backend.schemas.alerts import (
    AlertDetail,
    AlertPriorityUpdate,
    AlertsSummaryResponse,
    AlertStatusUpdate,
    AlertSummary,
)
from backend.schemas.common import ApiMeta, ApiResponse, PaginationMeta
from backend.services.alert_service import AlertService


router = APIRouter(tags=["Alerts"])


@router.get("/alerts", response_model=ApiResponse[List[AlertSummary]])
def list_alerts(
    analysisId: Optional[str] = Query(default=None, description="Filter by analysis run ID"),
    datasetId: Optional[str] = Query(default=None, description="Filter by dataset ID"),
    status: Optional[str] = Query(default=None, description="Filter by status (active, inactive, NEW, etc.)"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (critical, high, medium, low)"),
    alertType: Optional[str] = Query(default=None, description="Filter by alert type"),
    priority: Optional[str] = Query(default=None, description="Filter by priority (P1, P2, P3, P4)"),
    minRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum risk score"),
    search: Optional[str] = Query(default=None, description="Free text search on entity, TXID, or reason"),
    page: int = Query(default=1, ge=1, description="Page number"),
    pageSize: int = Query(default=50, ge=1, le=500, description="Items per page"),
    sortBy: str = Query(default="riskScore", description="Sort field (riskScore, createdAt, priority, severity)"),
    sortDir: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
    alert_service: AlertService = Depends(get_alert_service),
) -> ApiResponse[List[AlertSummary]]:
    """List alerts with filtering, search, and pagination."""
    items, pagination_meta = alert_service.list_alerts(
        analysis_id=analysisId,
        dataset_id=datasetId,
        status=status,
        severity=severity,
        alert_type=alertType,
        priority=priority,
        min_risk_score=minRiskScore,
        search=search,
        page=page,
        page_size=pageSize,
        sort_by=sortBy,
        sort_dir=sortDir,
    )
    return ApiResponse(
        success=True,
        data=[AlertSummary(**item) for item in items],
        meta=ApiMeta(pagination=PaginationMeta(**pagination_meta)),
    )


@router.get("/alerts/summary", response_model=ApiResponse[AlertsSummaryResponse])
def get_alerts_summary(
    analysisId: Optional[str] = Query(default=None, description="Analysis ID"),
    datasetId: Optional[str] = Query(default=None, description="Dataset ID"),
    alert_service: AlertService = Depends(get_alert_service),
) -> ApiResponse[AlertsSummaryResponse]:
    """Get aggregated alert metrics including active and total counts."""
    summary = alert_service.get_alerts_summary(analysis_id=analysisId, dataset_id=datasetId)
    return ApiResponse(
        success=True,
        data=AlertsSummaryResponse(**summary),
        meta=ApiMeta(),
    )


@router.post("/alerts/generate", response_model=ApiResponse[List[Dict[str, Any]]])
def generate_alerts(
    analysisId: str = Query(..., description="Analysis ID to generate alerts for"),
    datasetId: Optional[str] = Query(default=None, description="Dataset ID"),
    alert_service: AlertService = Depends(get_alert_service),
) -> ApiResponse[List[Dict[str, Any]]]:
    """Manually trigger or backfill alert generation for an analysis run."""
    generated = alert_service.generate_alerts_for_analysis(analysis_id=analysisId, dataset_id=datasetId)
    return ApiResponse(
        success=True,
        data=generated,
        meta=ApiMeta(),
    )


@router.get("/alerts/{alertId}", response_model=ApiResponse[AlertDetail])
def get_alert_detail(
    alertId: str,
    alert_service: AlertService = Depends(get_alert_service),
) -> ApiResponse[AlertDetail]:
    """Get full details and evidence for a single alert."""
    alert = alert_service.get_alert(alertId)
    return ApiResponse(
        success=True,
        data=AlertDetail(**alert),
        meta=ApiMeta(),
    )


@router.patch("/alerts/{alertId}/status", response_model=ApiResponse[AlertDetail])
def update_alert_status(
    alertId: str,
    body: AlertStatusUpdate,
    alert_service: AlertService = Depends(get_alert_service),
) -> ApiResponse[AlertDetail]:
    """Update persistent alert status (NEW, ACKNOWLEDGED, INVESTIGATING, ESCALATED, RESOLVED, DISMISSED)."""
    updated = alert_service.update_status(alertId, body.status)
    return ApiResponse(
        success=True,
        data=AlertDetail(**updated),
        meta=ApiMeta(),
    )


@router.patch("/alerts/{alertId}/priority", response_model=ApiResponse[AlertDetail])
def update_alert_priority(
    alertId: str,
    body: AlertPriorityUpdate,
    alert_service: AlertService = Depends(get_alert_service),
) -> ApiResponse[AlertDetail]:
    """Update alert priority (P1, P2, P3, P4)."""
    updated = alert_service.update_priority(alertId, body.priority)
    return ApiResponse(
        success=True,
        data=AlertDetail(**updated),
        meta=ApiMeta(),
    )

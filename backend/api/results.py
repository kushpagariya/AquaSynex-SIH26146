"""ML Prediction results and explainability routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_result_service
from backend.schemas.common import ApiMeta, ApiResponse, PaginationMeta
from backend.schemas.ml_results import MLResultDetail, MLResultSummary
from backend.services.result_service import ResultService


router = APIRouter(tags=["Results"])


@router.get("/analyses/{analysisId}/results", response_model=ApiResponse[List[MLResultSummary]])
def list_analysis_results(
    analysisId: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    pageSize: int = Query(default=50, ge=1, le=500, description="Items per page"),
    sortBy: str = Query(default="riskScore", description="Sort field"),
    sortDir: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
    riskLevel: Optional[str] = Query(default=None, description="Risk level filter"),
    minRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum risk score"),
    entityType: Optional[str] = Query(default=None, description="Entity type filter (address, transaction)"),
    result_service: ResultService = Depends(get_result_service),
) -> ApiResponse[List[MLResultSummary]]:
    """List ML predictions for an analysis run."""
    items, pagination_meta = result_service.list_results(
        analysis_id=analysisId,
        page=page,
        page_size=pageSize,
        sort_by=sortBy,
        sort_dir=sortDir,
        risk_level=riskLevel,
        min_risk_score=minRiskScore,
        entity_type=entityType,
    )
    return ApiResponse(
        success=True,
        data=[MLResultSummary(**item) for item in items],
        meta=ApiMeta(pagination=PaginationMeta(**pagination_meta)),
    )


@router.get("/analyses/{analysisId}/results/{entityId}", response_model=ApiResponse[MLResultDetail])
def get_entity_result_detail(
    analysisId: str,
    entityId: str,
    result_service: ResultService = Depends(get_result_service),
) -> ApiResponse[MLResultDetail]:
    """Get full ML result for one entity including SHAP explanations."""
    result = result_service.get_result(analysis_id=analysisId, entity_id=entityId)
    return ApiResponse(
        success=True,
        data=MLResultDetail(**result),
        meta=ApiMeta(),
    )

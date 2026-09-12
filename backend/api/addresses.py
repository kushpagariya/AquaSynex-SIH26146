"""Address and entity query routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_address_service
from backend.schemas.addresses import AddressDetail, AddressSummary
from backend.schemas.common import ApiMeta, ApiResponse, PaginationMeta
from backend.services.address_service import AddressService


router = APIRouter(tags=["Addresses"])


@router.get("/datasets/{datasetId}/addresses", response_model=ApiResponse[List[AddressSummary]])
def list_addresses(
    datasetId: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    pageSize: int = Query(default=50, ge=1, le=500, description="Items per page"),
    sortBy: str = Query(default="transactionCount", description="Sort field"),
    sortDir: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
    riskLevel: Optional[str] = Query(default=None, description="Risk level filter (low, medium, high, critical)"),
    minRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum risk score"),
    maxRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Maximum risk score"),
    analysisId: Optional[str] = Query(default=None, description="Filter to ML results from this analysis"),
    address_service: AddressService = Depends(get_address_service),
) -> ApiResponse[List[AddressSummary]]:
    """List addresses with risk scores and behavioral summary."""
    items, pagination_meta = address_service.list_addresses(
        dataset_id=datasetId,
        page=page,
        page_size=pageSize,
        sort_by=sortBy,
        sort_dir=sortDir,
        risk_level=riskLevel,
        min_risk_score=minRiskScore,
        max_risk_score=maxRiskScore,
        analysis_id=analysisId,
    )
    return ApiResponse(
        success=True,
        data=[AddressSummary(**item) for item in items],
        meta=ApiMeta(pagination=PaginationMeta(**pagination_meta)),
    )


@router.get("/addresses/{addressId}", response_model=ApiResponse[AddressDetail])
def get_address_profile(
    addressId: str,
    analysisId: Optional[str] = Query(default=None, description="Analysis ID for joined ML results"),
    address_service: AddressService = Depends(get_address_service),
) -> ApiResponse[AddressDetail]:
    """Get full address profile including ML explanations and graph evidence."""
    profile = address_service.get_address(addressId, analysis_id=analysisId)
    return ApiResponse(
        success=True,
        data=AddressDetail(**profile),
        meta=ApiMeta(),
    )

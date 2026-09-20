"""Network Intelligence API routes for offline GeoIP/ASN map visualization."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_network_service
from backend.schemas.common import ApiMeta, ApiResponse
from backend.schemas.network import NetworkMapResponse
from backend.services.network_service import NetworkService


router = APIRouter(tags=["Network"])


@router.get("/datasets/{datasetId}/network/map", response_model=ApiResponse[NetworkMapResponse])
def get_dataset_network_map(
    datasetId: str,
    analysisId: Optional[str] = Query(default=None, description="Optional analysis ID context"),
    network_service: NetworkService = Depends(get_network_service),
) -> ApiResponse[NetworkMapResponse]:
    """Retrieve aggregated network endpoints enriched with offline GeoIP and ASN metadata."""
    map_data = network_service.get_network_map(
        dataset_id=datasetId,
        analysis_id=analysisId,
    )
    return ApiResponse(
        success=True,
        data=NetworkMapResponse(**map_data),
        meta=ApiMeta(),
    )


@router.get("/network/map", response_model=ApiResponse[NetworkMapResponse])
def get_network_map(
    datasetId: str = Query(..., description="Target dataset ID"),
    analysisId: Optional[str] = Query(default=None, description="Optional analysis ID context"),
    network_service: NetworkService = Depends(get_network_service),
) -> ApiResponse[NetworkMapResponse]:
    """Alternative query-parameter route for network map data matching API envelope conventions."""
    map_data = network_service.get_network_map(
        dataset_id=datasetId,
        analysis_id=analysisId,
    )
    return ApiResponse(
        success=True,
        data=NetworkMapResponse(**map_data),
        meta=ApiMeta(),
    )

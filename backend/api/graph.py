"""Graph visualization and export routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_graph_service
from backend.schemas.common import ApiMeta, ApiResponse
from backend.schemas.graph import GraphExport
from backend.services.graph_service import GraphService


router = APIRouter(tags=["Graph"])


@router.get("/analyses/{analysisId}/graph", response_model=ApiResponse[GraphExport])
def get_analysis_graph(
    analysisId: str,
    minRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum node risk score"),
    maxNodes: int = Query(default=500, ge=1, le=5000, description="Max nodes to include"),
    includeNeighbors: bool = Query(default=True, description="Include 1-hop neighbors"),
    graph_service: GraphService = Depends(get_graph_service),
) -> ApiResponse[GraphExport]:
    """Return the full transaction graph (nodes + edges) for Cytoscape.js visualization."""
    graph_data = graph_service.get_analysis_graph(
        analysis_id=analysisId,
        min_risk_score=minRiskScore,
        max_nodes=maxNodes,
        include_neighbors=includeNeighbors,
    )
    return ApiResponse(
        success=True,
        data=GraphExport(**graph_data),
        meta=ApiMeta(),
    )


@router.get("/addresses/{addressId}/graph", response_model=ApiResponse[GraphExport])
def get_address_subgraph(
    addressId: str,
    hops: int = Query(default=2, ge=1, le=3, description="Neighborhood depth (1-3 hops)"),
    analysisId: Optional[str] = Query(default=None, description="Analysis ID for risk scoring"),
    graph_service: GraphService = Depends(get_graph_service),
) -> ApiResponse[GraphExport]:
    """Return the N-hop neighborhood subgraph around a specific address."""
    graph_data = graph_service.get_address_subgraph(
        address_id=addressId,
        hops=hops,
        analysis_id=analysisId,
    )
    return ApiResponse(
        success=True,
        data=GraphExport(**graph_data),
        meta=ApiMeta(),
    )

"""Graph visualization and export routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_graph_service
from backend.schemas.common import ApiMeta, ApiResponse
from backend.schemas.graph import GraphExport, GraphNeighborhoodResponse
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


@router.get("/graph/neighborhood", response_model=ApiResponse[GraphNeighborhoodResponse])
def get_graph_neighborhood(
    entityId: str = Query(..., description="Target transaction ID or address"),
    analysisId: Optional[str] = Query(default=None, description="Analysis ID for context"),
    datasetId: Optional[str] = Query(default=None, description="Dataset ID for context"),
    entityType: Optional[str] = Query(default=None, description="Optional entity type hint ('transaction' or 'address')"),
    depth: int = Query(default=2, ge=1, le=3, description="Expansion depth (1-3 hops)"),
    highRiskOnly: bool = Query(default=False, description="Filter to high-risk entities (risk_score >= 0.50)"),
    graph_service: GraphService = Depends(get_graph_service),
) -> ApiResponse[GraphNeighborhoodResponse]:
    """Return the multi-hop bipartite neighborhood subgraph around a transaction or address."""
    graph_data = graph_service.get_neighborhood(
        entity_id=entityId,
        analysis_id=analysisId,
        dataset_id=datasetId,
        entity_type=entityType,
        depth=depth,
        high_risk_only=highRiskOnly,
    )
    return ApiResponse(
        success=True,
        data=GraphNeighborhoodResponse(**graph_data),
        meta=ApiMeta(),
    )

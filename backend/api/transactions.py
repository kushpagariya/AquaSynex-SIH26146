"""Transaction query routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from backend.dependencies import get_transaction_service
from backend.schemas.common import ApiMeta, ApiResponse, PaginationMeta
from backend.schemas.transactions import TransactionDetail, TransactionSummary
from backend.services.transaction_service import TransactionService


router = APIRouter(tags=["Transactions"])


@router.get("/datasets/{datasetId}/transactions", response_model=ApiResponse[List[TransactionSummary]])
def list_transactions(
    datasetId: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    pageSize: int = Query(default=50, ge=1, le=500, description="Items per page"),
    sortBy: str = Query(default="timestamp", description="Sort field"),
    sortDir: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
    riskLevel: Optional[str] = Query(default=None, description="Risk level filter (low, medium, high, critical)"),
    minRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum risk score"),
    maxRiskScore: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Maximum risk score"),
    fromTimestamp: Optional[str] = Query(default=None, description="ISO 8601 start timestamp"),
    toTimestamp: Optional[str] = Query(default=None, description="ISO 8601 end timestamp"),
    minValueBtc: Optional[str] = Query(default=None, description="Minimum total value in BTC decimal string"),
    maxValueBtc: Optional[str] = Query(default=None, description="Maximum total value in BTC decimal string"),
    analysisId: Optional[str] = Query(default=None, description="Filter to ML results from this analysis"),
    ip: Optional[str] = Query(default=None, description="Filter transactions associated with an IP address"),
    address: Optional[str] = Query(default=None, description="Filter transactions involving a Bitcoin address"),
    txid: Optional[str] = Query(default=None, description="Filter to a specific transaction ID"),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> ApiResponse[List[TransactionSummary]]:
    """List transactions in a dataset with filtering, risk scores, and pagination."""
    items, pagination_meta = transaction_service.list_transactions(
        dataset_id=datasetId,
        page=page,
        page_size=pageSize,
        sort_by=sortBy,
        sort_dir=sortDir,
        risk_level=riskLevel,
        min_risk_score=minRiskScore,
        max_risk_score=maxRiskScore,
        from_timestamp=fromTimestamp,
        to_timestamp=toTimestamp,
        min_value_btc=minValueBtc,
        max_value_btc=maxValueBtc,
        analysis_id=analysisId,
        ip=ip,
        address=address,
        txid=txid,
    )
    return ApiResponse(
        success=True,
        data=[TransactionSummary(**item) for item in items],
        meta=ApiMeta(pagination=PaginationMeta(**pagination_meta)),
    )


@router.get("/transactions/{transactionId}", response_model=ApiResponse[TransactionDetail])
def get_transaction_detail(
    transactionId: str,
    analysisId: Optional[str] = Query(default=None, description="Analysis ID for joined ML results"),
    transaction_service: TransactionService = Depends(get_transaction_service),
) -> ApiResponse[TransactionDetail]:
    """Get full transaction detail including inputs, outputs, and ML prediction."""
    tx_detail = transaction_service.get_transaction(transactionId, analysisId)
    return ApiResponse(
        success=True,
        data=TransactionDetail(**tx_detail),
        meta=ApiMeta(),
    )

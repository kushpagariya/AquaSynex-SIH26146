"""Analysis run status and inspection routes."""

from fastapi import APIRouter, Depends
from backend.dependencies import get_analysis_service
from backend.schemas.analyses import AnalysisSummary
from backend.schemas.common import ApiMeta, ApiResponse
from backend.services.analysis_service import AnalysisService


router = APIRouter(tags=["Analyses"])


@router.get("/analyses/{analysisId}", response_model=ApiResponse[AnalysisSummary])
def get_analysis_status(
    analysisId: str,
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[AnalysisSummary]:
    """Get status and summary of an analysis run."""
    analysis = analysis_service.get_analysis(analysisId)
    return ApiResponse(
        success=True,
        data=AnalysisSummary(**analysis),
        meta=ApiMeta(),
    )

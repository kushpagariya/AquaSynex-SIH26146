"""Dataset and dataset-analysis routes."""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Response, UploadFile, status
from backend.dependencies import get_analysis_service, get_dataset_service
from backend.schemas.analyses import AnalysisRequest, AnalysisSummary, AnalysisTriggerResponse
from backend.schemas.common import ApiMeta, ApiResponse, PaginationMeta
from backend.schemas.datasets import DatasetDeleteResponse, DatasetDetail, DatasetSummary, DatasetUploadResponse
from backend.services.analysis_service import AnalysisService
from backend.services.dataset_service import DatasetService
from backend.utils.errors import ValidationError


router = APIRouter(tags=["Datasets"])


@router.get("/datasets", response_model=ApiResponse[List[DatasetSummary]])
def list_datasets(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(default=50, ge=1, le=500, description="Items per page"),
    sortBy: str = Query(default="uploadedAt", description="Field to sort by"),
    sortDir: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction"),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> ApiResponse[List[DatasetSummary]]:
    """List all registered datasets with pagination."""
    items, pagination_meta = dataset_service.list_datasets(
        page=page,
        page_size=pageSize,
        sort_by=sortBy,
        sort_dir=sortDir,
    )
    return ApiResponse(
        success=True,
        data=[DatasetSummary(**item) for item in items],
        meta=ApiMeta(pagination=PaginationMeta(**pagination_meta)),
    )


@router.post("/datasets/upload", response_model=ApiResponse[DatasetUploadResponse], status_code=status.HTTP_202_ACCEPTED)
async def upload_dataset(
    file: UploadFile = File(..., description="Dataset file (CSV, JSON, JSONL, Parquet)"),
    name: str = Form(..., description="User-provided dataset name"),
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> ApiResponse[DatasetUploadResponse]:
    """Upload and ingest a dataset file."""
    if not file.filename:
        raise ValidationError("Uploaded file must have a valid filename", details={"field": "file"})

    dataset = dataset_service.upload_dataset(
        file_obj=file.file,
        filename=file.filename,
        name=name,
        content_length=file.size,
    )
    return ApiResponse(
        success=True,
        data=DatasetUploadResponse(
            dataset_id=dataset["dataset_id"],
            name=dataset["name"],
            status=dataset["status"],
            uploaded_at=dataset["uploaded_at"],
        ),
        meta=ApiMeta(),
    )


@router.get("/datasets/{datasetId}", response_model=ApiResponse[DatasetDetail])
def get_dataset_detail(
    datasetId: str,
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> ApiResponse[DatasetDetail]:
    """Get dataset metadata and validation summary."""
    dataset = dataset_service.get_dataset(datasetId)
    return ApiResponse(
        success=True,
        data=DatasetDetail(**dataset),
        meta=ApiMeta(),
    )


@router.delete("/datasets/{datasetId}", response_model=ApiResponse[DatasetDeleteResponse])
def delete_dataset(
    datasetId: str,
    dataset_service: DatasetService = Depends(get_dataset_service),
) -> ApiResponse[DatasetDeleteResponse]:
    """Delete a dataset and all associated analysis records."""
    deleted = dataset_service.delete_dataset(datasetId)
    return ApiResponse(
        success=True,
        data=DatasetDeleteResponse(deleted=deleted),
        meta=ApiMeta(),
    )


@router.post("/datasets/{datasetId}/analyses", response_model=ApiResponse[AnalysisTriggerResponse], status_code=status.HTTP_202_ACCEPTED)
def trigger_analysis(
    datasetId: str,
    payload: Optional[AnalysisRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[AnalysisTriggerResponse]:
    """Trigger a new asynchronous analysis run on a dataset."""
    req = payload or AnalysisRequest()
    analysis = analysis_service.trigger_analysis(
        dataset_id=datasetId,
        model_id=req.model_id,
        model_version=req.model_version,
        config_dict=req.config,
        background_tasks=background_tasks,
    )
    return ApiResponse(
        success=True,
        data=AnalysisTriggerResponse(
            analysis_id=analysis["analysis_id"],
            dataset_id=analysis["dataset_id"],
            status=analysis["status"],
            started_at=analysis["started_at"],
        ),
        meta=ApiMeta(),
    )


@router.get("/datasets/{datasetId}/analyses", response_model=ApiResponse[List[AnalysisSummary]])
def list_analyses_for_dataset(
    datasetId: str,
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[List[AnalysisSummary]]:
    """List all analysis runs for a dataset."""
    items = analysis_service.list_analyses_for_dataset(datasetId)
    return ApiResponse(
        success=True,
        data=[AnalysisSummary(**item) for item in items],
        meta=ApiMeta(),
    )

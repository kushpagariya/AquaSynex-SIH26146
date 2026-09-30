"""Model registry routes."""

from typing import Any, Dict, List
from fastapi import APIRouter
from backend.schemas.common import ApiMeta, ApiResponse
from backend.schemas.models import ModelInfo
from backend.services.model_service import get_available_models, get_model_metadata


router = APIRouter(tags=["Models"])


@router.get("/models/metadata", response_model=ApiResponse[Dict[str, Any]])
def get_metadata() -> ApiResponse[Dict[str, Any]]:
    """Retrieve frozen production ML model metadata and specifications."""
    metadata = get_model_metadata()
    return ApiResponse(
        success=True,
        data=metadata,
        meta=ApiMeta(),
    )


@router.get("/models", response_model=ApiResponse[List[ModelInfo]])
def list_models() -> ApiResponse[List[ModelInfo]]:
    """List available ML models."""
    models = get_available_models()
    return ApiResponse(
        success=True,
        data=models,
        meta=ApiMeta(),
    )


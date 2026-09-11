"""Model registry routes."""

from typing import List
from fastapi import APIRouter
from backend.schemas.common import ApiMeta, ApiResponse
from backend.schemas.models import ModelInfo
from backend.services.model_service import get_available_models


router = APIRouter(tags=["Models"])


@router.get("/models", response_model=ApiResponse[List[ModelInfo]])
def list_models() -> ApiResponse[List[ModelInfo]]:
    """List available ML models."""
    models = get_available_models()
    return ApiResponse(
        success=True,
        data=models,
        meta=ApiMeta(),
    )

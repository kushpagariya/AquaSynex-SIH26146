"""Model registry routes."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter
from backend.config import settings
from backend.schemas.common import ApiMeta, ApiResponse
from backend.schemas.models import ModelInfo


router = APIRouter(tags=["Models"])


@router.get("/models", response_model=ApiResponse[List[ModelInfo]])
def list_models() -> ApiResponse[List[ModelInfo]]:
    """List available ML models."""
    models: List[ModelInfo] = [
        ModelInfo(
            model_id=settings.DEFAULT_MODEL_ID,
            model_version=settings.DEFAULT_MODEL_VERSION,
            algorithm="IsolationForest",
            model_type="anomaly_detection",
            feature_schema_version="1.0.0",
            training_completed_at=datetime(2026, 9, 11, 10, 0, 0, tzinfo=timezone.utc),
        )
    ]

    # Dynamically scan MODELS_DIR for additional models if present
    models_dir = Path(settings.MODELS_DIR)
    if models_dir.exists():
        for model_path in models_dir.iterdir():
            if model_path.is_dir() and model_path.name != settings.DEFAULT_MODEL_ID:
                for ver_path in model_path.iterdir():
                    if ver_path.is_dir():
                        models.append(
                            ModelInfo(
                                model_id=model_path.name,
                                model_version=ver_path.name,
                                algorithm="XGBoost" if "xgb" in model_path.name.lower() else "IsolationForest",
                                model_type="classification" if "xgb" in model_path.name.lower() else "anomaly_detection",
                                feature_schema_version="1.0.0",
                            )
                        )

    return ApiResponse(
        success=True,
        data=models,
        meta=ApiMeta(),
    )

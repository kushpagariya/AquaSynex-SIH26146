"""Model registry and discovery service providing unified model availability."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from backend.config import settings
from backend.schemas.models import ModelInfo


def get_available_models() -> List[ModelInfo]:
    """Discover available ML models from configuration and model artifacts directory."""
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
    return models


def is_model_available(model_id: str, model_version: Optional[str] = None) -> bool:
    """Check whether a model and optional version is recognized in the model registry."""
    available = get_available_models()
    for m in available:
        if m.model_id == model_id:
            if model_version is None or m.model_version == model_version:
                return True
    return False

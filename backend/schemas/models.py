"""Model registry schemas matching docs/backend/request-response-schemas.md."""

from datetime import datetime
from typing import Optional
from backend.schemas.common import CamelModel


class ModelInfo(CamelModel):
    model_id: str
    model_version: str
    algorithm: str
    model_type: str = "anomaly_detection"  # 'anomaly_detection' | 'classification'
    feature_schema_version: str = "1.0.0"
    training_completed_at: Optional[datetime] = None
    description: Optional[str] = None
    is_executable: bool = True

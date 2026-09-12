"""Dataset schemas matching docs/backend/request-response-schemas.md."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.schemas.common import CamelModel


class DatasetSummary(CamelModel):
    dataset_id: str
    name: str
    file_name: str
    format: str
    size_bytes: int
    row_count: Optional[int] = None
    status: str
    uploaded_at: datetime
    available_fields: List[str] = []


class DatasetDetail(DatasetSummary):
    canonical_tx_count: Optional[int] = None
    validation_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class DatasetUploadResponse(CamelModel):
    dataset_id: str
    name: str
    status: str
    uploaded_at: datetime


class DatasetDeleteResponse(CamelModel):
    deleted: bool

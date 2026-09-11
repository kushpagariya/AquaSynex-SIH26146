"""Analysis schemas matching docs/backend/request-response-schemas.md."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import Field
from backend.schemas.common import CamelModel


class AnalysisConfigSchema(CamelModel):
    max_entities: int = Field(default=10000, ge=1, le=1000000)
    top_explanations: int = Field(default=5, ge=1, le=20)
    compute_graph: bool = True
    graph_max_nodes: int = Field(default=100000, ge=1)
    random_state: int = 42


class AnalysisRequest(CamelModel):
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AnalysisSummary(CamelModel):
    analysis_id: str
    dataset_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    entity_count: Optional[int] = None
    high_risk_count: Optional[int] = None
    critical_risk_count: Optional[int] = None
    error_message: Optional[str] = None


class AnalysisTriggerResponse(CamelModel):
    analysis_id: str
    dataset_id: str
    status: str
    started_at: datetime

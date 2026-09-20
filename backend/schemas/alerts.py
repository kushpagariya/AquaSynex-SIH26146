"""Alerts request-response schemas matching DuckDB persistent alerts table."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.schemas.common import CamelModel


class AlertItem(CamelModel):
    alert_id: str
    analysis_id: str
    dataset_id: str
    entity_id: str
    entity_type: str
    transaction_id: Optional[str] = None
    alert_type: str
    severity: str
    priority: str
    risk_score: float
    behavior_type: Optional[str] = None
    trigger_source: Optional[str] = None
    trigger_reason: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

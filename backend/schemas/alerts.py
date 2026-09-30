"""Alert schemas for Alert Management System."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.schemas.common import CamelModel


class AlertSummary(CamelModel):
    alert_id: str
    analysis_id: str
    dataset_id: str
    fingerprint: str
    grouping_key: str
    transaction_id: Optional[str] = None
    entity_id: str
    entity_type: str
    alert_type: str
    severity: str
    priority: str
    risk_score: float
    behavior_type: Optional[str] = None
    trigger_source: str
    trigger_reason: str
    status: str
    created_at: datetime
    updated_at: datetime
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class AlertDetail(AlertSummary):
    pass


class AlertStatusUpdate(CamelModel):
    status: str


class AlertPriorityUpdate(CamelModel):
    priority: str


class AlertsSummaryResponse(CamelModel):
    total: int
    active: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_type: Dict[str, int]


# Compatibility alias for code expecting AlertItem
AlertItem = AlertSummary

"""Alert service managing alert queries, updates, and engine execution."""

from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.db.queries import alerts as alert_queries
from backend.db.queries import analyses as analysis_queries
from backend.services.alert_engine import AlertEngine


class AlertService:
    """Service providing alert query, state lifecycle, and generation operations."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.engine = AlertEngine(conn)

    def generate_alerts_for_analysis(
        self,
        analysis_id: str,
        dataset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run deterministic AlertEngine for an analysis run."""
        if not dataset_id:
            analysis = analysis_queries.get_analysis_by_id(self.conn, analysis_id)
            dataset_id = analysis["dataset_id"]
        return self.engine.generate_alerts_for_analysis(analysis_id, dataset_id)

    def list_alerts(
        self,
        analysis_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        priority: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "riskScore",
        sort_dir: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List alerts with filtering, sorting, and pagination."""
        return alert_queries.list_alerts(
            conn=self.conn,
            analysis_id=analysis_id,
            dataset_id=dataset_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
            priority=priority,
            min_risk_score=min_risk_score,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )

    def get_alert(self, alert_id: str) -> Dict[str, Any]:
        """Get single alert by ID."""
        return alert_queries.get_alert_by_id(self.conn, alert_id)

    def update_status(self, alert_id: str, status: str) -> Dict[str, Any]:
        """Update persistent alert status."""
        return alert_queries.update_alert_status(self.conn, alert_id, status)

    def update_priority(self, alert_id: str, priority: str) -> Dict[str, Any]:
        """Update alert priority."""
        return alert_queries.update_alert_priority(self.conn, alert_id, priority)

    def get_alerts_summary(
        self,
        analysis_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get aggregated alert metrics."""
        return alert_queries.get_alerts_summary(self.conn, analysis_id=analysis_id, dataset_id=dataset_id)

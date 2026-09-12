"""ML Results business service providing list and entity-level prediction queries."""

from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.db.queries import analyses as analysis_queries
from backend.db.queries import results as result_queries


class ResultService:
    """Service providing access to ML predictions, anomaly metrics, and SHAP explanations."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def list_results(
        self,
        analysis_id: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "riskScore",
        sort_dir: str = "desc",
        risk_level: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        entity_type: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List ML results for an analysis run."""
        analysis_queries.get_analysis_by_id(self.conn, analysis_id)

        return result_queries.list_ml_results(
            conn=self.conn,
            analysis_id=analysis_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            risk_level=risk_level,
            min_risk_score=min_risk_score,
            entity_type=entity_type,
        )

    def get_result(self, analysis_id: str, entity_id: str) -> Dict[str, Any]:
        """Get full ML result with explanations for a single entity."""
        return result_queries.get_ml_result_for_entity(
            conn=self.conn,
            analysis_id=analysis_id,
            entity_id=entity_id,
        )

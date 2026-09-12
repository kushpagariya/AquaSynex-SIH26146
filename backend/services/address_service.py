"""Address business service providing address listings and detailed behavioral profiles."""

from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.db.queries import addresses as address_queries
from backend.db.queries import datasets as dataset_queries


class AddressService:
    """Service providing access to derived address summaries and forensic profiles."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def list_addresses(
        self,
        dataset_id: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "transactionCount",
        sort_dir: str = "desc",
        risk_level: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        max_risk_score: Optional[float] = None,
        analysis_id: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List address records for a dataset with pagination and risk filters."""
        dataset_queries.get_dataset_by_id(self.conn, dataset_id)

        return address_queries.list_addresses(
            conn=self.conn,
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            risk_level=risk_level,
            min_risk_score=min_risk_score,
            max_risk_score=max_risk_score,
            analysis_id=analysis_id,
        )

    def get_address(
        self,
        address_id: str,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get full address profile including active days and ML explanations."""
        return address_queries.get_address_by_id(
            conn=self.conn,
            address_id=address_id,
            analysis_id=analysis_id,
        )

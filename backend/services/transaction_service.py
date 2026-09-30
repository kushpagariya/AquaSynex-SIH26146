"""Transaction business service handling filtering, sorting, and detail queries."""

from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.db.queries import datasets as dataset_queries
from backend.db.queries import transactions as transaction_queries


class TransactionService:
    """Service providing access to canonical transactions and full input/output details."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def list_transactions(
        self,
        dataset_id: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "timestamp",
        sort_dir: str = "desc",
        risk_level: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        max_risk_score: Optional[float] = None,
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
        min_value_btc: Optional[str] = None,
        max_value_btc: Optional[str] = None,
        analysis_id: Optional[str] = None,
        ip: Optional[str] = None,
        address: Optional[str] = None,
        txid: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List transactions for a dataset with filters and pagination."""
        # Ensure dataset exists
        dataset_queries.get_dataset_by_id(self.conn, dataset_id)

        return transaction_queries.list_transactions(
            conn=self.conn,
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            risk_level=risk_level,
            min_risk_score=min_risk_score,
            max_risk_score=max_risk_score,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            min_value_btc=min_value_btc,
            max_value_btc=max_value_btc,
            analysis_id=analysis_id,
            ip=ip,
            address=address,
            txid=txid,
        )

    def get_transaction(
        self,
        transaction_id: str,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get full transaction detail including inputs, outputs, and ML prediction."""
        return transaction_queries.get_transaction_by_id(
            conn=self.conn,
            transaction_id=transaction_id,
            analysis_id=analysis_id,
        )

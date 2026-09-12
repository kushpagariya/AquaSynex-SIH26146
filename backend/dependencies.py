"""FastAPI dependency injection provider for AquaSynex Backend."""

from typing import Generator
from fastapi import Depends
import duckdb
from backend.db.connection import get_db_connection
from backend.services.address_service import AddressService
from backend.services.analysis_service import AnalysisService
from backend.services.dataset_service import DatasetService
from backend.services.graph_service import GraphService
from backend.services.result_service import ResultService
from backend.services.transaction_service import TransactionService


def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Dependency yielding the shared DuckDB connection."""
    conn = get_db_connection()
    yield conn


def get_dataset_service(db: duckdb.DuckDBPyConnection = Depends(get_db)) -> DatasetService:
    return DatasetService(db)


def get_analysis_service(db: duckdb.DuckDBPyConnection = Depends(get_db)) -> AnalysisService:
    return AnalysisService(db)


def get_transaction_service(db: duckdb.DuckDBPyConnection = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


def get_address_service(db: duckdb.DuckDBPyConnection = Depends(get_db)) -> AddressService:
    return AddressService(db)


def get_graph_service(db: duckdb.DuckDBPyConnection = Depends(get_db)) -> GraphService:
    return GraphService(db)


def get_result_service(db: duckdb.DuckDBPyConnection = Depends(get_db)) -> ResultService:
    return ResultService(db)

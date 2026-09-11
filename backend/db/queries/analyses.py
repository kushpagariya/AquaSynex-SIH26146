"""DuckDB queries for analysis_runs table."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import duckdb
from backend.utils.errors import AnalysisNotFoundError


def insert_analysis_run(
    conn: duckdb.DuckDBPyConnection,
    analysis_id: str,
    dataset_id: str,
    status: str = "pending",
    model_id: Optional[str] = None,
    model_version: Optional[str] = None,
    feature_schema_version: Optional[str] = "1.0.0",
    config: Optional[Dict[str, Any]] = None,
    started_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Insert a new analysis run record."""
    started_at = started_at or datetime.now(timezone.utc)
    config_json = json.dumps(config) if config else None

    query = """
    INSERT INTO analysis_runs (
        analysis_id, dataset_id, status, started_at, model_id,
        model_version, feature_schema_version, config
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn.execute(
        query,
        [
            analysis_id,
            dataset_id,
            status,
            started_at,
            model_id,
            model_version,
            feature_schema_version,
            config_json,
        ],
    )
    return get_analysis_by_id(conn, analysis_id)


def get_analysis_by_id(conn: duckdb.DuckDBPyConnection, analysis_id: str) -> Dict[str, Any]:
    """Get single analysis run by ID."""
    query = "SELECT * FROM analysis_runs WHERE analysis_id = ?"
    rel = conn.execute(query, [analysis_id])
    row = rel.fetchone()
    if not row:
        raise AnalysisNotFoundError(analysis_id)

    col_names = [col[0] for col in rel.description]
    res = dict(zip(col_names, row))

    for json_col in ["config", "graph_summary"]:
        if res.get(json_col) and isinstance(res[json_col], str):
            try:
                res[json_col] = json.loads(res[json_col])
            except Exception:
                pass

    return res


def list_analyses_for_dataset(conn: duckdb.DuckDBPyConnection, dataset_id: str) -> List[Dict[str, Any]]:
    """List all analysis runs for a dataset ordered by started_at desc."""
    query = """
    SELECT * FROM analysis_runs
    WHERE dataset_id = ?
    ORDER BY started_at DESC
    """
    rel = conn.execute(query, [dataset_id])
    col_names = [col[0] for col in rel.description]

    items = []
    for row in rel.fetchall():
        record = dict(zip(col_names, row))
        for json_col in ["config", "graph_summary"]:
            if record.get(json_col) and isinstance(record[json_col], str):
                try:
                    record[json_col] = json.loads(record[json_col])
                except Exception:
                    pass
        items.append(record)

    return items


def update_analysis_status(
    conn: duckdb.DuckDBPyConnection,
    analysis_id: str,
    status: str,
    completed_at: Optional[datetime] = None,
    entity_count: Optional[int] = None,
    high_risk_count: Optional[int] = None,
    critical_risk_count: Optional[int] = None,
    error_message: Optional[str] = None,
    graph_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update status, counts, and completion time of an analysis run."""
    updates = ["status = ?"]
    params: List[Any] = [status]

    if completed_at is not None:
        updates.append("completed_at = ?")
        params.append(completed_at)
    if entity_count is not None:
        updates.append("entity_count = ?")
        params.append(entity_count)
    if high_risk_count is not None:
        updates.append("high_risk_count = ?")
        params.append(high_risk_count)
    if critical_risk_count is not None:
        updates.append("critical_risk_count = ?")
        params.append(critical_risk_count)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if graph_summary is not None:
        updates.append("graph_summary = ?")
        params.append(json.dumps(graph_summary))

    params.append(analysis_id)
    query = f"UPDATE analysis_runs SET {', '.join(updates)} WHERE analysis_id = ?"
    conn.execute(query, params)
    return get_analysis_by_id(conn, analysis_id)

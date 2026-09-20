"""Persistent Alerts query routes."""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
import duckdb
from backend.dependencies import get_db
from backend.schemas.alerts import AlertItem
from backend.schemas.common import ApiMeta, ApiResponse

router = APIRouter(tags=["Alerts"])


@router.get("/alerts", response_model=ApiResponse[List[AlertItem]])
def list_alerts(
    datasetId: Optional[str] = Query(default=None, description="Dataset ID filter"),
    analysisId: Optional[str] = Query(default=None, description="Analysis ID filter"),
    status: Optional[str] = Query(default=None, description="Status filter (active, new, investigating, resolved, etc.)"),
    entityId: Optional[str] = Query(default=None, description="Entity or transaction ID filter (comma-separated supported)"),
    entityType: Optional[str] = Query(default=None, description="Entity type filter (transaction, cluster, address)"),
    limit: int = Query(default=500, ge=1, le=2000, description="Max alerts to return"),
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
) -> ApiResponse[List[AlertItem]]:
    """Retrieve persistent alerts from DuckDB alerts table."""
    try:
        has_alerts = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'alerts'"
        ).fetchone()[0] > 0
        if not has_alerts:
            return ApiResponse(success=True, data=[], meta=ApiMeta())
    except Exception:
        return ApiResponse(success=True, data=[], meta=ApiMeta())

    where_clauses: List[str] = []
    params: List[Any] = []

    if datasetId:
        where_clauses.append("(dataset_id = ? OR dataset_id IS NULL)")
        params.append(datasetId)

    if analysisId:
        where_clauses.append("(analysis_id = ? OR analysis_id IS NULL)")
        params.append(analysisId)

    if status:
        if status.lower() == "active":
            where_clauses.append("UPPER(status) NOT IN ('RESOLVED', 'DISMISSED')")
        else:
            where_clauses.append("LOWER(status) = ?")
            params.append(status.lower())

    if entityId:
        entity_ids = [e.strip() for e in entityId.split(",") if e.strip()]
        if len(entity_ids) == 1:
            where_clauses.append("(entity_id = ? OR transaction_id = ?)")
            params.extend([entity_ids[0], entity_ids[0]])
        elif entity_ids:
            placeholders = ", ".join("?" for _ in entity_ids)
            where_clauses.append(f"(entity_id IN ({placeholders}) OR transaction_id IN ({placeholders}))")
            params.extend(entity_ids)
            params.extend(entity_ids)

    if entityType:
        where_clauses.append("LOWER(entity_type) = ?")
        params.append(entityType.lower())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
    SELECT 
        alert_id,
        analysis_id,
        dataset_id,
        entity_id,
        entity_type,
        transaction_id,
        alert_type,
        severity,
        priority,
        risk_score,
        behavior_type,
        trigger_source,
        trigger_reason,
        status,
        created_at,
        metadata_json
    FROM alerts
    {where_sql}
    ORDER BY created_at DESC
    LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    items: List[AlertItem] = []
    for r in rows:
        meta_val = None
        if r[15]:
            try:
                meta_val = json.loads(r[15]) if isinstance(r[15], str) else r[15]
            except Exception:
                meta_val = None

        items.append(
            AlertItem(
                alert_id=r[0],
                analysis_id=r[1],
                dataset_id=r[2],
                entity_id=r[3],
                entity_type=r[4],
                transaction_id=r[5],
                alert_type=r[6],
                severity=r[7],
                priority=r[8],
                risk_score=float(r[9]),
                behavior_type=r[10],
                trigger_source=r[11],
                trigger_reason=r[12],
                status=r[13],
                created_at=r[14],
                metadata=meta_val,
            )
        )

    return ApiResponse(success=True, data=items, meta=ApiMeta())

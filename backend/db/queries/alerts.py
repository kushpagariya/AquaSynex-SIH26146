"""DuckDB queries for alerts table."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.utils.errors import AlertNotFoundError, InvalidFilterValueError, InvalidSortFieldError
from backend.utils.pagination import build_pagination_meta, validate_and_normalize_pagination


ACTIVE_STATUSES = {"NEW", "ACKNOWLEDGED", "INVESTIGATING", "ESCALATED"}
INACTIVE_STATUSES = {"RESOLVED", "DISMISSED"}
ALL_VALID_STATUSES = ACTIVE_STATUSES | INACTIVE_STATUSES

ALLOWED_ALERT_SORT_FIELDS = {
    "createdAt": "created_at",
    "created_at": "created_at",
    "updatedAt": "updated_at",
    "updated_at": "updated_at",
    "riskScore": "risk_score",
    "risk_score": "risk_score",
    "severity": "severity",
    "priority": "priority",
    "status": "status",
}


def insert_alert(
    conn: duckdb.DuckDBPyConnection,
    alert_id: str,
    analysis_id: str,
    dataset_id: str,
    fingerprint: str,
    grouping_key: str,
    entity_id: str,
    entity_type: str,
    alert_type: str,
    severity: str,
    priority: str,
    risk_score: float,
    trigger_source: str,
    trigger_reason: str,
    status: str = "NEW",
    transaction_id: Optional[str] = None,
    behavior_type: Optional[str] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
    first_seen_at: Optional[datetime] = None,
    last_seen_at: Optional[datetime] = None,
    acknowledged_at: Optional[datetime] = None,
    resolved_at: Optional[datetime] = None,
    assigned_to: Optional[str] = None,
    metadata_json: Optional[Any] = None,
) -> None:
    """Insert an alert record idempotently."""
    now = datetime.now(timezone.utc)
    created_at = created_at or now
    updated_at = updated_at or now
    meta_str = json.dumps(metadata_json) if metadata_json is not None else None

    # Delete any existing record with same analysis_id and fingerprint for strict idempotency
    conn.execute(
        "DELETE FROM alerts WHERE analysis_id = ? AND fingerprint = ?",
        [analysis_id, fingerprint],
    )

    query = """
    INSERT INTO alerts (
        alert_id, analysis_id, dataset_id, fingerprint, grouping_key,
        transaction_id, entity_id, entity_type, alert_type, severity,
        priority, risk_score, behavior_type, trigger_source, trigger_reason,
        status, created_at, updated_at, first_seen_at, last_seen_at,
        acknowledged_at, resolved_at, assigned_to, metadata_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn.execute(
        query,
        [
            alert_id,
            analysis_id,
            dataset_id,
            fingerprint,
            grouping_key,
            transaction_id,
            entity_id,
            entity_type,
            alert_type,
            severity.lower(),
            priority.upper(),
            float(risk_score),
            behavior_type,
            trigger_source,
            trigger_reason,
            status.upper(),
            created_at,
            updated_at,
            first_seen_at,
            last_seen_at,
            acknowledged_at,
            resolved_at,
            assigned_to,
            meta_str,
        ],
    )


def list_alerts(
    conn: duckdb.DuckDBPyConnection,
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
    """List alert records with filters, search, and pagination."""
    page, page_size = validate_and_normalize_pagination(page, page_size)

    sort_col = ALLOWED_ALERT_SORT_FIELDS.get(sort_by)
    if not sort_col:
        raise InvalidSortFieldError(
            f"Sort field '{sort_by}' is not valid for alerts",
            details={"field": "sortBy", "allowed": list(ALLOWED_ALERT_SORT_FIELDS.keys()), "provided": sort_by},
        )

    where_clauses: List[str] = []
    params: List[Any] = []

    if analysis_id:
        where_clauses.append("analysis_id = ?")
        params.append(analysis_id)

    if dataset_id:
        where_clauses.append("dataset_id = ?")
        params.append(dataset_id)

    if status:
        # Support "active", "inactive", or explicit statuses (e.g. "NEW", "NEW,INVESTIGATING")
        if status.lower() == "active":
            placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
            where_clauses.append(f"status IN ({placeholders})")
            params.extend(list(ACTIVE_STATUSES))
        elif status.lower() == "inactive":
            placeholders = ", ".join("?" for _ in INACTIVE_STATUSES)
            where_clauses.append(f"status IN ({placeholders})")
            params.extend(list(INACTIVE_STATUSES))
        elif status.lower() != "all":
            status_list = [s.strip().upper() for s in status.split(",") if s.strip()]
            if status_list:
                placeholders = ", ".join("?" for _ in status_list)
                where_clauses.append(f"status IN ({placeholders})")
                params.extend(status_list)

    if severity and severity.lower() != "all":
        where_clauses.append("severity = ?")
        params.append(severity.lower())

    if alert_type and alert_type.lower() != "all":
        where_clauses.append("alert_type = ?")
        params.append(alert_type.upper())

    if priority and priority.lower() != "all":
        where_clauses.append("priority = ?")
        params.append(priority.upper())

    if min_risk_score is not None:
        where_clauses.append("risk_score >= ?")
        params.append(min_risk_score)

    if search:
        search_term = f"%{search.strip()}%"
        where_clauses.append(
            "(alert_id LIKE ? OR entity_id LIKE ? OR transaction_id LIKE ? OR trigger_reason LIKE ? OR behavior_type LIKE ?)"
        )
        params.extend([search_term, search_term, search_term, search_term, search_term])

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    count_sql = f"SELECT COUNT(*) FROM alerts{where_sql}"
    count_row = conn.execute(count_sql, params).fetchone()
    total_items = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    query_sql = f"""
    SELECT alert_id, analysis_id, dataset_id, fingerprint, grouping_key,
           transaction_id, entity_id, entity_type, alert_type, severity,
           priority, risk_score, behavior_type, trigger_source, trigger_reason,
           status, created_at, updated_at, first_seen_at, last_seen_at,
           acknowledged_at, resolved_at, assigned_to, metadata_json
    FROM alerts
    {where_sql}
    ORDER BY {sort_col} {direction}
    LIMIT ? OFFSET ?
    """
    exec_params = list(params) + [page_size, offset]
    rel = conn.execute(query_sql, exec_params)
    col_names = [col[0] for col in rel.description]

    items = []
    for row in rel.fetchall():
        record = dict(zip(col_names, row))
        if record.get("metadata_json") and isinstance(record["metadata_json"], str):
            try:
                record["metadata_json"] = json.loads(record["metadata_json"])
            except Exception:
                pass
        items.append(record)

    pagination_meta = build_pagination_meta(page, page_size, total_items)
    return items, pagination_meta


def get_alert_by_id(conn: duckdb.DuckDBPyConnection, alert_id: str) -> Dict[str, Any]:
    """Get single alert by ID."""
    query = "SELECT * FROM alerts WHERE alert_id = ? LIMIT 1"
    rel = conn.execute(query, [alert_id])
    row = rel.fetchone()
    if not row:
        raise AlertNotFoundError(alert_id)

    col_names = [col[0] for col in rel.description]
    record = dict(zip(col_names, row))
    if record.get("metadata_json") and isinstance(record["metadata_json"], str):
        try:
            record["metadata_json"] = json.loads(record["metadata_json"])
        except Exception:
            pass
    return record


def update_alert_status(
    conn: duckdb.DuckDBPyConnection,
    alert_id: str,
    status: str,
) -> Dict[str, Any]:
    """Update alert status with automatic timestamp management."""
    status_upper = status.strip().upper()
    if status_upper not in ALL_VALID_STATUSES:
        raise InvalidFilterValueError(
            f"Invalid alert status '{status}'. Valid statuses: {sorted(list(ALL_VALID_STATUSES))}",
            {"field": "status", "provided": status},
        )

    current = get_alert_by_id(conn, alert_id)
    now = datetime.now(timezone.utc)
    acknowledged_at = current.get("acknowledged_at")
    resolved_at = current.get("resolved_at")

    # Set acknowledged_at when transitioning from NEW to an in-progress state
    if current["status"] == "NEW" and status_upper in ("ACKNOWLEDGED", "INVESTIGATING", "ESCALATED"):
        acknowledged_at = acknowledged_at or now

    # Set resolved_at when transitioning to RESOLVED or DISMISSED
    if status_upper in ("RESOLVED", "DISMISSED"):
        resolved_at = now
    elif current["status"] in ("RESOLVED", "DISMISSED") and status_upper in ACTIVE_STATUSES:
        # Reopening an alert clears resolved_at
        resolved_at = None

    query = """
    UPDATE alerts
    SET status = ?,
        updated_at = ?,
        acknowledged_at = ?,
        resolved_at = ?
    WHERE alert_id = ?
    """
    conn.execute(query, [status_upper, now, acknowledged_at, resolved_at, alert_id])
    return get_alert_by_id(conn, alert_id)


def update_alert_priority(
    conn: duckdb.DuckDBPyConnection,
    alert_id: str,
    priority: str,
) -> Dict[str, Any]:
    """Update alert priority."""
    priority_upper = priority.strip().upper()
    if priority_upper not in ("P1", "P2", "P3", "P4"):
        raise InvalidFilterValueError(
            f"Invalid alert priority '{priority}'. Valid priorities: P1, P2, P3, P4",
            {"field": "priority", "provided": priority},
        )

    # Ensure alert exists
    get_alert_by_id(conn, alert_id)
    now = datetime.now(timezone.utc)

    query = """
    UPDATE alerts
    SET priority = ?,
        updated_at = ?
    WHERE alert_id = ?
    """
    conn.execute(query, [priority_upper, now, alert_id])
    return get_alert_by_id(conn, alert_id)


def get_alerts_summary(
    conn: duckdb.DuckDBPyConnection,
    analysis_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return aggregated alert statistics."""
    where_clauses = []
    params = []
    if analysis_id:
        where_clauses.append("analysis_id = ?")
        params.append(analysis_id)
    if dataset_id:
        where_clauses.append("dataset_id = ?")
        params.append(dataset_id)

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Total and active counts
    active_placeholders = ", ".join("?" for _ in ACTIVE_STATUSES)
    active_params = list(params) + list(ACTIVE_STATUSES)
    active_sql = f"SELECT COUNT(*) FROM alerts{where_sql} {'AND' if where_clauses else 'WHERE'} status IN ({active_placeholders})"
    active_row = conn.execute(active_sql, active_params).fetchone()
    active_count = active_row[0] if active_row else 0

    total_sql = f"SELECT COUNT(*) FROM alerts{where_sql}"
    total_row = conn.execute(total_sql, params).fetchone()
    total_count = total_row[0] if total_row else 0

    # Severity counts
    sev_sql = f"SELECT severity, COUNT(*) FROM alerts{where_sql} GROUP BY severity"
    sev_counts = {row[0]: row[1] for row in conn.execute(sev_sql, params).fetchall()}

    # Status counts
    status_sql = f"SELECT status, COUNT(*) FROM alerts{where_sql} GROUP BY status"
    status_counts = {row[0]: row[1] for row in conn.execute(status_sql, params).fetchall()}

    # Type counts
    type_sql = f"SELECT alert_type, COUNT(*) FROM alerts{where_sql} GROUP BY alert_type"
    type_counts = {row[0]: row[1] for row in conn.execute(type_sql, params).fetchall()}

    return {
        "total": total_count,
        "active": active_count,
        "bySeverity": {
            "critical": sev_counts.get("critical", 0),
            "high": sev_counts.get("high", 0),
            "medium": sev_counts.get("medium", 0),
            "low": sev_counts.get("low", 0),
        },
        "byStatus": status_counts,
        "byType": type_counts,
    }


def delete_alerts_for_analysis(
    conn: duckdb.DuckDBPyConnection,
    analysis_id: str,
) -> int:
    """Delete all alerts for an analysis run."""
    rel = conn.execute("DELETE FROM alerts WHERE analysis_id = ?", [analysis_id])
    return rel.fetchone()[0] if rel else 0

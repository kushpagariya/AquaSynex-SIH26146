"""DuckDB queries for addresses table."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.utils.converters import satoshi_to_btc_str, to_utc_datetime
from backend.utils.errors import AddressNotFoundError, InvalidFilterValueError, InvalidSortFieldError
from backend.utils.pagination import build_pagination_meta, validate_and_normalize_pagination


ALLOWED_ADDR_SORT_FIELDS = {
    "transactionCount": "a.transaction_count",
    "transaction_count": "a.transaction_count",
    "totalReceivedBtc": "a.total_received_satoshi",
    "total_received_satoshi": "a.total_received_satoshi",
    "totalSentBtc": "a.total_sent_satoshi",
    "total_sent_satoshi": "a.total_sent_satoshi",
    "riskScore": "r.risk_score",
    "risk_score": "r.risk_score",
    "firstSeen": "a.first_seen_timestamp",
    "lastSeen": "a.last_seen_timestamp",
}


def list_addresses(
    conn: duckdb.DuckDBPyConnection,
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
    """List addresses for a dataset with filters, risk scores, and pagination."""
    page, page_size = validate_and_normalize_pagination(page, page_size)

    sort_col = ALLOWED_ADDR_SORT_FIELDS.get(sort_by)
    if not sort_col:
        raise InvalidSortFieldError(
            f"Sort field '{sort_by}' is not valid for addresses",
            details={"field": "sortBy", "allowed": list(ALLOWED_ADDR_SORT_FIELDS.keys()), "provided": sort_by},
        )

    # Validate risk scores
    if min_risk_score is not None and (min_risk_score < 0.0 or min_risk_score > 1.0):
        raise InvalidFilterValueError("minRiskScore must be between 0.0 and 1.0", {"field": "minRiskScore", "provided": min_risk_score})
    if max_risk_score is not None and (max_risk_score < 0.0 or max_risk_score > 1.0):
        raise InvalidFilterValueError("maxRiskScore must be between 0.0 and 1.0", {"field": "maxRiskScore", "provided": max_risk_score})
    if min_risk_score is not None and max_risk_score is not None and min_risk_score > max_risk_score:
        raise InvalidFilterValueError("minRiskScore must be <= maxRiskScore")

    if risk_level is not None:
        valid_levels = {"low", "medium", "high", "critical"}
        if risk_level.lower() not in valid_levels:
            raise InvalidFilterValueError(f"riskLevel must be one of {valid_levels}", {"field": "riskLevel", "provided": risk_level})

    where_clauses = ["a.dataset_id = ?"]
    where_params: List[Any] = [dataset_id]

    if risk_level:
        where_clauses.append("r.risk_level = ?")
        where_params.append(risk_level.lower())

    if min_risk_score is not None:
        where_clauses.append("r.risk_score >= ?")
        where_params.append(min_risk_score)

    if max_risk_score is not None:
        where_clauses.append("r.risk_score <= ?")
        where_params.append(max_risk_score)

    join_params: List[Any] = []
    if analysis_id:
        join_clause = "LEFT JOIN ml_results r ON a.address_id = r.entity_id AND a.dataset_id = r.dataset_id AND r.analysis_id = ?"
        join_params.append(analysis_id)
    else:
        join_clause = """
        LEFT JOIN (
            SELECT entity_id, dataset_id, risk_score, risk_level
            FROM (
                SELECT entity_id, dataset_id, risk_score, risk_level,
                       ROW_NUMBER() OVER (PARTITION BY entity_id, dataset_id ORDER BY predicted_at DESC NULLS LAST, result_id DESC) as rn
                FROM ml_results
                WHERE entity_type = 'address'
            ) sub WHERE rn = 1
        ) r ON a.address_id = r.entity_id AND a.dataset_id = r.dataset_id
        """

    all_params = join_params + where_params
    where_sql = " AND ".join(where_clauses)
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    count_sql = f"SELECT COUNT(*) FROM addresses a {join_clause} WHERE {where_sql}"
    count_row = conn.execute(count_sql, all_params).fetchone()
    total_items = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    query_sql = f"""
    SELECT 
        a.address_id,
        a.transaction_count,
        a.total_received_satoshi,
        a.total_sent_satoshi,
        a.first_seen_timestamp,
        a.last_seen_timestamp,
        r.risk_score,
        r.risk_level
    FROM addresses a
    {join_clause}
    WHERE {where_sql}
    ORDER BY {sort_col} {direction} NULLS LAST
    LIMIT ? OFFSET ?
    """
    exec_params = list(all_params) + [page_size, offset]
    rel = conn.execute(query_sql, exec_params)
    col_names = [col[0] for col in rel.description]

    items = []
    for row in rel.fetchall():
        record = dict(zip(col_names, row))
        items.append({
            "address_id": record["address_id"],
            "transaction_count": record["transaction_count"],
            "total_received_btc": satoshi_to_btc_str(record["total_received_satoshi"]),
            "total_sent_btc": satoshi_to_btc_str(record["total_sent_satoshi"]),
            "first_seen": record["first_seen_timestamp"],
            "last_seen": record["last_seen_timestamp"],
            "risk_score": record["risk_score"],
            "risk_level": record["risk_level"],
        })

    pagination_meta = build_pagination_meta(page, page_size, total_items)
    return items, pagination_meta


def get_address_by_id(
    conn: duckdb.DuckDBPyConnection,
    address_id: str,
    analysis_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get address profile with activeDays, type, and ML result with explanations."""
    query = "SELECT * FROM addresses WHERE address_id = ? LIMIT 1"
    rel = conn.execute(query, [address_id])
    row = rel.fetchone()
    if not row:
        raise AddressNotFoundError(address_id)

    col_names = [col[0] for col in rel.description]
    addr = dict(zip(col_names, row))

    # Calculate active days
    active_days = None
    first_seen = addr.get("first_seen_timestamp")
    last_seen = addr.get("last_seen_timestamp")
    if first_seen and last_seen:
        dt_first = to_utc_datetime(first_seen)
        dt_last = to_utc_datetime(last_seen)
        if dt_first and dt_last:
            active_days = max(1, (dt_last - dt_first).days + 1)

    # Fetch ML result
    ml_query = """
    SELECT anomaly_score, risk_score, risk_level, prediction_label, confidence,
           explanation_json, features_json, graph_evidence_json,
           model_id, model_version, predicted_at
    FROM ml_results
    WHERE entity_id = ?
    """
    ml_params = [address_id]
    if analysis_id:
        ml_query += " AND analysis_id = ?"
        ml_params.append(analysis_id)
    ml_query += " ORDER BY predicted_at DESC LIMIT 1"

    ml_rel = conn.execute(ml_query, ml_params)
    ml_row = ml_rel.fetchone()
    ml_result = None
    risk_score = None
    risk_level = None

    if ml_row:
        ml_cols = [col[0] for col in ml_rel.description]
        ml_data = dict(zip(ml_cols, ml_row))
        risk_score = ml_data["risk_score"]
        risk_level = ml_data["risk_level"]

        # Parse JSON fields
        explanations = []
        features = []
        graph_evidence = []

        if ml_data.get("explanation_json"):
            raw = ml_data["explanation_json"]
            explanations = json.loads(raw) if isinstance(raw, str) else raw

        if ml_data.get("features_json"):
            raw = ml_data["features_json"]
            features = json.loads(raw) if isinstance(raw, str) else raw

        if ml_data.get("graph_evidence_json"):
            raw = ml_data["graph_evidence_json"]
            graph_evidence = json.loads(raw) if isinstance(raw, str) else raw

        ml_result = {
            "entity_id": address_id,
            "entity_type": "address",
            "anomaly_score": ml_data["anomaly_score"],
            "risk_score": ml_data["risk_score"],
            "risk_level": ml_data["risk_level"],
            "prediction_label": ml_data["prediction_label"],
            "confidence": ml_data["confidence"],
            "explanations": explanations or [],
            "features": features or [],
            "graph_evidence": graph_evidence or [],
            "model_id": ml_data["model_id"],
            "model_version": ml_data["model_version"],
            "predicted_at": ml_data["predicted_at"],
        }

    return {
        "address_id": addr["address_id"],
        "transaction_count": addr.get("transaction_count"),
        "total_received_btc": satoshi_to_btc_str(addr.get("total_received_satoshi")),
        "total_sent_btc": satoshi_to_btc_str(addr.get("total_sent_satoshi")),
        "first_seen": addr.get("first_seen_timestamp"),
        "last_seen": addr.get("last_seen_timestamp"),
        "address_type": addr.get("address_type"),
        "active_days": active_days,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "ml_result": ml_result,
    }

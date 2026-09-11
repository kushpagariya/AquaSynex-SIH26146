"""DuckDB queries for ml_results table."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.utils.errors import InvalidFilterValueError, InvalidSortFieldError, ResultNotFoundError
from backend.utils.pagination import build_pagination_meta, validate_and_normalize_pagination


ALLOWED_RESULT_SORT_FIELDS = {
    "riskScore": "risk_score",
    "risk_score": "risk_score",
    "anomalyScore": "anomaly_score",
    "anomaly_score": "anomaly_score",
}


def insert_ml_result(
    conn: duckdb.DuckDBPyConnection,
    result_id: str,
    analysis_id: str,
    dataset_id: str,
    entity_id: str,
    entity_type: str,
    anomaly_score: float,
    risk_score: float,
    risk_level: str,
    model_id: str,
    model_version: str,
    prediction_label: Optional[str] = None,
    confidence: Optional[float] = None,
    explanation_json: Optional[Any] = None,
    features_json: Optional[Any] = None,
    graph_evidence_json: Optional[Any] = None,
    predicted_at: Optional[datetime] = None,
) -> None:
    """Insert or replace an ML prediction result."""
    predicted_at = predicted_at or datetime.now(timezone.utc)
    exp_str = json.dumps(explanation_json) if explanation_json is not None else None
    feat_str = json.dumps(features_json) if features_json is not None else None
    graph_str = json.dumps(graph_evidence_json) if graph_evidence_json is not None else None

    # Delete any existing record for this entity in this analysis
    conn.execute(
        "DELETE FROM ml_results WHERE analysis_id = ? AND entity_id = ? AND entity_type = ?",
        [analysis_id, entity_id, entity_type],
    )

    query = """
    INSERT INTO ml_results (
        result_id, analysis_id, dataset_id, entity_id, entity_type,
        anomaly_score, risk_score, risk_level, prediction_label,
        confidence, explanation_json, features_json, graph_evidence_json,
        model_id, model_version, predicted_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn.execute(
        query,
        [
            result_id,
            analysis_id,
            dataset_id,
            entity_id,
            entity_type,
            anomaly_score,
            risk_score,
            risk_level,
            prediction_label,
            confidence,
            exp_str,
            feat_str,
            graph_str,
            model_id,
            model_version,
            predicted_at,
        ],
    )


def list_ml_results(
    conn: duckdb.DuckDBPyConnection,
    analysis_id: str,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "riskScore",
    sort_dir: str = "desc",
    risk_level: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    entity_type: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """List ML result summaries for an analysis run."""
    page, page_size = validate_and_normalize_pagination(page, page_size)

    sort_col = ALLOWED_RESULT_SORT_FIELDS.get(sort_by)
    if not sort_col:
        raise InvalidSortFieldError(
            f"Sort field '{sort_by}' is not valid for ML results",
            details={"field": "sortBy", "allowed": list(ALLOWED_RESULT_SORT_FIELDS.keys()), "provided": sort_by},
        )

    if min_risk_score is not None and (min_risk_score < 0.0 or min_risk_score > 1.0):
        raise InvalidFilterValueError("minRiskScore must be between 0.0 and 1.0", {"field": "minRiskScore", "provided": min_risk_score})

    if risk_level is not None:
        valid_levels = {"low", "medium", "high", "critical"}
        if risk_level.lower() not in valid_levels:
            raise InvalidFilterValueError(f"riskLevel must be one of {valid_levels}", {"field": "riskLevel", "provided": risk_level})

    if entity_type is not None:
        valid_types = {"address", "transaction"}
        if entity_type.lower() not in valid_types:
            raise InvalidFilterValueError(f"entityType must be one of {valid_types}", {"field": "entityType", "provided": entity_type})

    where_clauses = ["analysis_id = ?"]
    params: List[Any] = [analysis_id]

    if risk_level:
        where_clauses.append("risk_level = ?")
        params.append(risk_level.lower())

    if min_risk_score is not None:
        where_clauses.append("risk_score >= ?")
        params.append(min_risk_score)

    if entity_type:
        where_clauses.append("entity_type = ?")
        params.append(entity_type.lower())

    where_sql = " AND ".join(where_clauses)
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    count_sql = f"SELECT COUNT(*) FROM ml_results WHERE {where_sql}"
    count_row = conn.execute(count_sql, params).fetchone()
    total_items = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    query_sql = f"""
    SELECT entity_id, entity_type, anomaly_score, risk_score, risk_level,
           prediction_label, model_id, model_version, predicted_at
    FROM ml_results
    WHERE {where_sql}
    ORDER BY {sort_col} {direction}
    LIMIT ? OFFSET ?
    """
    exec_params = list(params) + [page_size, offset]
    rel = conn.execute(query_sql, exec_params)
    col_names = [col[0] for col in rel.description]

    items = [dict(zip(col_names, row)) for row in rel.fetchall()]
    pagination_meta = build_pagination_meta(page, page_size, total_items)
    return items, pagination_meta


def get_ml_result_for_entity(
    conn: duckdb.DuckDBPyConnection,
    analysis_id: str,
    entity_id: str,
) -> Dict[str, Any]:
    """Get full ML result detail with explanations for one entity."""
    query = """
    SELECT * FROM ml_results
    WHERE analysis_id = ? AND entity_id = ?
    LIMIT 1
    """
    rel = conn.execute(query, [analysis_id, entity_id])
    row = rel.fetchone()
    if not row:
        raise ResultNotFoundError(entity_id, analysis_id)

    col_names = [col[0] for col in rel.description]
    res = dict(zip(col_names, row))

    for json_col in ["explanation_json", "features_json", "graph_evidence_json"]:
        if res.get(json_col) and isinstance(res[json_col], str):
            try:
                res[json_col] = json.loads(res[json_col])
            except Exception:
                res[json_col] = []
        elif res.get(json_col) is None:
            res[json_col] = []

    return {
        "entity_id": res["entity_id"],
        "entity_type": res["entity_type"],
        "anomaly_score": res["anomaly_score"],
        "risk_score": res["risk_score"],
        "risk_level": res["risk_level"],
        "prediction_label": res.get("prediction_label"),
        "confidence": res.get("confidence"),
        "explanations": res.get("explanation_json") or [],
        "features": res.get("features_json") or [],
        "graph_evidence": res.get("graph_evidence_json") or [],
        "model_id": res["model_id"],
        "model_version": res["model_version"],
        "predicted_at": res["predicted_at"],
    }

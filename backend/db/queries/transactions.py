"""DuckDB queries for transactions, transaction_inputs, and transaction_outputs."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.utils.converters import btc_str_to_satoshi, satoshi_to_btc_str, to_utc_datetime
from backend.utils.errors import InvalidFilterValueError, InvalidSortFieldError, TransactionNotFoundError
from backend.utils.pagination import build_pagination_meta, validate_and_normalize_pagination


ALLOWED_TX_SORT_FIELDS = {
    "timestamp": "t.timestamp",
    "totalValueSatoshi": "t.total_output_value_satoshi",
    "total_output_value_satoshi": "t.total_output_value_satoshi",
    "inputCount": "t.input_count",
    "input_count": "t.input_count",
    "outputCount": "t.output_count",
    "output_count": "t.output_count",
    "riskScore": "r.risk_score",
    "risk_score": "r.risk_score",
}


def list_transactions(
    conn: duckdb.DuckDBPyConnection,
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
    """Query transactions for a dataset with filters, sorting, and pagination."""
    page, page_size = validate_and_normalize_pagination(page, page_size)

    sort_col = ALLOWED_TX_SORT_FIELDS.get(sort_by)
    if not sort_col:
        raise InvalidSortFieldError(
            f"Sort field '{sort_by}' is not valid for transactions",
            details={"field": "sortBy", "allowed": list(ALLOWED_TX_SORT_FIELDS.keys()), "provided": sort_by},
        )

    # Validate risk scores
    if min_risk_score is not None and (min_risk_score < 0.0 or min_risk_score > 1.0):
        raise InvalidFilterValueError("minRiskScore must be between 0.0 and 1.0", {"field": "minRiskScore", "provided": min_risk_score})
    if max_risk_score is not None and (max_risk_score < 0.0 or max_risk_score > 1.0):
        raise InvalidFilterValueError("maxRiskScore must be between 0.0 and 1.0", {"field": "maxRiskScore", "provided": max_risk_score})
    if min_risk_score is not None and max_risk_score is not None and min_risk_score > max_risk_score:
        raise InvalidFilterValueError("minRiskScore must be <= maxRiskScore")

    # Validate risk level
    if risk_level is not None:
        valid_levels = {"low", "medium", "high", "critical"}
        if risk_level.lower() not in valid_levels:
            raise InvalidFilterValueError(f"riskLevel must be one of {valid_levels}", {"field": "riskLevel", "provided": risk_level})

    # Base WHERE clauses
    where_clauses = ["t.dataset_id = ?"]
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

    dt_from = None
    if from_timestamp:
        try:
            dt_from = to_utc_datetime(from_timestamp)
            where_clauses.append("t.timestamp >= ?")
            where_params.append(dt_from)
        except Exception as exc:
            raise InvalidFilterValueError(f"Invalid fromTimestamp format: {exc}", {"field": "fromTimestamp", "provided": from_timestamp})

    dt_to = None
    if to_timestamp:
        try:
            dt_to = to_utc_datetime(to_timestamp)
            where_clauses.append("t.timestamp <= ?")
            where_params.append(dt_to)
        except Exception as exc:
            raise InvalidFilterValueError(f"Invalid toTimestamp format: {exc}", {"field": "toTimestamp", "provided": to_timestamp})

    if dt_from and dt_to and dt_from > dt_to:
        raise InvalidFilterValueError("fromTimestamp must be earlier than or equal to toTimestamp", {"fromTimestamp": from_timestamp, "toTimestamp": to_timestamp})

    min_sat = None
    if min_value_btc is not None:
        try:
            min_sat = btc_str_to_satoshi(min_value_btc)
            if min_sat < 0:
                raise InvalidFilterValueError("minValueBtc must be non-negative", {"field": "minValueBtc", "provided": min_value_btc})
            where_clauses.append("t.total_output_value_satoshi >= ?")
            where_params.append(min_sat)
        except InvalidFilterValueError:
            raise
        except Exception as exc:
            raise InvalidFilterValueError(f"Invalid minValueBtc format: {exc}", {"field": "minValueBtc", "provided": min_value_btc})

    max_sat = None
    if max_value_btc is not None:
        try:
            max_sat = btc_str_to_satoshi(max_value_btc)
            if max_sat < 0:
                raise InvalidFilterValueError("maxValueBtc must be non-negative", {"field": "maxValueBtc", "provided": max_value_btc})
            where_clauses.append("t.total_output_value_satoshi <= ?")
            where_params.append(max_sat)
        except InvalidFilterValueError:
            raise
        except Exception as exc:
            raise InvalidFilterValueError(f"Invalid maxValueBtc format: {exc}", {"field": "maxValueBtc", "provided": max_value_btc})

    if min_sat is not None and max_sat is not None and min_sat > max_sat:
        raise InvalidFilterValueError("minValueBtc must be <= maxValueBtc", {"minValueBtc": min_value_btc, "maxValueBtc": max_value_btc})

    # Optional server-side IP filter (via network_events semi-join)
    if ip:
        clean_ip = ip.strip()
        if clean_ip:
            where_clauses.append(
                """EXISTS (
                    SELECT 1 FROM network_events ne
                    WHERE ne.dataset_id = t.dataset_id
                      AND ne.transaction_id = t.transaction_id
                      AND (ne.src_ip = ? OR ne.dst_ip = ?)
                )"""
            )
            where_params.extend([clean_ip, clean_ip])

    # Optional server-side address filter (via inputs/outputs semi-joins)
    if address:
        clean_addr = address.strip()
        if clean_addr:
            where_clauses.append(
                """(
                    EXISTS (
                        SELECT 1 FROM transaction_inputs ti
                        WHERE ti.dataset_id = t.dataset_id
                          AND ti.transaction_id = t.transaction_id
                          AND ti.input_address = ?
                    )
                    OR EXISTS (
                        SELECT 1 FROM transaction_outputs tout
                        WHERE tout.dataset_id = t.dataset_id
                          AND tout.transaction_id = t.transaction_id
                          AND tout.output_address = ?
                    )
                )"""
            )
            where_params.extend([clean_addr, clean_addr])

    # Optional exact transaction_id filter
    if txid:
        clean_txid = txid.strip()
        if clean_txid:
            where_clauses.append("t.transaction_id = ?")
            where_params.append(clean_txid)

    # ML join
    join_params: List[Any] = []
    if analysis_id:
        join_clause = "LEFT JOIN ml_results r ON t.transaction_id = r.entity_id AND t.dataset_id = r.dataset_id AND r.analysis_id = ?"
        join_params.append(analysis_id)
    else:
        join_clause = """
        LEFT JOIN (
            SELECT entity_id, dataset_id, risk_score, risk_level
            FROM (
                SELECT entity_id, dataset_id, risk_score, risk_level,
                       ROW_NUMBER() OVER (PARTITION BY entity_id, dataset_id ORDER BY predicted_at DESC NULLS LAST, result_id DESC) as rn
                FROM ml_results
                WHERE entity_type = 'transaction'
            ) sub WHERE rn = 1
        ) r ON t.transaction_id = r.entity_id AND t.dataset_id = r.dataset_id
        """

    all_params = join_params + where_params
    where_sql = " AND ".join(where_clauses)
    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    # Count total
    count_sql = f"SELECT COUNT(*) FROM transactions t {join_clause} WHERE {where_sql}"
    count_row = conn.execute(count_sql, all_params).fetchone()
    total_items = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    query_sql = f"""
    SELECT 
        t.transaction_id,
        t.block_height,
        t.timestamp,
        t.input_count,
        t.output_count,
        t.total_input_value_satoshi,
        t.total_output_value_satoshi,
        t.fee_satoshi,
        r.risk_score,
        r.risk_level
    FROM transactions t
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
            "transaction_id": record["transaction_id"],
            "block_height": record["block_height"],
            "timestamp": record["timestamp"],
            "input_count": record["input_count"],
            "output_count": record["output_count"],
            "total_input_value_btc": satoshi_to_btc_str(record["total_input_value_satoshi"]),
            "total_output_value_btc": satoshi_to_btc_str(record["total_output_value_satoshi"]),
            "fee_btc": satoshi_to_btc_str(record["fee_satoshi"]),
            "risk_score": record["risk_score"],
            "risk_level": record["risk_level"],
        })

    pagination_meta = build_pagination_meta(page, page_size, total_items)
    return items, pagination_meta


def get_transaction_by_id(
    conn: duckdb.DuckDBPyConnection,
    transaction_id: str,
    analysis_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get full transaction detail including inputs, outputs, and ML prediction if available."""
    # Find base transaction
    tx_query = "SELECT * FROM transactions WHERE transaction_id = ? LIMIT 1"
    rel = conn.execute(tx_query, [transaction_id])
    row = rel.fetchone()
    if not row:
        raise TransactionNotFoundError(transaction_id)

    col_names = [col[0] for col in rel.description]
    tx_record = dict(zip(col_names, row))

    # Fetch inputs
    inputs_query = """
    SELECT input_index, input_address, input_value_satoshi
    FROM transaction_inputs
    WHERE transaction_id = ?
    ORDER BY input_index ASC
    """
    inputs_rel = conn.execute(inputs_query, [transaction_id])
    inputs = [
        {
            "input_index": r[0],
            "input_address": r[1],
            "input_value_btc": satoshi_to_btc_str(r[2]),
        }
        for r in inputs_rel.fetchall()
    ]

    # Fetch outputs
    outputs_query = """
    SELECT output_index, output_address, output_value_satoshi, script_type
    FROM transaction_outputs
    WHERE transaction_id = ?
    ORDER BY output_index ASC
    """
    outputs_rel = conn.execute(outputs_query, [transaction_id])
    outputs = [
        {
            "output_index": r[0],
            "output_address": r[1],
            "output_value_btc": satoshi_to_btc_str(r[2]),
            "script_type": r[3],
        }
        for r in outputs_rel.fetchall()
    ]

    # Fetch ML result if present
    ml_query = """
    SELECT anomaly_score, risk_score, risk_level, prediction_label,
           model_id, model_version, predicted_at
    FROM ml_results
    WHERE entity_id = ?
    """
    ml_params = [transaction_id]
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
        ml_result = {
            "entity_id": transaction_id,
            "entity_type": "transaction",
            "anomaly_score": ml_data["anomaly_score"],
            "risk_score": ml_data["risk_score"],
            "risk_level": ml_data["risk_level"],
            "prediction_label": ml_data["prediction_label"],
            "model_id": ml_data["model_id"],
            "model_version": ml_data["model_version"],
            "predicted_at": ml_data["predicted_at"],
        }

    # Fetch network events if present
    net_query = """
    SELECT src_ip, src_port, dst_ip, dst_port, country, asn
    FROM network_events
    WHERE transaction_id = ? AND dataset_id = ?
    LIMIT 10
    """
    net_rel = conn.execute(net_query, [transaction_id, tx_record["dataset_id"]])
    network_events = [
        {
            "src_ip": r[0],
            "src_port": r[1],
            "dst_ip": r[2],
            "dst_port": r[3],
            "country": r[4],
            "asn": r[5],
        }
        for r in net_rel.fetchall()
    ]

    return {
        "transaction_id": tx_record["transaction_id"],
        "block_height": tx_record.get("block_height"),
        "block_hash": tx_record.get("block_hash"),
        "timestamp": tx_record.get("timestamp"),
        "input_count": tx_record.get("input_count"),
        "output_count": tx_record.get("output_count"),
        "total_input_value_btc": satoshi_to_btc_str(tx_record.get("total_input_value_satoshi")),
        "total_output_value_btc": satoshi_to_btc_str(tx_record.get("total_output_value_satoshi")),
        "fee_btc": satoshi_to_btc_str(tx_record.get("fee_satoshi")),
        "transaction_size_bytes": tx_record.get("transaction_size_bytes"),
        "label": tx_record.get("label"),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "inputs": inputs,
        "outputs": outputs,
        "network_events": network_events,
        "ml_result": ml_result,
    }

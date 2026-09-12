"""DuckDB queries for datasets table.

Authoritative reference: docs/backend/backend-architecture.md
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
import duckdb
from backend.utils.errors import DatasetNotFoundError, InvalidSortFieldError
from backend.utils.pagination import build_pagination_meta, validate_and_normalize_pagination


ALLOWED_SORT_FIELDS = {
    "uploadedAt": "uploaded_at",
    "uploaded_at": "uploaded_at",
    "name": "name",
    "rowCount": "row_count",
    "row_count": "row_count",
    "sizeBytes": "size_bytes",
    "size_bytes": "size_bytes",
}


def insert_dataset(
    conn: duckdb.DuckDBPyConnection,
    dataset_id: str,
    name: str,
    file_name: str,
    file_path: str,
    format_str: str,
    size_bytes: int,
    status: str = "uploaded",
    available_fields: Optional[List[str]] = None,
    validation_summary: Optional[Dict[str, Any]] = None,
    canonical_field_map: Optional[Dict[str, Any]] = None,
    row_count: Optional[int] = None,
    canonical_tx_count: Optional[int] = None,
    error_message: Optional[str] = None,
    uploaded_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Insert a new dataset record."""
    uploaded_at = uploaded_at or datetime.now(timezone.utc)
    fields_list = available_fields or []
    val_json = json.dumps(validation_summary) if validation_summary is not None else None
    map_json = json.dumps(canonical_field_map) if canonical_field_map is not None else None

    query = """
    INSERT INTO datasets (
        dataset_id, name, file_name, file_path, format, size_bytes,
        row_count, canonical_tx_count, uploaded_at, status,
        available_fields, canonical_field_map, validation_summary, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    conn.execute(
        query,
        [
            dataset_id,
            name,
            file_name,
            file_path,
            format_str,
            size_bytes,
            row_count,
            canonical_tx_count,
            uploaded_at,
            status,
            fields_list,
            map_json,
            val_json,
            error_message,
        ],
    )
    return get_dataset_by_id(conn, dataset_id)


def get_dataset_by_id(conn: duckdb.DuckDBPyConnection, dataset_id: str) -> Dict[str, Any]:
    """Retrieve full dataset record by UUID."""
    query = "SELECT * FROM datasets WHERE dataset_id = ?"
    rel = conn.execute(query, [dataset_id])
    row = rel.fetchone()
    if not row:
        raise DatasetNotFoundError(dataset_id)

    col_names = [col[0] for col in rel.description]
    res = dict(zip(col_names, row))

    # Parse JSON fields if strings
    for json_col in ["validation_summary", "canonical_field_map"]:
        if res.get(json_col) and isinstance(res[json_col], str):
            try:
                res[json_col] = json.loads(res[json_col])
            except Exception:
                pass

    if res.get("available_fields") is None:
        res["available_fields"] = []

    return res


def list_datasets(
    conn: duckdb.DuckDBPyConnection,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "uploadedAt",
    sort_dir: str = "desc",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """List datasets with pagination and sorting."""
    page, page_size = validate_and_normalize_pagination(page, page_size)

    sort_column = ALLOWED_SORT_FIELDS.get(sort_by)
    if not sort_column:
        raise InvalidSortFieldError(
            f"Sort field '{sort_by}' is not valid for datasets",
            details={"field": "sortBy", "allowed": list(ALLOWED_SORT_FIELDS.keys()), "provided": sort_by},
        )

    direction = "DESC" if sort_dir.lower() == "desc" else "ASC"

    # Count total
    count_row = conn.execute("SELECT COUNT(*) FROM datasets").fetchone()
    total_items = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    query = f"""
    SELECT dataset_id, name, file_name, file_path, format, size_bytes,
           row_count, canonical_tx_count, uploaded_at, status, available_fields,
           validation_summary, error_message
    FROM datasets
    ORDER BY {sort_column} {direction}
    LIMIT ? OFFSET ?
    """
    rel = conn.execute(query, [page_size, offset])
    col_names = [col[0] for col in rel.description]

    items = []
    for row in rel.fetchall():
        item = dict(zip(col_names, row))
        if item.get("validation_summary") and isinstance(item["validation_summary"], str):
            try:
                item["validation_summary"] = json.loads(item["validation_summary"])
            except Exception:
                pass
        if item.get("available_fields") is None:
            item["available_fields"] = []
        items.append(item)

    pagination_meta = build_pagination_meta(page, page_size, total_items)
    return items, pagination_meta


def update_dataset(
    conn: duckdb.DuckDBPyConnection,
    dataset_id: str,
    status: Optional[str] = None,
    row_count: Optional[int] = None,
    canonical_tx_count: Optional[int] = None,
    available_fields: Optional[List[str]] = None,
    validation_summary: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Update fields on a dataset record."""
    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if row_count is not None:
        updates.append("row_count = ?")
        params.append(row_count)
    if canonical_tx_count is not None:
        updates.append("canonical_tx_count = ?")
        params.append(canonical_tx_count)
    if available_fields is not None:
        updates.append("available_fields = ?")
        params.append(available_fields)
    if validation_summary is not None:
        updates.append("validation_summary = ?")
        params.append(json.dumps(validation_summary))
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if updates:
        params.append(dataset_id)
        query = f"UPDATE datasets SET {', '.join(updates)} WHERE dataset_id = ?"
        conn.execute(query, params)

    return get_dataset_by_id(conn, dataset_id)


def delete_dataset(conn: duckdb.DuckDBPyConnection, dataset_id: str) -> bool:
    """Delete a dataset and all associated records across tables."""
    # Ensure exists
    get_dataset_by_id(conn, dataset_id)

    # Cascading deletes
    conn.execute("DELETE FROM ml_results WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM analysis_runs WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM network_events WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM transaction_inputs WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM transaction_outputs WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM transactions WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM addresses WHERE dataset_id = ?", [dataset_id])
    conn.execute("DELETE FROM datasets WHERE dataset_id = ?", [dataset_id])
    return True

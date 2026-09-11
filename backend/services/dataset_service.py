"""Dataset management service for upload, validation, parsing, and deletion."""

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any, BinaryIO, Dict, List, Optional, Tuple
import uuid
import duckdb
from backend.config import settings
from backend.db.queries import datasets as dataset_queries
from backend.utils.converters import btc_str_to_satoshi, to_utc_datetime
from backend.utils.errors import (
    DatasetAnalysisRunningError,
    DatasetError,
    DatasetNotFoundError,
    FileTooLargeError,
    UnsupportedFileFormatError,
    ValidationError,
)
from backend.utils.logging import logger


ALLOWED_FORMATS = {
    ".csv": "csv",
    ".parquet": "parquet",
    ".json": "json",
    ".jsonl": "jsonl",
}


def escape_sql_literal(val: Any) -> str:
    """Escape a Python value for use as a SQL string literal by doubling single quotes."""
    return str(val).replace("'", "''")


def escape_sql_identifier(identifier: str) -> str:
    """Escape a column/table name for use as a SQL quoted identifier by doubling double quotes."""
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


class DatasetService:
    """Service managing dataset upload, validation, ingestion, and deletion."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def upload_dataset(
        self,
        file_obj: BinaryIO,
        filename: str,
        name: str,
        content_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate, store, register, and process an uploaded dataset file."""
        if not name or len(name.strip()) == 0 or len(name) > 200:
            raise ValidationError("Dataset name must be between 1 and 200 characters", details={"field": "name"})

        safe_filename = Path(filename).name
        if not safe_filename or safe_filename in (".", ".."):
            raise ValidationError("Invalid file name", details={"field": "filename", "provided": filename})

        import urllib.parse
        unescaped_filename = urllib.parse.unquote(safe_filename)
        if any(c in safe_filename or c in unescaped_filename for c in ("'", '"', '`')):
            raise ValidationError("Filename must not contain quotes", details={"field": "filename", "provided": filename})

        ext = Path(safe_filename).suffix.lower()
        if ext not in ALLOWED_FORMATS:
            raise UnsupportedFileFormatError(
                f"File format '{ext}' is not supported. Supported formats: {list(ALLOWED_FORMATS.keys())}",
                details={"provided": ext, "allowed": list(ALLOWED_FORMATS.keys())},
            )

        format_str = ALLOWED_FORMATS[ext]
        dataset_id = str(uuid.uuid4())

        # Create dataset directory
        dataset_dir = Path(settings.DATA_DIR) / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dataset_dir / safe_filename

        # Write file with size validation
        size_bytes = 0
        with open(dest_path, "wb") as f_out:
            while chunk := file_obj.read(1024 * 1024):  # 1MB chunks
                size_bytes += len(chunk)
                if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    f_out.close()
                    dest_path.unlink(missing_ok=True)
                    raise FileTooLargeError(
                        f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
                        details={"maxSizeBytes": settings.MAX_UPLOAD_SIZE_BYTES, "receivedBytes": size_bytes},
                    )
                f_out.write(chunk)

        if size_bytes == 0:
            dest_path.unlink(missing_ok=True)
            raise ValidationError("Uploaded file is empty", details={"field": "file"})

        # Register dataset in DuckDB with status='processing'
        dataset = dataset_queries.insert_dataset(
            conn=self.conn,
            dataset_id=dataset_id,
            name=name.strip(),
            file_name=safe_filename,
            file_path=str(dest_path),
            format_str=format_str,
            size_bytes=size_bytes,
            status="processing",
            uploaded_at=datetime.now(timezone.utc),
        )

        # Ingest file into canonical tables
        try:
            self._ingest_file(dataset_id, dest_path, format_str)
        except Exception as exc:
            logger.error(f"Ingestion failed for dataset {dataset_id}: {exc}")
            # Rollback partially ingested rows for this dataset
            try:
                self.conn.execute("DELETE FROM transaction_inputs WHERE dataset_id = ?", [dataset_id])
                self.conn.execute("DELETE FROM transaction_outputs WHERE dataset_id = ?", [dataset_id])
                self.conn.execute("DELETE FROM transactions WHERE dataset_id = ?", [dataset_id])
                self.conn.execute("DELETE FROM addresses WHERE dataset_id = ?", [dataset_id])
            except Exception as rollback_exc:
                logger.warning(f"Failed to rollback partial ingestion records: {rollback_exc}")

            dataset_queries.update_dataset_status(
                conn=self.conn,
                dataset_id=dataset_id,
                status="error",
                error_message=str(exc),
            )
            raise DatasetError(f"Failed to process dataset file: {exc}", details={"error": str(exc)}) from exc

        return dataset

    def _ingest_file(self, dataset_id: str, file_path: Path, format_str: str) -> None:
        """Parse raw file, detect fields, and normalize records into canonical tables."""
        logger.info(f"Ingesting dataset {dataset_id} from {file_path} ({format_str})...")

        # Load data using DuckDB analytical scanner
        temp_view = f"temp_upload_{dataset_id.replace('-', '_')}"
        safe_file_path = escape_sql_literal(file_path)
        if format_str == "csv":
            self.conn.execute(f"CREATE OR REPLACE VIEW {temp_view} AS SELECT * FROM read_csv_auto('{safe_file_path}')")
        elif format_str == "parquet":
            self.conn.execute(f"CREATE OR REPLACE VIEW {temp_view} AS SELECT * FROM read_parquet('{safe_file_path}')")
        elif format_str in ["json", "jsonl"]:
            self.conn.execute(f"CREATE OR REPLACE VIEW {temp_view} AS SELECT * FROM read_json_auto('{safe_file_path}')")

        # Inspect available columns
        sample_rel = self.conn.execute(f"SELECT * FROM {temp_view} LIMIT 0")
        raw_cols = [c[0] for c in sample_rel.description]
        raw_cols_lower = {c.lower(): c for c in raw_cols}

        # Field mapping for canonical transaction fields
        tx_col = raw_cols_lower.get("transaction_id") or raw_cols_lower.get("txid") or raw_cols_lower.get("tx_id") or raw_cols_lower.get("transactionid") or raw_cols_lower.get("hash")
        time_col = raw_cols_lower.get("timestamp") or raw_cols_lower.get("time") or raw_cols_lower.get("block_time")
        val_col = raw_cols_lower.get("total_output_value_satoshi") or raw_cols_lower.get("value") or raw_cols_lower.get("amount") or raw_cols_lower.get("val")
        fee_col = raw_cols_lower.get("fee_satoshi") or raw_cols_lower.get("fee")
        block_height_col = raw_cols_lower.get("block_height") or raw_cols_lower.get("block") or raw_cols_lower.get("height")
        in_addr_col = raw_cols_lower.get("input_address") or raw_cols_lower.get("sender") or raw_cols_lower.get("from_address")
        out_addr_col = raw_cols_lower.get("output_address") or raw_cols_lower.get("receiver") or raw_cols_lower.get("to_address")
        label_col = raw_cols_lower.get("label") or raw_cols_lower.get("class") or raw_cols_lower.get("is_illicit") or raw_cols_lower.get("category")

        if not tx_col:
            # Fallback: if no tx column, generate row hash or UUID surrogate
            tx_col_expr = "CAST(uuid() AS VARCHAR)"
        else:
            tx_col_expr = f'CAST({escape_sql_identifier(tx_col)} AS VARCHAR)'

        # Timestamp normalization: supports unix epochs (seconds / ms) and ISO timestamps
        if time_col:
            time_col_ident = escape_sql_identifier(time_col)
            timestamp_expr = f"""
            CASE 
                WHEN {time_col_ident} IS NULL THEN NULL
                WHEN TRY_CAST({time_col_ident} AS BIGINT) IS NOT NULL AND TRY_CAST({time_col_ident} AS BIGINT) > 100000000000
                    THEN to_timestamp(TRY_CAST({time_col_ident} AS DOUBLE) / 1000.0)
                WHEN TRY_CAST({time_col_ident} AS BIGINT) IS NOT NULL AND TRY_CAST({time_col_ident} AS BIGINT) BETWEEN 1230940800 AND 3000000000
                    THEN to_timestamp(TRY_CAST({time_col_ident} AS BIGINT))
                ELSE TRY_CAST({time_col_ident} AS TIMESTAMPTZ)
            END
            """
        else:
            timestamp_expr = "NULL"

        # Value normalization: preserves satoshi precision for both BTC float/string and satoshi integer
        if val_col:
            val_col_ident = escape_sql_identifier(val_col)
            val_col_lit = escape_sql_literal(val_col)
            val_expr = f"""
            CASE 
                WHEN {val_col_ident} IS NULL THEN NULL
                WHEN LOWER('{val_col_lit}') LIKE '%sat%' THEN TRY_CAST({val_col_ident} AS BIGINT)
                WHEN LOWER('{val_col_lit}') LIKE '%btc%' THEN CAST(ROUND(TRY_CAST({val_col_ident} AS DOUBLE) * 100000000) AS BIGINT)
                WHEN CAST({val_col_ident} AS VARCHAR) LIKE '%.%' 
                     OR CAST({val_col_ident} AS VARCHAR) LIKE '%e-%' 
                     OR CAST({val_col_ident} AS VARCHAR) LIKE '%E-%'
                THEN CAST(ROUND(TRY_CAST({val_col_ident} AS DOUBLE) * 100000000) AS BIGINT)
                ELSE TRY_CAST({val_col_ident} AS BIGINT)
            END
            """
        else:
            val_expr = "NULL"

        if fee_col:
            fee_col_ident = escape_sql_identifier(fee_col)
            fee_col_lit = escape_sql_literal(fee_col)
            fee_expr = f"""
            CASE 
                WHEN {fee_col_ident} IS NULL THEN NULL
                WHEN LOWER('{fee_col_lit}') LIKE '%sat%' THEN TRY_CAST({fee_col_ident} AS BIGINT)
                WHEN LOWER('{fee_col_lit}') LIKE '%btc%' THEN CAST(ROUND(TRY_CAST({fee_col_ident} AS DOUBLE) * 100000000) AS BIGINT)
                WHEN CAST({fee_col_ident} AS VARCHAR) LIKE '%.%' 
                     OR CAST({fee_col_ident} AS VARCHAR) LIKE '%e-%' 
                     OR CAST({fee_col_ident} AS VARCHAR) LIKE '%E-%'
                THEN CAST(ROUND(TRY_CAST({fee_col_ident} AS DOUBLE) * 100000000) AS BIGINT)
                ELSE TRY_CAST({fee_col_ident} AS BIGINT)
            END
            """
        else:
            fee_expr = "NULL"

        block_expr = f'TRY_CAST({escape_sql_identifier(block_height_col)} AS INTEGER)' if block_height_col else "NULL"

        if label_col:
            label_col_ident = escape_sql_identifier(label_col)
            label_expr = f"""
            CASE 
                WHEN CAST({label_col_ident} AS VARCHAR) IN ('1', 'illicit', 'ILLICIT', 'true', 'True') THEN 'illicit'
                WHEN CAST({label_col_ident} AS VARCHAR) IN ('0', 'licit', 'LICIT', 'legitimate', 'false', 'False') THEN 'licit'
                ELSE 'unknown'
            END
            """
        else:
            label_expr = "NULL"

        # Count total rows
        count_row = self.conn.execute(f"SELECT COUNT(*) FROM {temp_view}").fetchone()
        row_count = count_row[0] if count_row else 0

        # Insert transactions into canonical table
        insert_tx_sql = f"""
        INSERT OR REPLACE INTO transactions (
            transaction_id, dataset_id, block_height, timestamp,
            input_count, output_count, total_output_value_satoshi,
            fee_satoshi, label, ingested_at
        )
        SELECT 
            {tx_col_expr} AS transaction_id,
            '{dataset_id}' AS dataset_id,
            {block_expr} AS block_height,
            {timestamp_expr} AS timestamp,
            1 AS input_count,
            1 AS output_count,
            {val_expr} AS total_output_value_satoshi,
            {fee_expr} AS fee_satoshi,
            {label_expr} AS label,
            current_timestamp AS ingested_at
        FROM {temp_view}
        WHERE {tx_col_expr} IS NOT NULL
        """
        self.conn.execute(insert_tx_sql)

        # Check canonical tx count
        tx_count_row = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE dataset_id = ?", [dataset_id]
        ).fetchone()
        canonical_tx_count = tx_count_row[0] if tx_count_row else 0

        # Derive inputs & outputs if address columns exist
        available_fields = ["transactionId"]
        if time_col:
            available_fields.append("timestamp")
        if val_col:
            available_fields.append("totalOutputValueBtc")
        if fee_col:
            available_fields.append("feeBtc")
        if label_col:
            available_fields.append("label")

        if out_addr_col:
            out_addr_ident = escape_sql_identifier(out_addr_col)
            available_fields.append("outputAddress")
            insert_out_sql = f"""
            INSERT OR REPLACE INTO transaction_outputs (
                output_id, transaction_id, dataset_id, output_index,
                output_address, output_value_satoshi, is_spent
            )
            SELECT 
                {tx_col_expr} || ':0' AS output_id,
                {tx_col_expr} AS transaction_id,
                '{dataset_id}' AS dataset_id,
                0 AS output_index,
                CAST({out_addr_ident} AS VARCHAR) AS output_address,
                {val_expr} AS output_value_satoshi,
                FALSE AS is_spent
            FROM {temp_view}
            WHERE {out_addr_ident} IS NOT NULL
            """
            self.conn.execute(insert_out_sql)

        if in_addr_col:
            in_addr_ident = escape_sql_identifier(in_addr_col)
            available_fields.append("inputAddress")
            insert_in_sql = f"""
            INSERT OR REPLACE INTO transaction_inputs (
                input_id, transaction_id, dataset_id, input_index,
                input_address, input_value_satoshi
            )
            SELECT 
                {tx_col_expr} || ':0' AS input_id,
                {tx_col_expr} AS transaction_id,
                '{dataset_id}' AS dataset_id,
                0 AS input_index,
                CAST({in_addr_ident} AS VARCHAR) AS input_address,
                {val_expr} AS input_value_satoshi
            FROM {temp_view}
            WHERE {in_addr_ident} IS NOT NULL
            """
            self.conn.execute(insert_in_sql)

        # Populate derived addresses table
        populate_addr_sql = f"""
        INSERT OR REPLACE INTO addresses (
            address_id, dataset_id, first_seen_timestamp, last_seen_timestamp,
            total_received_satoshi, total_sent_satoshi, transaction_count
        )
        SELECT 
            t.addr AS address_id,
            '{dataset_id}' AS dataset_id,
            MIN(t.ts) AS first_seen_timestamp,
            MAX(t.ts) AS last_seen_timestamp,
            SUM(t.recv) AS total_received_satoshi,
            SUM(t.sent) AS total_sent_satoshi,
            COUNT(DISTINCT t.tx_id) AS transaction_count
        FROM (
            SELECT o.output_address AS addr, tx.timestamp AS ts, o.output_value_satoshi AS recv, 0 AS sent, o.transaction_id AS tx_id
            FROM transaction_outputs o
            JOIN transactions tx ON o.transaction_id = tx.transaction_id AND o.dataset_id = tx.dataset_id
            WHERE o.dataset_id = '{dataset_id}' AND o.output_address IS NOT NULL
            UNION ALL
            SELECT i.input_address AS addr, tx.timestamp AS ts, 0 AS recv, i.input_value_satoshi AS sent, i.transaction_id AS tx_id
            FROM transaction_inputs i
            JOIN transactions tx ON i.transaction_id = tx.transaction_id AND i.dataset_id = tx.dataset_id
            WHERE i.dataset_id = '{dataset_id}' AND i.input_address IS NOT NULL
        ) t
        GROUP BY t.addr
        """
        self.conn.execute(populate_addr_sql)

        # Drop temporary view
        self.conn.execute(f"DROP VIEW IF EXISTS {temp_view}")

        # Update dataset status to 'ready'
        validation_summary = {
            "rejectedRows": max(0, row_count - canonical_tx_count),
            "warnedRows": 0,
            "fieldCoverage": {f: 1.0 for f in available_fields},
            "analysisCapability": {
                "graphAnalysis": bool(out_addr_col or in_addr_col),
                "temporalAnalysis": bool(time_col),
            },
        }

        dataset_queries.update_dataset(
            self.conn,
            dataset_id=dataset_id,
            status="ready",
            row_count=row_count,
            canonical_tx_count=canonical_tx_count,
            available_fields=available_fields,
            validation_summary=validation_summary,
        )
        logger.info(f"Dataset {dataset_id} successfully ingested with {canonical_tx_count} transactions.")

    def get_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Retrieve dataset details."""
        return dataset_queries.get_dataset_by_id(self.conn, dataset_id)

    def list_datasets(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "uploadedAt",
        sort_dir: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List all datasets with pagination."""
        return dataset_queries.list_datasets(self.conn, page, page_size, sort_by, sort_dir)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete dataset and all related records, ensuring no analysis is currently running."""
        running_query = "SELECT COUNT(*) FROM analysis_runs WHERE dataset_id = ? AND status = 'running'"
        rel = self.conn.execute(running_query, [dataset_id]).fetchone()
        if rel and rel[0] > 0:
            raise DatasetAnalysisRunningError(f"Cannot delete dataset {dataset_id}: an analysis is currently running.")

        # Remove files from disk
        dataset_dir = Path(settings.DATA_DIR) / dataset_id
        if dataset_dir.exists():
            shutil.rmtree(dataset_dir, ignore_errors=True)

        return dataset_queries.delete_dataset(self.conn, dataset_id)

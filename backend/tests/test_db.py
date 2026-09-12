"""Unit tests for DuckDB database layer and migrations."""

import duckdb
from backend.db.migrations import run_migrations
from backend.db.queries import datasets as dataset_queries


def test_migrations_create_all_tables(db: duckdb.DuckDBPyConnection):
    # Verify all 7 canonical tables exist
    tables = [r[0] for r in db.execute("SHOW TABLES").fetchall()]
    assert "datasets" in tables
    assert "transactions" in tables
    assert "transaction_inputs" in tables
    assert "transaction_outputs" in tables
    assert "addresses" in tables
    assert "analysis_runs" in tables
    assert "ml_results" in tables


def test_dataset_crud_operations(db: duckdb.DuckDBPyConnection):
    # Insert
    ds = dataset_queries.insert_dataset(
        conn=db,
        dataset_id="ds-test-1",
        name="Test Ingestion",
        file_name="tx.csv",
        file_path="/data/tx.csv",
        format_str="csv",
        size_bytes=2048,
    )
    assert ds["dataset_id"] == "ds-test-1"
    assert ds["status"] == "uploaded"

    # Update
    updated = dataset_queries.update_dataset(db, "ds-test-1", status="ready", row_count=100)
    assert updated["status"] == "ready"
    assert updated["row_count"] == 100

    # List
    items, meta = dataset_queries.list_datasets(db)
    assert len(items) == 1
    assert meta["totalItems"] == 1

    # Delete
    assert dataset_queries.delete_dataset(db, "ds-test-1") is True
    items_after, _ = dataset_queries.list_datasets(db)
    assert len(items_after) == 0

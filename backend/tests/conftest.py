"""Pytest fixtures providing isolated test databases, TestClient, and sample data."""

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from typing import Generator
from fastapi.testclient import TestClient
import pytest
import duckdb

from backend.config import settings
from backend.db.connection import close_db, init_db
from backend.db.migrations import run_migrations
from backend.dependencies import get_db
from backend.main import app


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Setup temporary test storage directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        settings.DATA_DIR = str(temp_path / "data")
        settings.MODELS_DIR = str(temp_path / "models")
        settings.DB_PATH = str(temp_path / "test_aquasynex.db")
        settings.ensure_directories()
        init_db(settings.DB_PATH)
        yield
        close_db()


@pytest.fixture
def db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Provide a direct connection to the test DuckDB database with clean tables."""
    conn = duckdb.connect(database=settings.DB_PATH)
    run_migrations(conn)
    # Clean tables between tests
    for tbl in ["network_events", "alerts", "ml_results", "analysis_runs", "addresses", "transaction_outputs", "transaction_inputs", "transactions", "datasets"]:
        try:
            conn.execute(f"DELETE FROM {tbl}")
        except Exception:
            pass
    yield conn
    conn.close()


@pytest.fixture
def client(db: duckdb.DuckDBPyConnection) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with the db dependency overridden."""
    def override_get_db():
        conn = duckdb.connect(database=settings.DB_PATH)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_db(db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    """Seed the database with known test dataset, transactions, addresses, and ML results."""
    dataset_id = "test-dataset-1"
    analysis_id = "test-analysis-1"
    now = datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Insert dataset
    db.execute(
        """
        INSERT INTO datasets (
            dataset_id, name, file_name, file_path, format, size_bytes,
            row_count, canonical_tx_count, uploaded_at, status, available_fields
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            dataset_id,
            "Test Genesis Dataset",
            "test.csv",
            "/tmp/test.csv",
            "csv",
            1024,
            2,
            2,
            now,
            "ready",
            ["transactionId", "timestamp", "outputAddress", "totalOutputValueBtc"],
        ],
    )

    # 2. Insert transactions
    # Tx 1: 50 BTC (5,000,000,000 satoshis)
    # Tx 2: 10 BTC (1,000,000,000 satoshis)
    db.execute(
        """
        INSERT INTO transactions (
            transaction_id, dataset_id, block_height, timestamp, input_count,
            output_count, total_input_value_satoshi, total_output_value_satoshi, fee_satoshi, ingested_at
        ) VALUES 
        ('tx-001', ?, 170, ?, 1, 2, 5000000000, 4999900000, 100000, ?),
        ('tx-002', ?, 171, ?, 1, 1, 1000000000, 999900000, 100000, ?)
        """,
        [dataset_id, now, now, dataset_id, now, now],
    )

    # 3. Insert transaction inputs
    db.execute(
        """
        INSERT INTO transaction_inputs (
            input_id, transaction_id, dataset_id, input_index, input_address, input_value_satoshi
        ) VALUES 
        ('tx-001:0', 'tx-001', ?, 0, 'addr-alice', 5000000000),
        ('tx-002:0', 'tx-002', ?, 0, 'addr-bob', 1000000000)
        """,
        [dataset_id, dataset_id],
    )

    # 4. Insert transaction outputs
    db.execute(
        """
        INSERT INTO transaction_outputs (
            output_id, transaction_id, dataset_id, output_index, output_address, output_value_satoshi, script_type, is_spent
        ) VALUES 
        ('tx-001:0', 'tx-001', ?, 0, 'addr-bob', 4000000000, 'P2PKH', TRUE),
        ('tx-001:1', 'tx-001', ?, 1, 'addr-change', 999900000, 'P2PKH', FALSE),
        ('tx-002:0', 'tx-002', ?, 0, 'addr-charlie', 999900000, 'P2WPKH', FALSE)
        """,
        [dataset_id, dataset_id, dataset_id],
    )

    # 5. Insert derived addresses
    db.execute(
        """
        INSERT INTO addresses (
            address_id, dataset_id, address_type, first_seen_timestamp, last_seen_timestamp,
            total_received_satoshi, total_sent_satoshi, transaction_count
        ) VALUES 
        ('addr-alice', ?, 'P2PKH', ?, ?, 0, 5000000000, 1),
        ('addr-bob', ?, 'P2PKH', ?, ?, 4000000000, 1000000000, 2),
        ('addr-charlie', ?, 'P2WPKH', ?, ?, 999900000, 0, 1)
        """,
        [dataset_id, now, now, dataset_id, now, now, dataset_id, now, now],
    )

    # 6. Insert analysis run
    db.execute(
        """
        INSERT INTO analysis_runs (
            analysis_id, dataset_id, status, started_at, completed_at,
            model_id, model_version, entity_count, high_risk_count, critical_risk_count
        ) VALUES (?, ?, 'completed', ?, ?, 'isolation_forest_v1', '1.0.0', 3, 1, 0)
        """,
        [analysis_id, dataset_id, now, now],
    )

    # 7. Insert ML results
    db.execute(
        """
        INSERT INTO ml_results (
            result_id, analysis_id, dataset_id, entity_id, entity_type,
            anomaly_score, risk_score, risk_level, model_id, model_version, predicted_at,
            explanation_json, features_json, graph_evidence_json
        ) VALUES 
        ('res-001', ?, ?, 'addr-bob', 'address', 0.85, 0.82, 'high', 'isolation_forest_v1', '1.0.0', ?,
         '[{"featureName": "graph_pagerank", "displayLabel": "Network Centrality", "shapValue": 0.23, "direction": "increases_risk", "importanceRank": 1, "normalizedImportance": 1.0, "featureValue": 0.08}]',
         '[{"featureName": "graph_pagerank", "rawValue": 0.08, "normalizedValue": 0.82, "isImputed": false}]',
         '[{"evidenceType": "graph_metric", "label": "Network Centrality", "featureName": "graph_pagerank", "value": 0.08, "description": "High centrality"}]'
        ),
        ('res-002', ?, ?, 'tx-001', 'transaction', 0.78, 0.75, 'high', 'isolation_forest_v1', '1.0.0', ?, '[]', '[]', '[]')
        """,
        [analysis_id, dataset_id, now, analysis_id, dataset_id, now],
    )

    return db

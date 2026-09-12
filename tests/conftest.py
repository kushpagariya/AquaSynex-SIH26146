"""Pytest configuration and fixtures for Frontend ↔ Backend Integration Tests.

CRITICAL INVARIANTS:
1. Isolated temporary DuckDB database - data/aquasynex.db is NEVER touched or corrupted.
2. Clean teardown with explicit connection closure for Windows file lock safety.
3. Real FastAPI TestClient using actual backend router definitions and database execution.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Generator
from fastapi.testclient import TestClient
import pytest
import duckdb

from backend.config import settings
from backend.db.connection import close_db, init_db
from backend.db.migrations import run_migrations
from backend.dependencies import get_db
from backend.main import app


TEST_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TEST_DIR / "fixtures"
SAMPLE_CSV_PATH = FIXTURES_DIR / "sample_bitcoin_dataset.csv"


@pytest.fixture(scope="session", autouse=True)
def test_environment() -> Generator[Path, None, None]:
    """Provide an isolated temporary environment for integration tests."""
    temp_dir = tempfile.mkdtemp(prefix="aquasynex_test_")
    temp_path = Path(temp_dir)

    orig_data_dir = settings.DATA_DIR
    orig_models_dir = settings.MODELS_DIR
    orig_db_path = settings.DB_PATH

    settings.DATA_DIR = str(temp_path / "data")
    settings.MODELS_DIR = str(temp_path / "models")
    settings.DB_PATH = str(temp_path / "test_aquasynex.db")
    settings.ensure_directories()

    # Populate real frozen model artifacts into test models directory
    repo_models = TEST_DIR.parent / "models"
    if repo_models.exists():
        import shutil
        for art in [
            "aquasynex_xgb_binary_v1.json",
            "aquasynex_catboost_multiclass_v1.cbm",
            "preprocessor_v1.joblib",
            "model_metadata.json",
        ]:
            src = repo_models / art
            if src.exists():
                shutil.copy2(src, Path(settings.MODELS_DIR) / art)

    # Initialize connection and schema in the test database
    init_db(settings.DB_PATH)

    try:
        yield temp_path
    finally:
        # Tear down connection to release file lock on Windows
        close_db()
        settings.DATA_DIR = orig_data_dir
        settings.MODELS_DIR = orig_models_dir
        settings.DB_PATH = orig_db_path
        # Clean up temporary directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Provide a direct connection to the test DuckDB database."""
    conn = duckdb.connect(database=settings.DB_PATH)
    yield conn
    conn.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide FastAPI TestClient wired to the isolated test database."""
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


@pytest.fixture(scope="session")
def sample_csv_path() -> Path:
    """Return path to the deterministic sample Bitcoin dataset fixture."""
    assert SAMPLE_CSV_PATH.exists(), f"Sample CSV fixture not found at {SAMPLE_CSV_PATH}"
    return SAMPLE_CSV_PATH


@pytest.fixture(scope="session")
def sample_csv_content(sample_csv_path: Path) -> bytes:
    """Return raw bytes of the deterministic sample Bitcoin dataset."""
    return sample_csv_path.read_bytes()


@pytest.fixture
def uploaded_dataset(client: TestClient, sample_csv_path: Path) -> Dict[str, Any]:
    """Upload and ingest the deterministic sample Bitcoin dataset for test use."""
    with open(sample_csv_path, "rb") as f:
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_bitcoin_dataset.csv", f, "text/csv")},
            data={"name": "Deterministic Bitcoin Integration Test Dataset"},
        )
    assert resp.status_code == 202, f"Dataset upload failed: {resp.text}"
    body = resp.json()
    assert body["success"] is True
    return body["data"]


@pytest.fixture
def uploaded_ml_dataset(client: TestClient, db: duckdb.DuckDBPyConnection, ml_sample_dir: Path) -> Dict[str, Any]:
    """Provide an ingested dataset equipped with canonical network events for real ML integration testing."""
    dataset_id = "test-ml-dataset-1"
    dataset_dir = Path(settings.DATA_DIR) / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # Copy ML sample parquet files into dataset directory
    import shutil
    import pandas as pd
    for fname in [
        "transactions.parquet",
        "transaction_inputs.parquet",
        "transaction_outputs.parquet",
        "network_events.parquet",
        "labels.parquet",
    ]:
        src = ml_sample_dir / fname
        if src.exists():
            shutil.copy2(src, dataset_dir / fname)

    # Ingest into DuckDB test database
    now = datetime.now(timezone.utc)
    db.execute(
        """
        INSERT OR REPLACE INTO datasets (
            dataset_id, name, file_name, file_path, format, size_bytes,
            row_count, canonical_tx_count, uploaded_at, status, available_fields
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            dataset_id,
            "Deterministic ML Benchmark Dataset",
            "transactions.parquet",
            str(dataset_dir / "transactions.parquet"),
            "parquet",
            10240,
            5,
            5,
            now,
            "ready",
            ["transactionId", "timestamp", "networkEvents", "graphAnalysis"],
        ],
    )

    # Read and insert records into DuckDB canonical tables
    con_sample = duckdb.connect()
    df_tx = con_sample.execute(f"SELECT * FROM '{str(dataset_dir / 'transactions.parquet').replace(os.sep, '/')}'").fetchdf()
    df_in = con_sample.execute(f"SELECT * FROM '{str(dataset_dir / 'transaction_inputs.parquet').replace(os.sep, '/')}'").fetchdf()
    df_out = con_sample.execute(f"SELECT * FROM '{str(dataset_dir / 'transaction_outputs.parquet').replace(os.sep, '/')}'").fetchdf()
    df_net = con_sample.execute(f"SELECT * FROM '{str(dataset_dir / 'network_events.parquet').replace(os.sep, '/')}'").fetchdf()
    con_sample.close()

    for _, r in df_tx.iterrows():
        db.execute(
            """
            INSERT OR REPLACE INTO transactions (
                transaction_id, dataset_id, timestamp, input_count, output_count,
                total_input_value_satoshi, total_output_value_satoshi, fee_satoshi,
                transaction_size_bytes, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                r["txid"], dataset_id, r["timestamp"], int(r["input_count"]), int(r["output_count"]),
                int(r["total_input_value_satoshi"]), int(r["total_output_value_satoshi"]), int(r["fee_satoshi"]),
                int(r["transaction_size_bytes"]), now
            ],
        )

    for _, r in df_in.iterrows():
        db.execute(
            """
            INSERT OR REPLACE INTO transaction_inputs (
                input_id, transaction_id, dataset_id, input_index, input_address, input_value_satoshi
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [f"{r['txid']}:{r['input_index']}", r["txid"], dataset_id, int(r["input_index"]), str(r["address"]), int(r["amount_satoshi"])],
        )

    for _, r in df_out.iterrows():
        db.execute(
            """
            INSERT OR REPLACE INTO transaction_outputs (
                output_id, transaction_id, dataset_id, output_index, output_address, output_value_satoshi, is_spent
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [f"{r['txid']}:{r['output_index']}", r["txid"], dataset_id, int(r["output_index"]), str(r["address"]), int(r["amount_satoshi"]), False],
        )

    for _, r in df_net.iterrows():
        db.execute(
            """
            INSERT OR REPLACE INTO network_events (
                event_id, transaction_id, dataset_id, timestamp, timestamp_epoch_sec,
                src_ip, src_port, dst_ip, dst_port, country, asn
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                r["event_id"], r["txid"], dataset_id, r["timestamp"],
                int(pd.to_datetime(r["timestamp"], utc=True).timestamp()),
                r["src_ip"], int(r["src_port"]), r["dst_ip"], int(r["dst_port"]), r["country"], int(r["asn"])
            ],
        )

    # Populate addresses table
    db.execute(
        f"""
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
    )

    return {
        "datasetId": dataset_id,
        "name": "Deterministic ML Benchmark Dataset",
        "status": "ready",
        "rowCount": 5,
        "canonicalTxCount": 5,
    }


ML_SAMPLE_DIR = FIXTURES_DIR / "ml_sample"
MODELS_DIR = TEST_DIR.parent / "models"


def _generate_deterministic_ml_fixtures(target_dir: Path):
    """Generate deterministic 5-transaction multi-entity ML fixture files."""
    import duckdb
    import pandas as pd

    target_dir.mkdir(parents=True, exist_ok=True)
    tx1 = "1" * 64
    tx2 = "2" * 64
    tx3 = "3" * 64
    tx4 = "4" * 64
    tx5 = "5" * 64

    txs = [
        {"txid": tx1, "timestamp": "2026-09-01T10:00:00Z", "input_count": 1, "output_count": 2, "total_input_value_satoshi": 100000000, "total_output_value_satoshi": 99990000, "fee_satoshi": 10000, "transaction_size_bytes": 226, "scenario_id": "scen_norm_1"},
        {"txid": tx2, "timestamp": "2026-09-01T10:05:00Z", "input_count": 1, "output_count": 2, "total_input_value_satoshi": 50000000, "total_output_value_satoshi": 49992000, "fee_satoshi": 8000, "transaction_size_bytes": 226, "scenario_id": "scen_norm_1"},
        {"txid": tx3, "timestamp": "2026-09-01T10:15:00Z", "input_count": 2, "output_count": 2, "total_input_value_satoshi": 80000000, "total_output_value_satoshi": 79985000, "fee_satoshi": 15000, "transaction_size_bytes": 374, "scenario_id": "scen_burst_2"},
        {"txid": tx4, "timestamp": "2026-09-01T10:30:00Z", "input_count": 1, "output_count": 1, "total_input_value_satoshi": 40000000, "total_output_value_satoshi": 39994000, "fee_satoshi": 6000, "transaction_size_bytes": 192, "scenario_id": "scen_peel_3"},
        {"txid": tx5, "timestamp": "2026-09-01T11:00:00Z", "input_count": 2, "output_count": 1, "total_input_value_satoshi": 60000000, "total_output_value_satoshi": 59988000, "fee_satoshi": 12000, "transaction_size_bytes": 340, "scenario_id": "scen_norm_4"}
    ]

    inputs = [
        {"txid": tx1, "input_index": 0, "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "amount_satoshi": 100000000},
        {"txid": tx2, "input_index": 0, "address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "amount_satoshi": 50000000},
        {"txid": tx3, "input_index": 0, "address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "amount_satoshi": 40000000},
        {"txid": tx3, "input_index": 1, "address": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "amount_satoshi": 40000000},
        {"txid": tx4, "input_index": 0, "address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "amount_satoshi": 40000000},
        {"txid": tx5, "input_index": 0, "address": "1CounterpartyXXXXXXXXXXXXXXXUWLpVr", "amount_satoshi": 30000000},
        {"txid": tx5, "input_index": 1, "address": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "amount_satoshi": 30000000},
    ]

    outputs = [
        {"txid": tx1, "output_index": 0, "address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "amount_satoshi": 50000000, "is_change": False},
        {"txid": tx1, "output_index": 1, "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "amount_satoshi": 49990000, "is_change": True},
        {"txid": tx2, "output_index": 0, "address": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "amount_satoshi": 30000000, "is_change": False},
        {"txid": tx2, "output_index": 1, "address": "1BoatSLRHtKNngkdXEeobR76b53LETtpyT", "amount_satoshi": 19992000, "is_change": True},
        {"txid": tx3, "output_index": 0, "address": "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", "amount_satoshi": 50000000, "is_change": False},
        {"txid": tx3, "output_index": 1, "address": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "amount_satoshi": 29985000, "is_change": True},
        {"txid": tx4, "output_index": 0, "address": "1CounterpartyXXXXXXXXXXXXXXXUWLpVr", "amount_satoshi": 39994000, "is_change": False},
        {"txid": tx5, "output_index": 0, "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "amount_satoshi": 59988000, "is_change": False},
    ]

    network = [
        {"event_id": "EVT_001", "txid": tx1, "timestamp": "2026-09-01T10:00:00Z", "src_ip": "1.1.1.1", "src_port": 54321, "dst_ip": "10.0.0.1", "dst_port": 8333, "country": "US", "asn": 15169, "has_network_anomaly": False},
        {"event_id": "EVT_002", "txid": tx2, "timestamp": "2026-09-01T10:05:00Z", "src_ip": "2.2.2.2", "src_port": 54322, "dst_ip": "10.0.0.1", "dst_port": 8333, "country": "DE", "asn": 3320, "has_network_anomaly": False},
        {"event_id": "EVT_003", "txid": tx3, "timestamp": "2026-09-01T10:15:00Z", "src_ip": "3.3.3.3", "src_port": 54323, "dst_ip": "10.0.0.1", "dst_port": 8333, "country": "NL", "asn": 13335, "has_network_anomaly": True},
        {"event_id": "EVT_004", "txid": tx4, "timestamp": "2026-09-01T10:30:00Z", "src_ip": "4.4.4.4", "src_port": 54324, "dst_ip": "10.0.0.1", "dst_port": 8333, "country": "US", "asn": 15169, "has_network_anomaly": False},
        {"event_id": "EVT_005", "txid": tx5, "timestamp": "2026-09-01T11:00:00Z", "src_ip": "5.5.5.5", "src_port": 54325, "dst_ip": "10.0.0.1", "dst_port": 8333, "country": "FR", "asn": 16509, "has_network_anomaly": False},
    ]

    labels = [
        {"txid": tx1, "entity_id": "ENT_001", "scenario_id": "scen_norm_1", "behavior_type": "normal", "ground_truth_label": 0},
        {"txid": tx2, "entity_id": "ENT_001", "scenario_id": "scen_norm_1", "behavior_type": "normal", "ground_truth_label": 0},
        {"txid": tx3, "entity_id": "ENT_002", "scenario_id": "scen_burst_2", "behavior_type": "transaction_burst", "ground_truth_label": 1},
        {"txid": tx4, "entity_id": "ENT_003", "scenario_id": "scen_peel_3", "behavior_type": "peeling_chain", "ground_truth_label": 1},
        {"txid": tx5, "entity_id": "ENT_004", "scenario_id": "scen_norm_4", "behavior_type": "normal", "ground_truth_label": 0},
    ]

    con = duckdb.connect()
    for name, data in [
        ("transactions", txs),
        ("transaction_inputs", inputs),
        ("transaction_outputs", outputs),
        ("network_events", network),
        ("labels", labels)
    ]:
        df = pd.DataFrame(data)
        con.register("temp_df", df)
        out_file = (target_dir / f"{name}.parquet").as_posix()
        con.execute(f"COPY temp_df TO '{out_file}' (FORMAT PARQUET)")
        con.unregister("temp_df")
    con.close()


@pytest.fixture(scope="session")
def ml_sample_dir() -> Path:
    """Return path to deterministic ML sample parquet directory, auto-generating if needed."""
    required_files = [
        "transactions.parquet",
        "transaction_inputs.parquet",
        "transaction_outputs.parquet",
        "network_events.parquet",
        "labels.parquet"
    ]
    if not all((ML_SAMPLE_DIR / f).exists() for f in required_files):
        _generate_deterministic_ml_fixtures(ML_SAMPLE_DIR)

    return ML_SAMPLE_DIR


@pytest.fixture(scope="session")
def models_dir() -> Path:
    """Return path to models artifact directory."""
    assert MODELS_DIR.exists(), f"Models dir not found at {MODELS_DIR}"
    return MODELS_DIR


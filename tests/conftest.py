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


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

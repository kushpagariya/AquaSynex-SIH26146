"""Regression test for sih_transactions_sample.csv upload and analysis.

Verifies:
1. Exact schema ingestion from sih_transactions_sample.csv (nested list address & amount strings).
2. Proper decomposition into canonical DuckDB tables (transactions, inputs, outputs, addresses, network events).
3. Thread-safe execution and persistence of ML inference and risk analysis.
4. Process stability with no DuckDB crashes or access violations.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi.testclient import TestClient
import duckdb
import pytest

from backend.config import settings


def test_sih_transactions_sample_upload_and_ingestion(
    client: TestClient, db: duckdb.DuckDBPyConnection
):
    """Verify end-to-end ingestion and DuckDB decomposition of sih_transactions_sample.csv."""
    sample_file = Path(settings.DATA_DIR) / "sample" / "sih_transactions_sample.csv"
    if not sample_file.exists():
        # Also check root data/sample
        sample_file = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "sih_transactions_sample.csv"
    assert sample_file.exists(), f"Sample file not found at {sample_file}"

    # 1. Upload the CSV file via the API
    with open(sample_file, "rb") as f:
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sih_transactions_sample.csv", f, "text/csv")},
            data={"name": "SIH Sample Regression Dataset"},
        )
    assert resp.status_code == 202, f"Upload failed: {resp.text}"
    body = resp.json()
    assert body["success"] is True
    dataset_id = body["data"]["datasetId"]

    # 2. Verify dataset record in DuckDB
    ds_row = db.execute(
        "SELECT name, status, row_count, canonical_tx_count FROM datasets WHERE dataset_id = ?",
        [dataset_id],
    ).fetchone()
    assert ds_row is not None
    assert ds_row[0] == "SIH Sample Regression Dataset"
    assert ds_row[1] == "ready"
    assert ds_row[2] == 500
    assert ds_row[3] == 500

    # 3. Verify transactions table
    tx_count = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert tx_count == 500

    # Verify no NULLs in input/output values
    null_vals = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE dataset_id = ? AND (total_input_value_satoshi IS NULL OR total_output_value_satoshi IS NULL)",
        [dataset_id],
    ).fetchone()[0]
    assert null_vals == 0

    # 4. Verify transaction inputs and outputs tables
    in_count = db.execute(
        "SELECT COUNT(*) FROM transaction_inputs WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert in_count == 683

    out_count = db.execute(
        "SELECT COUNT(*) FROM transaction_outputs WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert out_count == 1519

    # 5. Verify addresses table
    addr_count = db.execute(
        "SELECT COUNT(*) FROM addresses WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert addr_count == 1839

    # 6. Verify network events table
    net_count = db.execute(
        "SELECT COUNT(*) FROM network_events WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert net_count == 500

    # 7. Verify concurrent reads do not crash DuckDB
    def fetch_datasets():
        res = client.get("/api/datasets")
        assert res.status_code == 200
        return len(res.json()["data"])

    def fetch_transactions():
        res = client.get(f"/api/datasets/{dataset_id}/transactions?limit=50")
        assert res.status_code == 200
        return len(res.json()["data"])

    with ThreadPoolExecutor(max_workers=4) as executor:
        futs = [
            executor.submit(fetch_datasets),
            executor.submit(fetch_transactions),
            executor.submit(fetch_datasets),
            executor.submit(fetch_transactions),
        ]
        results = [f.result() for f in futs]
    assert results[0] >= 1
    assert results[1] == 50


def test_sih_transactions_sample_ml_analysis_run(
    client: TestClient, db: duckdb.DuckDBPyConnection
):
    """Verify that ML analysis runs cleanly on sih_transactions_sample.csv without crashing."""
    sample_file = Path(settings.DATA_DIR) / "sample" / "sih_transactions_sample.csv"
    if not sample_file.exists():
        sample_file = Path(__file__).resolve().parent.parent.parent / "data" / "sample" / "sih_transactions_sample.csv"

    # Upload
    with open(sample_file, "rb") as f:
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sih_transactions_sample.csv", f, "text/csv")},
            data={"name": "SIH Sample ML Run Dataset"},
        )
    assert resp.status_code == 202
    dataset_id = resp.json()["data"]["datasetId"]

    # Trigger ML analysis with XGBoost binary model
    analysis_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={
            "model_id": "aquasynex_xgb_binary_v1",
            "model_version": "1.0.0",
        },
    )
    assert analysis_resp.status_code == 202
    analysis_id = analysis_resp.json()["data"]["analysisId"]

    # Check analysis status and details
    get_analysis = client.get(f"/api/analyses/{analysis_id}")
    assert get_analysis.status_code == 200
    analysis_data = get_analysis.json()["data"]
    assert analysis_data["status"] == "completed"
    assert analysis_data["entityCount"] == 500

    # Verify ml_results in DuckDB
    res_count = db.execute(
        "SELECT COUNT(*) FROM ml_results WHERE analysis_id = ?", [analysis_id]
    ).fetchone()[0]
    assert res_count == 500

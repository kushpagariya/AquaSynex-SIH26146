"""Dataset Upload Flow Integration Test.

Tests real end-to-end ingestion:
Client multipart upload -> file storage -> DuckDB table population -> metadata update.
"""

from pathlib import Path
from fastapi.testclient import TestClient
import duckdb


def test_dataset_upload_and_database_persistence_flow(
    client: TestClient, db: duckdb.DuckDBPyConnection, sample_csv_path: Path
):
    """Verify that uploading sample_bitcoin_dataset.csv populates all canonical DuckDB tables."""
    dataset_name = "End-to-End Ingestion Flow Dataset"
    with open(sample_csv_path, "rb") as f:
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_bitcoin_dataset.csv", f, "text/csv")},
            data={"name": dataset_name},
        )
    assert resp.status_code == 202
    body = resp.json()
    assert body["success"] is True
    dataset_id = body["data"]["datasetId"]

    # 1. Verify dataset row in DuckDB
    ds_row = db.execute(
        "SELECT name, status, row_count, canonical_tx_count FROM datasets WHERE dataset_id = ?",
        [dataset_id],
    ).fetchone()
    assert ds_row is not None
    assert ds_row[0] == dataset_name
    assert ds_row[1] == "ready"
    assert ds_row[2] == 5
    assert ds_row[3] == 5

    # 2. Verify transactions table in DuckDB
    tx_count = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert tx_count == 5

    # 3. Verify inputs and outputs tables in DuckDB
    in_count = db.execute(
        "SELECT COUNT(*) FROM transaction_inputs WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert in_count == 5

    out_count = db.execute(
        "SELECT COUNT(*) FROM transaction_outputs WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert out_count == 5

    # 4. Verify addresses table in DuckDB
    addr_count = db.execute(
        "SELECT COUNT(*) FROM addresses WHERE dataset_id = ?", [dataset_id]
    ).fetchone()[0]
    assert addr_count == 5

    # 5. Verify total satoshis and balances
    recv_sum = db.execute(
        "SELECT SUM(total_received_satoshi) FROM addresses WHERE dataset_id = ?",
        [dataset_id],
    ).fetchone()[0]
    # Sum of all transaction values: 50 + 30 + 20 + 10 + 15 = 125 BTC = 12,500,000,000 satoshis
    assert recv_sum == 12_500_000_000

"""Comprehensive regression and verification tests for second-pass hardening and contract fixes."""

from datetime import datetime, timezone
import io
import uuid
import pytest
from fastapi.testclient import TestClient
import duckdb

from backend.schemas.common import ApiError, ApiResponse
from backend.schemas.analyses import AnalysisConfigSchema, AnalysisRequest
from backend.services.pipeline_service import PipelineService, set_pipeline_runner, reset_pipeline_runner
from backend.services.graph_service import GraphService
from backend.utils.converters import satoshi_to_btc_str, btc_str_to_satoshi
from backend.utils.errors import GraphNotAvailableError, MLError, ValidationError, AnalysisNotFoundError
from backend.db.queries import addresses as address_queries
from backend.db.queries import transactions as transaction_queries
from backend.db.queries import results as result_queries


def test_converters_reject_non_integral_satoshi():
    """Verify satoshi_to_btc_str rejects non-integral satoshi values."""
    assert satoshi_to_btc_str(100) == "0.00000100"
    assert satoshi_to_btc_str(100.0) == "0.00000100"
    assert satoshi_to_btc_str("100") == "0.00000100"
    assert satoshi_to_btc_str(None) is None

    with pytest.raises(ValueError, match="must be an integer"):
        satoshi_to_btc_str(1.9)

    with pytest.raises(ValueError, match="must be an integer"):
        satoshi_to_btc_str("2.5")


def test_converters_reject_sub_satoshi_precision():
    """Verify btc_str_to_satoshi rejects values with sub-satoshi precision."""
    assert btc_str_to_satoshi("0.00000001") == 1
    assert btc_str_to_satoshi("1.00000000") == 100_000_000

    with pytest.raises(ValueError, match="Sub-satoshi precision is not supported"):
        btc_str_to_satoshi("0.000000001")

    with pytest.raises(ValueError, match="Sub-satoshi precision is not supported"):
        btc_str_to_satoshi(0.000000001)


def test_api_response_envelope_invariant():
    """Verify ApiResponse enforces envelope invariants for success and error pairing."""
    # Valid success
    resp = ApiResponse(success=True, data={"key": "val"})
    assert resp.success is True
    assert resp.error is None

    # Valid failure
    err = ApiError(code="TEST_ERR", message="Something broke")
    resp_err = ApiResponse(success=False, error=err)
    assert resp_err.success is False
    assert resp_err.error.code == "TEST_ERR"

    # Invalid: success=True with error
    with pytest.raises(ValueError, match="Successful response must not contain an error"):
        ApiResponse(success=True, data={"key": "val"}, error=err)

    # Invalid: success=False without error
    with pytest.raises(ValueError, match="Failed response must contain an error"):
        ApiResponse(success=False, data=None)


def test_analysis_request_config_schema_validation(client: TestClient, seeded_db):
    """Verify AnalysisRequest config validates maxEntities and known constraints."""
    # maxEntities = 0 violates ge=1
    res = client.post(
        "/api/datasets/test-dataset-1/analyses",
        json={"config": {"maxEntities": 0}},
    )
    assert res.status_code == 400
    res_data = res.json()
    assert res_data["success"] is False
    assert res_data["error"]["code"] == "VALIDATION_ERROR"


def test_upload_filename_with_quotes_rejected(client: TestClient):
    """Verify uploaded filenames with quote characters are rejected."""
    csv_content = b"transaction_id,timestamp,value\ntx1,1600000000,1000\n"
    
    # Single quote
    res_single = client.post(
        "/api/datasets/upload",
        data={"name": "Quote Test 1"},
        files={"file": ("test'file.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert res_single.status_code == 400
    assert "Filename must not contain quotes" in res_single.json()["error"]["message"]

    # Double quote
    res_double = client.post(
        "/api/datasets/upload",
        data={"name": "Quote Test 2"},
        files={"file": ('test"file.csv', io.BytesIO(csv_content), "text/csv")},
    )
    assert res_double.status_code == 400
    assert "Filename must not contain quotes" in res_double.json()["error"]["message"]


def test_query_deduplication_across_multiple_analyses(seeded_db: duckdb.DuckDBPyConnection):
    """Verify list_addresses and list_transactions do not duplicate items when multiple analyses exist."""
    # Seed a second analysis with a newer prediction for addr-bob and tx-001
    analysis2_id = "test-analysis-2"
    seeded_db.execute(
        "INSERT INTO analysis_runs (analysis_id, dataset_id, status, model_id, model_version, started_at) "
        "VALUES (?, 'test-dataset-1', 'completed', 'isolation_forest_v1', '1.0.0', current_timestamp)",
        [analysis2_id],
    )
    # Insert second result for addr-bob with higher risk
    result_queries.insert_ml_result(
        conn=seeded_db,
        result_id=str(uuid.uuid4()),
        analysis_id=analysis2_id,
        dataset_id="test-dataset-1",
        entity_id="addr-bob",
        entity_type="address",
        anomaly_score=0.99,
        risk_score=0.99,
        risk_level="critical",
        model_id="isolation_forest_v1",
        model_version="1.0.0",
        predicted_at=datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc),
    )
    # Insert second result for tx-001
    result_queries.insert_ml_result(
        conn=seeded_db,
        result_id=str(uuid.uuid4()),
        analysis_id=analysis2_id,
        dataset_id="test-dataset-1",
        entity_id="tx-001",
        entity_type="transaction",
        anomaly_score=0.99,
        risk_score=0.99,
        risk_level="critical",
        model_id="isolation_forest_v1",
        model_version="1.0.0",
        predicted_at=datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc),
    )

    # 1. Query addresses without analysis_id -> should have exact same address count (3 addresses in seeded_db: alice, bob, charlie)
    items, meta = address_queries.list_addresses(
        conn=seeded_db,
        dataset_id="test-dataset-1",
        page=1,
        page_size=50,
    )
    assert meta["totalItems"] == 3
    bob = next(item for item in items if item["address_id"] == "addr-bob")
    # Latest prediction was 0.99
    assert bob["risk_score"] == 0.99
    assert bob["risk_level"] == "critical"

    # 2. Query transactions without analysis_id -> should have exact transaction count (2 in seeded_db: tx-001, tx-002)
    tx_items, tx_meta = transaction_queries.list_transactions(
        conn=seeded_db,
        dataset_id="test-dataset-1",
        page=1,
        page_size=50,
    )
    assert tx_meta["totalItems"] == 2
    tx1 = next(item for item in tx_items if item["transaction_id"] == "tx-001")
    assert tx1["risk_score"] == 0.99


def test_subgraph_rejects_missing_address_or_invalid_analysis(seeded_db: duckdb.DuckDBPyConnection):
    """Verify get_address_subgraph raises GraphNotAvailableError or AnalysisNotFoundError."""
    svc = GraphService(seeded_db)

    # Nonexistent address in dataset
    with pytest.raises(GraphNotAvailableError):
        svc.get_address_subgraph("nonexistent-address", hops=1, analysis_id="test-analysis-1")

    # Invalid analysis_id must raise AnalysisNotFoundError rather than being swallowed
    with pytest.raises(AnalysisNotFoundError):
        svc.get_address_subgraph("addr-bob", hops=1, analysis_id="invalid-analysis-id")


def test_pipeline_service_score_conversion_and_transaction_rollback(seeded_db: duckdb.DuckDBPyConnection):
    """Verify score validation raises MLError on non-numeric input and rolls back partial persistence."""
    svc = PipelineService(seeded_db)

    # 1. Test _as_score directly
    with pytest.raises(MLError, match="must be numeric"):
        svc._as_score("risk_score", "not_a_number")

    with pytest.raises(MLError, match="between 0.0 and 1.0"):
        svc._as_score("risk_score", 1.5)

    with pytest.raises(MLError, match="is required"):
        svc._as_score("risk_score", None, required=True)

    # 2. Test batch validation: if second item is invalid, neither should be persisted
    bad_batch = [
        {
            "entity_id": "tx-good",
            "entity_type": "transaction",
            "anomaly_score": 0.5,
            "risk_score": 0.5,
            "risk_level": "medium",
        },
        {
            "entity_id": "tx-bad",
            "entity_type": "transaction",
            "anomaly_score": "bad_score",
            "risk_score": 0.5,
            "risk_level": "medium",
        },
    ]

    set_pipeline_runner(lambda **kwargs: bad_batch)
    try:
        with pytest.raises(MLError):
            svc.run_analysis(
                dataset_id="test-dataset-1",
                analysis_id="rollback-test",
                model_id="isolation_forest_v1",
                model_version="1.0.0",
                config=AnalysisConfigSchema(),
            )

        # Confirm tx-good was not persisted
        persisted = seeded_db.execute(
            "SELECT COUNT(*) FROM ml_results WHERE analysis_id = 'rollback-test'"
        ).fetchone()[0]
        assert persisted == 0
    finally:
        reset_pipeline_runner()

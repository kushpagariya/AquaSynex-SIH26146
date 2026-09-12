"""ML ↔ Backend Integration Test Suite.

Authoritative reference: docs/backend/backend-ml-contract.md, docs/ml/model-output-contract.md.
Rules:
- Tests the complete bridge between FastAPI backend and ML subsystem.
- Real model artifacts (XGBoost, CatBoost, preprocessor) and deterministic fixtures.
- Zero mocked model predictions.
- Strict dataset isolation verification.
- Enforce that failures transition to 'failed' state without fake results.
"""

from datetime import datetime, timezone
import importlib
from pathlib import Path
from typing import Any, Dict, List
import duckdb
from fastapi.testclient import TestClient
import pytest

from backend.config import settings
from backend.services.pipeline_service import PipelineService
from backend.utils.errors import ModelLoadError, ModelNotFoundError


def test_01_ml_adapter_import():
    """Verify that backend can discover and import the ML pipeline entrypoint callable."""
    mod = importlib.import_module("pipeline.ml.model_inference")
    assert hasattr(mod, "run_analysis")
    run_func = getattr(mod, "run_analysis")
    assert callable(run_func)


def test_02_model_discovery(client: TestClient):
    """Verify that GET /api/models discovers and lists the production XGBoost model."""
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    models = body["data"]

    model_ids = [m["modelId"] for m in models]
    assert "aquasynex_xgb_binary_v1" in model_ids or "aquasynex_v1" in model_ids

    xgb_model = next(m for m in models if m["modelId"] in ("aquasynex_xgb_binary_v1", "aquasynex_v1"))
    assert xgb_model["modelVersion"] == "1.0.0"
    assert "XGBoost" in xgb_model["algorithm"]


def test_03_invalid_model_request(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify that requesting an unregistered/unsupported model raises a controlled error."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "non_existent_algorithm_v99", "modelVersion": "99.0.0"},
    )
    # ModelNotFoundError returns 404 from the API route
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "MODEL_NOT_FOUND" in body["error"]["code"] or "not found" in body["error"]["message"].lower()


def test_04_dataset_isolation(client: TestClient, db: duckdb.DuckDBPyConnection, uploaded_ml_dataset: Dict[str, Any]):
    """Verify that analysis of dataset A never consumes, processes, or persists data from dataset B."""
    dataset_a_id = uploaded_ml_dataset["datasetId"]
    dataset_b_id = "isolated-dataset-b"

    now = datetime.now(timezone.utc)
    # Insert dataset B with distinct transaction and network telemetry
    tx_b = "b" * 64
    db.execute(
        """
        INSERT OR REPLACE INTO datasets (
            dataset_id, name, file_name, file_path, format, size_bytes,
            row_count, canonical_tx_count, uploaded_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [dataset_b_id, "Dataset B", "tx_b.parquet", "tx_b.parquet", "parquet", 1024, 1, 1, now, "ready"],
    )
    db.execute(
        """
        INSERT OR REPLACE INTO transactions (
            transaction_id, dataset_id, timestamp, input_count, output_count,
            total_input_value_satoshi, total_output_value_satoshi, fee_satoshi,
            transaction_size_bytes, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [tx_b, dataset_b_id, "2026-09-01T12:00:00Z", 1, 1, 50000000, 49990000, 10000, 226, now],
    )
    db.execute(
        """
        INSERT OR REPLACE INTO transaction_inputs (
            input_id, transaction_id, dataset_id, input_index, input_address, input_value_satoshi
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        [f"{tx_b}:0", tx_b, dataset_b_id, 0, "1IsolatedAddressDatasetB", 50000000],
    )
    db.execute(
        """
        INSERT OR REPLACE INTO transaction_outputs (
            output_id, transaction_id, dataset_id, output_index, output_address, output_value_satoshi, is_spent
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [f"{tx_b}:0", tx_b, dataset_b_id, 0, "1DestinationAddressDatasetB", 49990000, False],
    )
    db.execute(
        """
        INSERT OR REPLACE INTO network_events (
            event_id, transaction_id, dataset_id, timestamp, timestamp_epoch_sec,
            src_ip, src_port, dst_ip, dst_port, country, asn
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ["EVT_B_001", tx_b, dataset_b_id, "2026-09-01T12:00:00Z", 1788264000, "9.9.9.9", 54329, "10.0.0.1", 8333, "US", 15169],
    )

    # Trigger analysis on Dataset A
    trigger_resp = client.post(
        f"/api/datasets/{dataset_a_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    assert trigger_resp.status_code == 202
    analysis_a_id = trigger_resp.json()["data"]["analysisId"]

    # Verify results of Analysis A
    results_resp = client.get(f"/api/analyses/{analysis_a_id}/results")
    assert results_resp.status_code == 200
    results_a = results_resp.json()["data"]

    # Invariant: None of the results from analysis A reference Dataset B's transaction
    entity_ids = [r["entityId"] for r in results_a]
    assert tx_b not in entity_ids
    assert len(entity_ids) == 5

    # Check database rows for contamination
    db_results = db.execute(
        "SELECT entity_id, dataset_id FROM ml_results WHERE analysis_id = ?",
        [analysis_a_id],
    ).fetchall()
    assert all(row[1] == dataset_a_id for row in db_results)
    assert not any(row[0] == tx_b for row in db_results)


def test_05_analysis_creation(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify that POST /api/datasets/{id}/analyses returns 202 Accepted with analysisId."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={
            "modelId": "aquasynex_xgb_binary_v1",
            "modelVersion": "1.0.0",
            "config": {"maxEntities": 5, "topExplanations": 3},
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["success"] is True
    assert "analysisId" in body["data"]
    assert body["data"]["status"] in ("pending", "running", "completed")


def test_06_real_ml_execution_and_persistence(client: TestClient, db: duckdb.DuckDBPyConnection, uploaded_ml_dataset: Dict[str, Any]):
    """Execute end-to-end ML pipeline with real model artifacts and verify complete persistence in DuckDB."""
    dataset_id = uploaded_ml_dataset["datasetId"]

    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    assert trigger_resp.status_code == 202
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    # Check analysis record in database
    analysis_row = db.execute(
        "SELECT status, entity_count, high_risk_count, critical_risk_count, error_message FROM analysis_runs WHERE analysis_id = ?",
        [analysis_id],
    ).fetchone()
    assert analysis_row is not None
    assert analysis_row[0] == "completed", f"Analysis failed with error: {analysis_row[4]}"
    assert analysis_row[1] == 5  # 5 transactions analyzed

    # Verify results in ml_results table
    res_rows = db.execute(
        "SELECT entity_id, entity_type, anomaly_score, risk_score, risk_level, prediction_label, confidence FROM ml_results WHERE analysis_id = ?",
        [analysis_id],
    ).fetchall()
    assert len(res_rows) == 5

    for row in res_rows:
        entity_id, entity_type, anomaly_score, risk_score, risk_level, pred_label, confidence = row
        assert entity_type == "transaction"
        assert len(entity_id) == 64
        assert 0.0 <= anomaly_score <= 1.0
        assert 0.0 <= risk_score <= 1.0
        assert risk_level in ("low", "medium", "high", "critical")
        assert pred_label is not None
        assert 0.0 <= confidence <= 1.0


def test_07_result_schema_validation(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify each result satisfies backend PipelineService validation invariants."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    assert results_resp.status_code == 200
    results = results_resp.json()["data"]
    assert len(results) == 5

    pipeline_service = PipelineService(conn=None)
    for r in results:
        # Convert camelCase API response to snake_case for internal validator check
        internal_payload = {
            "entity_id": r["entityId"],
            "entity_type": r["entityType"],
            "anomaly_score": r["anomalyScore"],
            "risk_score": r["riskScore"],
            "risk_level": r["riskLevel"],
            "prediction_label": r.get("predictionLabel"),
        }
        pipeline_service._validate_ml_result(internal_payload)


def test_08_xgboost_probability_properties(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify XGBoost prediction outputs non-trivial, continuous risk probabilities."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    results = results_resp.json()["data"]

    scores = [r["riskScore"] for r in results]
    assert len(scores) == 5
    assert all(isinstance(s, (float, int)) for s in scores)
    assert all(0.0 <= s <= 1.0 for s in scores)
    # Verify scores are not all identical dummy numbers
    assert len(set(scores)) >= 2


def test_09_catboost_typology_and_confidence(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify CatBoost multiclass typology labels and confidence values are present on entity detail."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    results = results_resp.json()["data"]
    first_entity_id = results[0]["entityId"]

    # Query detailed result for the entity
    detail_resp = client.get(f"/api/analyses/{analysis_id}/results/{first_entity_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]

    assert "predictionLabel" in detail
    assert detail["predictionLabel"] is not None
    assert isinstance(detail["predictionLabel"], str)
    assert "confidence" in detail
    assert detail["confidence"] is not None
    assert 0.0 <= detail["confidence"] <= 1.0


def test_10_treeshap_explanations(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify that real TreeSHAP explanations are computed, ranked, and persisted."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={
            "modelId": "aquasynex_xgb_binary_v1",
            "modelVersion": "1.0.0",
            "config": {"topExplanations": 5},
        },
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    first_entity_id = results_resp.json()["data"][0]["entityId"]

    detail_resp = client.get(f"/api/analyses/{analysis_id}/results/{first_entity_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]

    explanations = detail.get("explanations", [])
    assert len(explanations) == 5

    # Verify structure and ordering by importanceRank
    for rank, exp in enumerate(explanations, start=1):
        assert exp["importanceRank"] == rank
        assert "featureName" in exp
        assert "displayLabel" in exp
        assert isinstance(exp["shapValue"], (float, int))
        assert exp["direction"] in ("increases_risk", "decreases_risk", "neutral")
        assert 0.0 <= exp["normalizedImportance"] <= 1.0


def test_11_graph_evidence(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify that real graph-derived evidence is produced and serialized."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    first_entity_id = results_resp.json()["data"][0]["entityId"]

    detail_resp = client.get(f"/api/analyses/{analysis_id}/results/{first_entity_id}")
    detail = detail_resp.json()["data"]

    graph_evidence = detail.get("graphEvidence", [])
    assert len(graph_evidence) >= 1

    feature_names = [e["featureName"] for e in graph_evidence]
    assert "hist_cluster_size" in feature_names or "hist_component_size" in feature_names

    for item in graph_evidence:
        assert "evidenceType" in item
        assert "label" in item
        assert "value" in item
        assert "description" in item
        assert len(item["description"]) > 0


def test_12_controlled_ml_failure_without_fake_predictions(client: TestClient, db: duckdb.DuckDBPyConnection, sample_csv_path: Path):
    """Verify that analyzing a dataset without required network telemetry triggers a controlled failure without fake results."""
    with open(sample_csv_path, "rb") as f:
        upload_resp = client.post(
            "/api/datasets/upload",
            files={"file": ("sample_bitcoin_dataset.csv", f, "text/csv")},
            data={"name": "No-Network Telemetry Bitcoin Dataset"},
        )
    dataset_id = upload_resp.json()["data"]["datasetId"]

    # Trigger ML analysis
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    # Poll status
    status_resp = client.get(f"/api/analyses/{analysis_id}")
    analysis = status_resp.json()["data"]

    assert analysis["status"] == "failed"
    assert analysis["errorMessage"] is not None
    assert "network telemetry" in analysis["errorMessage"].lower() or "missing" in analysis["errorMessage"].lower()

    # Verify zero fake results were written
    results_resp = client.get(f"/api/analyses/{analysis_id}/results")
    assert results_resp.status_code == 200
    assert len(results_resp.json()["data"]) == 0

    count_row = db.execute("SELECT COUNT(*) FROM ml_results WHERE analysis_id = ?", [analysis_id]).fetchone()
    assert count_row[0] == 0


def test_13_end_to_end_investigator_workflow(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Full 14-step investigator journey using real ML model execution."""
    dataset_id = uploaded_ml_dataset["datasetId"]

    # 1. Health check
    health = client.get("/api/health").json()
    assert health["success"] is True

    # 2. Dataset inspect
    dataset = client.get(f"/api/datasets/{dataset_id}").json()["data"]
    assert dataset["status"] == "ready"

    # 3. Model list
    models = client.get("/api/models").json()["data"]
    chosen_model = next(m for m in models if m["modelId"] in ("aquasynex_xgb_binary_v1", "aquasynex_v1"))

    # 4. Trigger analysis
    trigger = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": chosen_model["modelId"], "modelVersion": chosen_model["modelVersion"]},
    ).json()["data"]
    analysis_id = trigger["analysisId"]

    # 5. Check completion
    analysis = client.get(f"/api/analyses/{analysis_id}").json()["data"]
    assert analysis["status"] == "completed"
    assert analysis["entityCount"] == 5

    # 6. Query results
    results = client.get(f"/api/analyses/{analysis_id}/results").json()["data"]
    assert len(results) == 5

    # 7. Entity detail
    top_entity = results[0]["entityId"]
    entity_detail = client.get(f"/api/analyses/{analysis_id}/results/{top_entity}").json()["data"]
    assert entity_detail["entityId"] == top_entity
    assert len(entity_detail["explanations"]) > 0

    # 8. Graph endpoint remains fully functional
    graph = client.get(f"/api/analyses/{analysis_id}/graph").json()["data"]
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0


def test_14_risk_level_mapping_boundaries():
    """Verify exact boundary behavior for risk level mapping function."""
    from pipeline.ml.model_inference import map_risk_level

    # Test critical boundaries (>= 0.90)
    assert map_risk_level(1.00) == "critical"
    assert map_risk_level(0.95) == "critical"
    assert map_risk_level(0.90) == "critical"
    assert map_risk_level(0.899999) == "high"

    # Test high boundaries (>= 0.70)
    assert map_risk_level(0.89) == "high"
    assert map_risk_level(0.70) == "high"
    assert map_risk_level(0.699999) == "medium"

    # Test medium boundaries (>= 0.40)
    assert map_risk_level(0.69) == "medium"
    assert map_risk_level(0.40) == "medium"
    assert map_risk_level(0.399999) == "low"

    # Test low boundaries (< 0.40)
    assert map_risk_level(0.39) == "low"
    assert map_risk_level(0.00) == "low"


def test_15_frontend_contract_field_alignment(client: TestClient, uploaded_ml_dataset: Dict[str, Any]):
    """Verify that result fields strictly align with frontend TypeScript MLResultDetail definition."""
    dataset_id = uploaded_ml_dataset["datasetId"]
    trigger_resp = client.post(
        f"/api/datasets/{dataset_id}/analyses",
        json={"modelId": "aquasynex_xgb_binary_v1", "modelVersion": "1.0.0"},
    )
    analysis_id = trigger_resp.json()["data"]["analysisId"]

    results = client.get(f"/api/analyses/{analysis_id}/results").json()["data"]
    entity_id = results[0]["entityId"]

    detail = client.get(f"/api/analyses/{analysis_id}/results/{entity_id}").json()["data"]

    # Frontend MLResultSummary fields
    assert "entityId" in detail and isinstance(detail["entityId"], str)
    assert "entityType" in detail and detail["entityType"] in ("transaction", "address")
    assert "anomalyScore" in detail and isinstance(detail["anomalyScore"], (float, int))
    assert "riskScore" in detail and isinstance(detail["riskScore"], (float, int))
    assert "riskLevel" in detail and detail["riskLevel"] in ("low", "medium", "high", "critical")
    assert "predictionLabel" in detail
    assert "modelId" in detail and detail["modelId"] == "aquasynex_xgb_binary_v1"
    assert "modelVersion" in detail and detail["modelVersion"] == "1.0.0"
    assert "predictedAt" in detail

    # Frontend MLResultDetail extensions
    assert "confidence" in detail
    assert "explanations" in detail and isinstance(detail["explanations"], list)
    assert "features" in detail and isinstance(detail["features"], list)
    assert "graphEvidence" in detail and isinstance(detail["graphEvidence"], list)

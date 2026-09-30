"""Comprehensive test suite for the DuckDB Alert Management System."""

import json
from datetime import datetime, timezone, timedelta
import duckdb
from fastapi.testclient import TestClient
import pytest

from backend.services.alert_engine import AlertEngine, ALL_FROZEN_CATBOOST_CLASSES
from backend.services.alert_service import AlertService


def test_frozen_behavior_classes():
    """Verify that ONLY the 11 frozen CatBoost behavior classes are recognized."""
    expected = {
        "normal",
        "benign_high_volume",
        "transaction_burst",
        "rapid_multihop",
        "peeling_chain",
        "coordinated_activity",
        "high_fan_in",
        "high_fan_out",
        "temporal_anomaly",
        "mixing_like",
        "amount_anomaly",
    }
    assert ALL_FROZEN_CATBOOST_CLASSES == expected
    assert "mixer_interaction" not in ALL_FROZEN_CATBOOST_CLASSES
    assert "scatter_gather" not in ALL_FROZEN_CATBOOST_CLASSES
    assert "cyclic_flow" not in ALL_FROZEN_CATBOOST_CLASSES
    assert "high_fee_anomaly" not in ALL_FROZEN_CATBOOST_CLASSES


def test_alerts_schema_and_indexes(db: duckdb.DuckDBPyConnection):
    """Verify that the alerts table and all required indexes exist with correct schema."""
    cols = db.execute("PRAGMA table_info('alerts')").fetchall()
    col_names = {c[1] for c in cols}
    required_cols = {
        "alert_id",
        "analysis_id",
        "dataset_id",
        "fingerprint",
        "grouping_key",
        "transaction_id",
        "entity_id",
        "entity_type",
        "alert_type",
        "severity",
        "priority",
        "risk_score",
        "behavior_type",
        "trigger_source",
        "trigger_reason",
        "status",
        "created_at",
        "updated_at",
        "first_seen_at",
        "last_seen_at",
        "acknowledged_at",
        "resolved_at",
        "assigned_to",
        "metadata_json",
    }
    assert required_cols.issubset(col_names)

    # Check indexes exist
    indexes = db.execute("SELECT index_name FROM duckdb_indexes() WHERE table_name = 'alerts'").fetchall()
    index_names = {idx[0] for idx in indexes}
    assert "idx_alerts_analysis" in index_names
    assert "idx_alerts_dataset" in index_names
    assert "idx_alerts_status" in index_names
    assert "idx_alerts_severity" in index_names
    assert "idx_alerts_type" in index_names
    assert "idx_alerts_entity" in index_names


def test_deterministic_alert_generation_and_metadata_traceability(db: duckdb.DuckDBPyConnection):
    """Verify alert generation, grouping, and traceable metadata."""
    now = datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc)
    analysis_id = "test-analysis-alerts"
    dataset_id = "test-dataset-alerts"

    # Seed dataset and analysis run
    db.execute(
        """
        INSERT INTO datasets (dataset_id, name, file_name, file_path, format, size_bytes, row_count, uploaded_at, status)
        VALUES (?, 'Alert Test Dataset', 'test.csv', '/tmp/test.csv', 'csv', 100, 3, ?, 'ready')
        """,
        [dataset_id, now],
    )
    db.execute(
        """
        INSERT INTO analysis_runs (analysis_id, dataset_id, status, started_at, completed_at, entity_count, high_risk_count)
        VALUES (?, ?, 'completed', ?, ?, 3, 2)
        """,
        [analysis_id, dataset_id, now, now],
    )

    # Insert 3 transactions:
    # Tx 1: High risk (0.85), peeling_chain, non-standard port 9999
    # Tx 2: High risk (0.75), peeling_chain, same cluster 10, standard port 8333 (within 2 minutes)
    # Tx 3: Low risk (0.15), normal, cluster 20
    txs = [
        ("tx_alert_1", dataset_id, 800000, now, 1, 2, 5000000000, 5000000000, 10000, now),
        ("tx_alert_2", dataset_id, 800001, now + timedelta(minutes=2), 1, 2, 4000000000, 4000000000, 10000, now),
        ("tx_alert_3", dataset_id, 800002, now + timedelta(hours=1), 1, 1, 1000000000, 1000000000, 5000, now),
    ]
    for tx in txs:
        db.execute(
            """
            INSERT INTO transactions (
                transaction_id, dataset_id, block_height, timestamp, input_count, output_count,
                total_input_value_satoshi, total_output_value_satoshi, fee_satoshi, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(tx),
        )

    # Insert ML results
    ml_results = [
        (
            "res_1", analysis_id, dataset_id, "tx_alert_1", "transaction", 0.85, 0.85, "high", "peeling_chain", 0.92,
            "{}", json.dumps({"cluster_id": 10, "fan_in": 1, "fan_out": 2, "net_is_standard_bitcoin_port": 0, "net_src_port": 9999, "net_dst_port": 8333}),
            "{}", "xgboost_risk_v1", "v1", now,
        ),
        (
            "res_2", analysis_id, dataset_id, "tx_alert_2", "transaction", 0.75, 0.75, "high", "peeling_chain", 0.88,
            "{}", json.dumps({"cluster_id": 10, "fan_in": 1, "fan_out": 2, "net_is_standard_bitcoin_port": 1, "net_src_port": 8333, "net_dst_port": 8333}),
            "{}", "xgboost_risk_v1", "v1", now,
        ),
        (
            "res_3", analysis_id, dataset_id, "tx_alert_3", "transaction", 0.15, 0.15, "low", "normal", 0.99,
            "{}", json.dumps({"cluster_id": 20, "fan_in": 1, "fan_out": 1, "net_is_standard_bitcoin_port": 1, "net_src_port": 8333, "net_dst_port": 8333}),
            "{}", "xgboost_risk_v1", "v1", now,
        ),
    ]
    for res in ml_results:
        db.execute(
            """
            INSERT INTO ml_results (
                result_id, analysis_id, dataset_id, entity_id, entity_type,
                anomaly_score, risk_score, risk_level, prediction_label,
                confidence, explanation_json, features_json, graph_evidence_json,
                model_id, model_version, predicted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(res),
        )

    # Run alert generation
    engine = AlertEngine(db)
    generated_first = engine.generate_alerts_for_analysis(analysis_id, dataset_id)
    assert len(generated_first) > 0

    # Test IDEMPOTENCY: run a second time, verify exact same count and zero duplicate rows
    generated_second = engine.generate_alerts_for_analysis(analysis_id, dataset_id)
    assert len(generated_second) == len(generated_first)

    total_rows = db.execute("SELECT COUNT(*) FROM alerts WHERE analysis_id = ?", [analysis_id]).fetchone()[0]
    assert total_rows == len(generated_first)

    # Inspect alerts generated
    alerts = db.execute(
        "SELECT alert_type, entity_id, risk_score, behavior_type, status, metadata_json FROM alerts WHERE analysis_id = ? ORDER BY risk_score DESC",
        [analysis_id],
    ).fetchall()

    all_categories = set()
    for alert in alerts:
        meta = json.loads(alert[5])
        assert "triggering_signals" in meta
        assert "source_features" in meta
        assert "risk_score" in meta
        assert "behavior_type" in meta
        assert alert[4] == "NEW"
        all_categories.update(meta["triggering_signals"])

    assert "ml_xgboost" in all_categories
    assert "catboost_typology" in all_categories
    assert "network_telemetry" in all_categories


def test_status_lifecycle_and_dashboard_metric_separation(db: duckdb.DuckDBPyConnection):
    """
    Verify:
    1. High-Risk Transactions count = count of ML results with risk_score >= 0.50
    2. Active Alerts count = count of alerts with status IN ('NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'ESCALATED')
    3. Resolving an alert immediately reduces Active Alerts without altering High-Risk Transactions count.
    """
    now = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)
    analysis_id = "test-analysis-metrics"
    dataset_id = "test-dataset-metrics"

    db.execute(
        "INSERT INTO datasets (dataset_id, name, file_name, file_path, format, size_bytes, row_count, uploaded_at, status) VALUES (?, 'DS', 'f.csv', '/p', 'csv', 10, 2, ?, 'ready')",
        [dataset_id, now],
    )
    db.execute(
        "INSERT INTO analysis_runs (analysis_id, dataset_id, status, started_at, completed_at, entity_count, high_risk_count) VALUES (?, ?, 'completed', ?, ?, 2, 2)",
        [analysis_id, dataset_id, now, now],
    )

    # 2 high-risk transactions
    for txid in ["tx_high_1", "tx_high_2"]:
        db.execute(
            """
            INSERT INTO transactions (
                transaction_id, dataset_id, block_height, timestamp, input_count, output_count,
                total_input_value_satoshi, total_output_value_satoshi, fee_satoshi, ingested_at
            ) VALUES (?, ?, 800000, ?, 1, 1, 100000, 100000, 1000, ?)
            """,
            [txid, dataset_id, now, now],
        )
        db.execute(
            """
            INSERT INTO ml_results (
                result_id, analysis_id, dataset_id, entity_id, entity_type,
                anomaly_score, risk_score, risk_level, prediction_label,
                confidence, explanation_json, features_json, graph_evidence_json,
                model_id, model_version, predicted_at
            ) VALUES (?, ?, ?, ?, 'transaction', 0.85, 0.85, 'high', 'peeling_chain', 0.9, '{}', '{}', '{}', 'xgboost_risk_v1', 'v1', ?)
            """,
            [f"res_{txid}", analysis_id, dataset_id, txid, now],
        )

    # Generate alerts
    service = AlertService(db)
    service.generate_alerts_for_analysis(analysis_id, dataset_id)

    # Initial metric counts
    high_risk_tx_count = db.execute(
        "SELECT COUNT(*) FROM ml_results WHERE analysis_id = ? AND entity_type = 'transaction' AND risk_score >= 0.50",
        [analysis_id],
    ).fetchone()[0]
    assert high_risk_tx_count == 2

    summary_initial = service.get_alerts_summary(analysis_id=analysis_id)
    initial_active_alerts = summary_initial["active"]
    assert initial_active_alerts >= 2

    # Get one alert ID to transition
    alerts_list, _ = service.list_alerts(analysis_id=analysis_id, page_size=1)
    target_alert_id = alerts_list[0]["alert_id"]

    # Transition 1: Acknowledge
    service.update_status(target_alert_id, "ACKNOWLEDGED")
    alert_ack = service.get_alert(target_alert_id)
    assert alert_ack["status"] == "ACKNOWLEDGED"

    # Active count should remain the same because ACKNOWLEDGED is active
    summary_ack = service.get_alerts_summary(analysis_id=analysis_id)
    assert summary_ack["active"] == initial_active_alerts

    # Transition 2: Investigating
    service.update_status(target_alert_id, "INVESTIGATING")
    alert_inv = service.get_alert(target_alert_id)
    assert alert_inv["status"] == "INVESTIGATING"

    # Transition 3: Escalated
    service.update_status(target_alert_id, "ESCALATED")
    alert_esc = service.get_alert(target_alert_id)
    assert alert_esc["status"] == "ESCALATED"

    # Transition 4: Resolve
    service.update_status(target_alert_id, "RESOLVED")
    alert_res = service.get_alert(target_alert_id)
    assert alert_res["status"] == "RESOLVED"
    assert alert_res["resolved_at"] is not None

    # CRITICAL CHECK:
    # 1. Active Alerts count MUST have decreased by exactly 1
    summary_resolved = service.get_alerts_summary(analysis_id=analysis_id)
    assert summary_resolved["active"] == initial_active_alerts - 1
    assert summary_resolved["byStatus"]["RESOLVED"] == 1

    # 2. High-Risk Transactions count MUST REMAIN EXACTLY 2 (unchanged)
    high_risk_tx_count_after = db.execute(
        "SELECT COUNT(*) FROM ml_results WHERE analysis_id = ? AND entity_type = 'transaction' AND risk_score >= 0.50",
        [analysis_id],
    ).fetchone()[0]
    assert high_risk_tx_count_after == 2


def test_alerts_api_endpoints(client: TestClient, db: duckdb.DuckDBPyConnection):
    """Verify all /api/alerts REST API endpoints."""
    now = datetime(2026, 9, 15, 14, 0, 0, tzinfo=timezone.utc)
    analysis_id = "test-api-analysis"
    dataset_id = "test-api-dataset"

    db.execute(
        "INSERT INTO datasets (dataset_id, name, file_name, file_path, format, size_bytes, row_count, uploaded_at, status) VALUES (?, 'DS', 'f.csv', '/p', 'csv', 10, 1, ?, 'ready')",
        [dataset_id, now],
    )
    db.execute(
        "INSERT INTO analysis_runs (analysis_id, dataset_id, status, started_at, completed_at, entity_count, high_risk_count) VALUES (?, ?, 'completed', ?, ?, 1, 1)",
        [analysis_id, dataset_id, now, now],
    )
    db.execute(
        """
        INSERT INTO transactions (
            transaction_id, dataset_id, block_height, timestamp, input_count, output_count,
            total_input_value_satoshi, total_output_value_satoshi, fee_satoshi, ingested_at
        ) VALUES ('tx_api_1', ?, 800000, ?, 1, 1, 100000, 100000, 1000, ?)
        """,
        [dataset_id, now, now],
    )
    db.execute(
        """
        INSERT INTO ml_results (
            result_id, analysis_id, dataset_id, entity_id, entity_type,
            anomaly_score, risk_score, risk_level, prediction_label,
            confidence, explanation_json, features_json, graph_evidence_json,
            model_id, model_version, predicted_at
        ) VALUES ('res_api_1', ?, ?, 'tx_api_1', 'transaction', 0.95, 0.95, 'critical', 'rapid_multihop', 0.95, '{}', '{}', '{}', 'xgboost_risk_v1', 'v1', ?)
        """,
        [analysis_id, dataset_id, now],
    )

    # 1. Trigger generate alerts via API
    gen_res = client.post(f"/api/alerts/generate?analysisId={analysis_id}&datasetId={dataset_id}")
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["success"] is True
    assert len(gen_data["data"]) >= 1

    # 2. GET /api/alerts/summary
    sum_res = client.get(f"/api/alerts/summary?analysisId={analysis_id}")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert sum_data["total"] >= 1
    assert sum_data["active"] >= 1
    assert "critical" in sum_data["bySeverity"]

    # 3. GET /api/alerts
    list_res = client.get(f"/api/alerts?analysisId={analysis_id}&status=NEW")
    assert list_res.status_code == 200
    list_data = list_res.json()["data"]
    assert len(list_data) >= 1
    target_alert = list_data[0]
    alert_id = target_alert["alertId"]

    # 4. GET /api/alerts/{alert_id}
    detail_res = client.get(f"/api/alerts/{alert_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()["data"]
    assert detail_data["alertId"] == alert_id
    assert detail_data["metadataJson"]["behavior_type"] == "rapid_multihop"

    # 5. PATCH /api/alerts/{alert_id}/priority
    pri_res = client.patch(f"/api/alerts/{alert_id}/priority", json={"priority": "P1"})
    assert pri_res.status_code == 200
    assert pri_res.json()["data"]["priority"] == "P1"

    # 6. PATCH /api/alerts/{alert_id}/status -> INVESTIGATING
    st_res = client.patch(f"/api/alerts/{alert_id}/status", json={"status": "INVESTIGATING", "resolved_by": "analyst_2"})
    assert st_res.status_code == 200
    assert st_res.json()["data"]["status"] == "INVESTIGATING"

    # 7. PATCH /api/alerts/{alert_id}/status -> DISMISSED
    st_dis = client.patch(
        f"/api/alerts/{alert_id}/status",
        json={"status": "DISMISSED", "resolved_by": "analyst_2", "resolution_reason": "False positive benign volume"},
    )
    assert st_dis.status_code == 200
    assert st_dis.json()["data"]["status"] == "DISMISSED"

    # 8. Check active alerts decremented
    sum_res_after = client.get(f"/api/alerts/summary?analysisId={analysis_id}")
    assert sum_res_after.json()["data"]["active"] == sum_data["active"] - 1

"""Schema creation and migration runner for DuckDB.

Authoritative reference: docs/backend/duckdb-schema.md
"""

import duckdb
from backend.utils.logging import logger


MIGRATION_STATEMENTS = [
    # 1. Datasets table
    """
    CREATE TABLE IF NOT EXISTS datasets (
        dataset_id         VARCHAR PRIMARY KEY,
        name               VARCHAR NOT NULL,
        file_name          VARCHAR NOT NULL,
        file_path          VARCHAR NOT NULL,
        format             VARCHAR NOT NULL,
        size_bytes         BIGINT,
        row_count          INTEGER,
        canonical_tx_count INTEGER,
        uploaded_at        TIMESTAMPTZ NOT NULL,
        status             VARCHAR NOT NULL,
        available_fields   VARCHAR[],
        canonical_field_map JSON,
        validation_summary  JSON,
        error_message      VARCHAR
    );
    """,

    # 2. Transactions table
    """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id              VARCHAR NOT NULL,
        dataset_id                  VARCHAR NOT NULL,
        block_hash                  VARCHAR,
        block_height                INTEGER,
        timestamp                   TIMESTAMPTZ,
        input_count                 INTEGER,
        output_count                INTEGER,
        total_input_value_satoshi   BIGINT,
        total_output_value_satoshi  BIGINT,
        fee_satoshi                 BIGINT,
        transaction_size_bytes      INTEGER,
        label                       VARCHAR,
        ingested_at                 TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (transaction_id, dataset_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_transactions_dataset ON transactions(dataset_id);",
    "CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(dataset_id, timestamp);",

    # 3. Transaction inputs table
    """
    CREATE TABLE IF NOT EXISTS transaction_inputs (
        input_id                VARCHAR PRIMARY KEY,
        transaction_id          VARCHAR NOT NULL,
        dataset_id              VARCHAR NOT NULL,
        input_index             INTEGER NOT NULL,
        input_address           VARCHAR,
        input_value_satoshi     BIGINT,
        sequence_number         BIGINT,
        previous_transaction_id VARCHAR,
        previous_output_index   INTEGER
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_tx_inputs_address ON transaction_inputs(input_address);",

    # 4. Transaction outputs table
    """
    CREATE TABLE IF NOT EXISTS transaction_outputs (
        output_id               VARCHAR PRIMARY KEY,
        transaction_id          VARCHAR NOT NULL,
        dataset_id              VARCHAR NOT NULL,
        output_index            INTEGER NOT NULL,
        output_address          VARCHAR,
        output_value_satoshi    BIGINT,
        script_type             VARCHAR,
        is_spent                BOOLEAN
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_tx_outputs_address ON transaction_outputs(output_address);",

    # 5. Derived addresses table
    """
    CREATE TABLE IF NOT EXISTS addresses (
        address_id                 VARCHAR NOT NULL,
        dataset_id                 VARCHAR NOT NULL,
        address_type               VARCHAR,
        first_seen_timestamp       TIMESTAMPTZ,
        last_seen_timestamp        TIMESTAMPTZ,
        total_received_satoshi     BIGINT,
        total_sent_satoshi         BIGINT,
        transaction_count          INTEGER,
        output_count               INTEGER,
        input_count                INTEGER,
        PRIMARY KEY (address_id, dataset_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_addresses_dataset ON addresses(dataset_id);",

    # 6. Analysis runs table
    """
    CREATE TABLE IF NOT EXISTS analysis_runs (
        analysis_id             VARCHAR PRIMARY KEY,
        dataset_id              VARCHAR NOT NULL,
        status                  VARCHAR NOT NULL,
        started_at              TIMESTAMPTZ,
        completed_at            TIMESTAMPTZ,
        model_id                VARCHAR,
        model_version           VARCHAR,
        feature_schema_version  VARCHAR,
        entity_count            INTEGER,
        high_risk_count         INTEGER,
        critical_risk_count     INTEGER,
        error_message           VARCHAR,
        config                  JSON,
        graph_summary           JSON
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_analysis_dataset ON analysis_runs(dataset_id);",

    # 7. ML Results table
    """
    CREATE TABLE IF NOT EXISTS ml_results (
        result_id           VARCHAR PRIMARY KEY,
        analysis_id         VARCHAR NOT NULL,
        dataset_id          VARCHAR NOT NULL,
        entity_id           VARCHAR NOT NULL,
        entity_type         VARCHAR NOT NULL,
        anomaly_score       DOUBLE NOT NULL,
        risk_score          DOUBLE NOT NULL,
        risk_level          VARCHAR NOT NULL,
        prediction_label    VARCHAR,
        confidence          DOUBLE,
        explanation_json    JSON,
        features_json       JSON,
        graph_evidence_json JSON,
        model_id            VARCHAR NOT NULL,
        model_version       VARCHAR NOT NULL,
        predicted_at        TIMESTAMPTZ NOT NULL,
        UNIQUE (analysis_id, entity_id, entity_type)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_ml_results_analysis ON ml_results(analysis_id);",
    "CREATE INDEX IF NOT EXISTS idx_ml_results_entity ON ml_results(entity_id, dataset_id);",
    "CREATE INDEX IF NOT EXISTS idx_ml_results_risk ON ml_results(analysis_id, risk_score);",

    # 8. Network events table
    """
    CREATE TABLE IF NOT EXISTS network_events (
        event_id            VARCHAR PRIMARY KEY,
        transaction_id      VARCHAR NOT NULL,
        dataset_id          VARCHAR NOT NULL,
        timestamp           TIMESTAMPTZ,
        timestamp_epoch_sec BIGINT,
        src_ip              VARCHAR,
        src_port            INTEGER,
        dst_ip              VARCHAR,
        dst_port            INTEGER,
        country             VARCHAR,
        asn                 BIGINT
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_network_events_dataset ON network_events(dataset_id);",
    "CREATE INDEX IF NOT EXISTS idx_network_events_tx ON network_events(transaction_id);",

    # 9. Alerts table
    """
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id            VARCHAR PRIMARY KEY,
        analysis_id         VARCHAR NOT NULL,
        dataset_id          VARCHAR NOT NULL,
        fingerprint         VARCHAR NOT NULL,
        grouping_key        VARCHAR NOT NULL,
        transaction_id      VARCHAR,
        entity_id           VARCHAR NOT NULL,
        entity_type         VARCHAR NOT NULL,
        alert_type          VARCHAR NOT NULL,
        severity            VARCHAR NOT NULL,
        priority            VARCHAR NOT NULL,
        risk_score          DOUBLE NOT NULL,
        behavior_type       VARCHAR,
        trigger_source      VARCHAR NOT NULL,
        trigger_reason      VARCHAR NOT NULL,
        status              VARCHAR NOT NULL,
        created_at          TIMESTAMPTZ NOT NULL,
        updated_at          TIMESTAMPTZ NOT NULL,
        first_seen_at       TIMESTAMPTZ,
        last_seen_at        TIMESTAMPTZ,
        acknowledged_at     TIMESTAMPTZ,
        resolved_at         TIMESTAMPTZ,
        assigned_to         VARCHAR,
        metadata_json       JSON,
        UNIQUE (analysis_id, fingerprint)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_alerts_analysis ON alerts(analysis_id);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_dataset ON alerts(dataset_id);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(analysis_id, status);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(analysis_id, severity);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(analysis_id, alert_type);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alerts(entity_id);",
]


def run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    """Run all schema migrations idempotently."""
    logger.info("Initializing DuckDB schema migrations...")
    for stmt in MIGRATION_STATEMENTS:
        try:
            conn.execute(stmt)
        except Exception as e:
            logger.error(f"Migration statement failed: {e}\nStatement: {stmt}")
            raise
    logger.info("DuckDB schema migrations applied successfully.")

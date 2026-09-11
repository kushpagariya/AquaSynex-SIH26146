# DuckDB Schema

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Authoritative database schema.** All DuckDB queries in the backend must conform to this schema.
> Do NOT change table or column names without updating this document and coordinating with the Backend Owner.

---

## 1. Why DuckDB

See [ADR-001](../decisions/ADR-001-duckdb-selection.md) for the full rationale. Summary:

- **Embedded**: No separate database server process. Runs in-process with FastAPI.
- **Analytical**: Optimized for column-oriented analytical queries (aggregations, window functions, joins on large tables).
- **Offline**: No network dependency. Database is a local file.
- **Parquet-native**: Can query Parquet files directly without importing. Perfect for large datasets.
- **Simple operations**: Single-user analytical workload; no complex transaction management needed.

---

## 2. Database File

| Property | Value |
|---|---|
| File path | Configured via `DB_PATH` environment variable (default: `/app/db/aquasynex.db`) |
| File format | DuckDB native format |
| Persistence | Durable; survives container restarts via Docker volume |

---

## 3. Connection Model

DuckDB in Python:

```python
import duckdb

# Backend opens one connection at startup
conn = duckdb.connect(database=DB_PATH)

# All queries use this connection
result = conn.execute("SELECT * FROM datasets").fetchdf()
```

**Concurrency**: DuckDB supports one writer at a time. For Phase 1 (single-user), this is sufficient. If multiple simultaneous analyses become a requirement, this limitation must be addressed via an ADR.

---

## 4. Tables

### 4.1 `datasets`

Tracks uploaded datasets.

```sql
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id         VARCHAR PRIMARY KEY,
    name               VARCHAR NOT NULL,
    file_name          VARCHAR NOT NULL,
    file_path          VARCHAR NOT NULL,
    format             VARCHAR NOT NULL,           -- 'csv' | 'json' | 'jsonl' | 'parquet'
    size_bytes         BIGINT,
    row_count          INTEGER,
    canonical_tx_count INTEGER,
    uploaded_at        TIMESTAMPTZ NOT NULL,
    status             VARCHAR NOT NULL,           -- 'uploaded' | 'processing' | 'ready' | 'error'
    available_fields   VARCHAR[],                  -- list of canonical field names
    canonical_field_map JSON,
    validation_summary  JSON,
    error_message      VARCHAR
);
```

---

### 4.2 `transactions`

Canonical transaction records.

```sql
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id              VARCHAR NOT NULL,
    dataset_id                  VARCHAR NOT NULL REFERENCES datasets(dataset_id),
    block_hash                  VARCHAR,
    block_height                INTEGER,
    timestamp                   TIMESTAMPTZ,
    input_count                 INTEGER,
    output_count                INTEGER,
    total_input_value_satoshi   BIGINT,
    total_output_value_satoshi  BIGINT,
    fee_satoshi                 BIGINT,
    transaction_size_bytes      INTEGER,
    label                       VARCHAR,           -- 'illicit' | 'licit' | 'unknown' | NULL
    ingested_at                 TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (transaction_id, dataset_id)
);
CREATE INDEX idx_transactions_dataset ON transactions(dataset_id);
CREATE INDEX idx_transactions_timestamp ON transactions(dataset_id, timestamp);
```

---

### 4.3 `transaction_inputs`

Per-transaction input records (only populated when raw input data is available).

```sql
CREATE TABLE IF NOT EXISTS transaction_inputs (
    input_id                VARCHAR PRIMARY KEY,   -- '{tx_id}:{input_index}'
    transaction_id          VARCHAR NOT NULL,
    dataset_id              VARCHAR NOT NULL,
    input_index             INTEGER NOT NULL,
    input_address           VARCHAR,
    input_value_satoshi     BIGINT,
    sequence_number         BIGINT,
    previous_transaction_id VARCHAR,
    previous_output_index   INTEGER,
    FOREIGN KEY (transaction_id, dataset_id) REFERENCES transactions(transaction_id, dataset_id)
);
CREATE INDEX idx_tx_inputs_address ON transaction_inputs(input_address) WHERE input_address IS NOT NULL;
```

---

### 4.4 `transaction_outputs`

Per-transaction output records.

```sql
CREATE TABLE IF NOT EXISTS transaction_outputs (
    output_id               VARCHAR PRIMARY KEY,   -- '{tx_id}:{output_index}'
    transaction_id          VARCHAR NOT NULL,
    dataset_id              VARCHAR NOT NULL,
    output_index            INTEGER NOT NULL,
    output_address          VARCHAR,
    output_value_satoshi    BIGINT,
    script_type             VARCHAR,
    is_spent                BOOLEAN,
    FOREIGN KEY (transaction_id, dataset_id) REFERENCES transactions(transaction_id, dataset_id)
);
CREATE INDEX idx_tx_outputs_address ON transaction_outputs(output_address) WHERE output_address IS NOT NULL;
```

---

### 4.5 `addresses`

Derived address summaries.

```sql
CREATE TABLE IF NOT EXISTS addresses (
    address_id                 VARCHAR NOT NULL,
    dataset_id                 VARCHAR NOT NULL REFERENCES datasets(dataset_id),
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
CREATE INDEX idx_addresses_dataset ON addresses(dataset_id);
```

---

### 4.6 `analysis_runs`

Tracks analysis pipeline runs.

```sql
CREATE TABLE IF NOT EXISTS analysis_runs (
    analysis_id             VARCHAR PRIMARY KEY,
    dataset_id              VARCHAR NOT NULL REFERENCES datasets(dataset_id),
    status                  VARCHAR NOT NULL,      -- 'pending' | 'running' | 'completed' | 'failed'
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
    graph_summary           JSON                   -- graph_analysis_summary JSON
);
CREATE INDEX idx_analysis_dataset ON analysis_runs(dataset_id);
```

---

### 4.7 `ml_results`

ML prediction results per entity per analysis run.

```sql
CREATE TABLE IF NOT EXISTS ml_results (
    result_id           VARCHAR PRIMARY KEY,
    analysis_id         VARCHAR NOT NULL REFERENCES analysis_runs(analysis_id),
    dataset_id          VARCHAR NOT NULL,
    entity_id           VARCHAR NOT NULL,           -- Bitcoin address or transaction ID
    entity_type         VARCHAR NOT NULL,           -- 'address' | 'transaction'
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
CREATE INDEX idx_ml_results_analysis ON ml_results(analysis_id);
CREATE INDEX idx_ml_results_entity ON ml_results(entity_id, dataset_id);
CREATE INDEX idx_ml_results_risk ON ml_results(analysis_id, risk_score DESC);
```

---

## 5. DuckDB + Parquet Strategy

For large datasets, the data pipeline writes canonical records to Parquet files on disk. DuckDB can query these directly:

```sql
-- Query Parquet file directly (no import needed)
SELECT * FROM read_parquet('/app/data/dataset-uuid/transactions.parquet')
WHERE timestamp >= '2009-01-01';

-- Or register as a view
CREATE VIEW IF NOT EXISTS parquet_transactions AS
SELECT * FROM read_parquet('/app/data/*/transactions.parquet');
```

**When to use Parquet vs DuckDB tables**:
- Small datasets (< 1M rows): Import into DuckDB table for faster repeated queries
- Large datasets (≥ 1M rows): Keep as Parquet; query via `read_parquet()` — avoids double storage

`DECISION REQUIRED`: Define exact threshold and strategy.

---

## 6. Common Query Patterns

### Get high-risk addresses for an analysis

```sql
SELECT 
    r.entity_id AS address_id,
    r.risk_score,
    r.risk_level,
    a.transaction_count,
    a.total_received_satoshi,
    a.total_sent_satoshi
FROM ml_results r
JOIN addresses a ON r.entity_id = a.address_id AND r.dataset_id = a.dataset_id
WHERE r.analysis_id = ?
  AND r.entity_type = 'address'
  AND r.risk_score >= ?
ORDER BY r.risk_score DESC
LIMIT ? OFFSET ?;
```

### Get transaction list with risk scores

```sql
SELECT 
    t.transaction_id,
    t.timestamp,
    t.total_output_value_satoshi,
    t.fee_satoshi,
    r.risk_score,
    r.risk_level
FROM transactions t
LEFT JOIN ml_results r ON t.transaction_id = r.entity_id 
    AND t.dataset_id = r.dataset_id 
    AND r.analysis_id = ?
WHERE t.dataset_id = ?
ORDER BY r.risk_score DESC NULLS LAST
LIMIT ? OFFSET ?;
```

---

*Last updated: 2026-09-11 | Status: PLANNED | Owner: Backend Owner*
*References: [canonical-schema.md](../data/canonical-schema.md) | [api-specification.md](./api-specification.md) | [ADR-001](../decisions/ADR-001-duckdb-selection.md)*

# Canonical Schema

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative internal data model.**
> All subsystems — ML, Graph, Backend — consume and produce data in this format after the data pipeline runs.
> See [data-dictionary.md](./data-dictionary.md) for field-level definitions.

---

## 1. Overview

The canonical schema defines the internal representation of Bitcoin transaction data after ingestion, cleaning, and normalization. Raw datasets are heterogeneous; the canonical schema is homogeneous and explicit.

```
Raw Dataset (variable format)
        │
        ▼
Data Pipeline (normalization)
        │
        ▼
Canonical Records ──► DuckDB storage (Parquet)
        │
        ├──► Graph Layer (NetworkX graph construction)
        │
        └──► ML Layer (feature engineering)
```

---

## 2. Canonical Data Entities

The canonical schema defines four primary data entities:

| Entity | Description | Table (DuckDB) |
|---|---|---|
| `Transaction` | A single Bitcoin transaction | `transactions` |
| `TransactionInput` | One input of a transaction | `transaction_inputs` |
| `TransactionOutput` | One output of a transaction | `transaction_outputs` |
| `Address` | A Bitcoin address as derived from outputs | `addresses` |

---

## 3. Transaction Entity

**DuckDB table**: `transactions`

| Column | Type | Nullable | Availability | Description |
|---|---|---|---|---|
| `transaction_id` | `VARCHAR` | No | `REQUIRED_CANONICAL` | Bitcoin txid (64-char hex) |
| `dataset_id` | `VARCHAR` | No | `REQUIRED_CANONICAL` | Links to `datasets` table |
| `block_hash` | `VARCHAR` | Yes | `OPTIONAL` | Block containing this transaction |
| `block_height` | `INTEGER` | Yes | `OPTIONAL` | Block height |
| `timestamp` | `TIMESTAMPTZ` | Yes | `OPTIONAL` | Transaction timestamp (UTC) |
| `input_count` | `INTEGER` | Yes | `OPTIONAL` | Number of inputs |
| `output_count` | `INTEGER` | Yes | `OPTIONAL` | Number of outputs |
| `total_input_value_satoshi` | `BIGINT` | Yes | `OPTIONAL` | Sum of input values (satoshis) |
| `total_output_value_satoshi` | `BIGINT` | Yes | `OPTIONAL` | Sum of output values (satoshis) |
| `fee_satoshi` | `BIGINT` | Yes | `OPTIONAL/DERIVED` | Transaction fee (satoshis) |
| `transaction_size_bytes` | `INTEGER` | Yes | `DATASET_DEPENDENT` | Transaction byte size |
| `label` | `VARCHAR` | Yes | `DATASET_DEPENDENT` | Known label if available |
| `ingested_at` | `TIMESTAMPTZ` | No | `DERIVED` | When this record was created |

**Primary key**: `(transaction_id, dataset_id)`

**Uniqueness constraint**: `transaction_id` must be unique within a dataset.

---

## 4. TransactionInput Entity

**DuckDB table**: `transaction_inputs`

| Column | Type | Nullable | Availability | Description |
|---|---|---|---|---|
| `input_id` | `VARCHAR` | No | `DERIVED` | Surrogate: `{txid}:{input_index}` |
| `transaction_id` | `VARCHAR` | No | `REQUIRED` | Foreign key to `transactions` |
| `dataset_id` | `VARCHAR` | No | `REQUIRED` | Foreign key to `datasets` |
| `input_index` | `INTEGER` | No | `REQUIRED` | Position of input in transaction |
| `input_address` | `VARCHAR` | Yes | `DATASET_DEPENDENT` | Spending address |
| `input_value_satoshi` | `BIGINT` | Yes | `DATASET_DEPENDENT` | Value being spent (satoshis) |
| `sequence_number` | `BIGINT` | Yes | `DATASET_DEPENDENT` | RBF sequence number |
| `previous_transaction_id` | `VARCHAR` | Yes | `DATASET_DEPENDENT` | UTXO being spent |
| `previous_output_index` | `INTEGER` | Yes | `DATASET_DEPENDENT` | UTXO output index |

**Primary key**: `input_id`

**Note**: This table is only populated if the dataset includes per-input detail. Many datasets only contain aggregate input counts/values.

---

## 5. TransactionOutput Entity

**DuckDB table**: `transaction_outputs`

| Column | Type | Nullable | Availability | Description |
|---|---|---|---|---|
| `output_id` | `VARCHAR` | No | `DERIVED` | Surrogate: `{txid}:{output_index}` |
| `transaction_id` | `VARCHAR` | No | `REQUIRED` | Foreign key to `transactions` |
| `dataset_id` | `VARCHAR` | No | `REQUIRED` | Foreign key to `datasets` |
| `output_index` | `INTEGER` | No | `REQUIRED` | Vout index |
| `output_address` | `VARCHAR` | Yes | `OPTIONAL` | Receiving address |
| `output_value_satoshi` | `BIGINT` | Yes | `OPTIONAL` | Output value (satoshis) |
| `script_type` | `VARCHAR` | Yes | `DATASET_DEPENDENT` | P2PKH / P2SH / P2WPKH / etc. |
| `is_spent` | `BOOLEAN` | Yes | `DATASET_DEPENDENT` | Whether this output was spent |

**Primary key**: `output_id`

---

## 6. Address Entity

**DuckDB table**: `addresses`

This entity is **derived** from transaction outputs. It represents unique Bitcoin addresses observed in the dataset.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `address_id` | `VARCHAR` | No | Bitcoin address string (canonical address identifier) |
| `dataset_id` | `VARCHAR` | No | Which dataset this address was observed in |
| `address_type` | `VARCHAR` | Yes | Script type (P2PKH, P2SH, etc.) |
| `first_seen_timestamp` | `TIMESTAMPTZ` | Yes | Earliest transaction timestamp |
| `last_seen_timestamp` | `TIMESTAMPTZ` | Yes | Latest transaction timestamp |
| `total_received_satoshi` | `BIGINT` | Yes | Total BTC received |
| `total_sent_satoshi` | `BIGINT` | Yes | Total BTC sent |
| `transaction_count` | `INTEGER` | Yes | Number of transactions involving this address |
| `output_count` | `INTEGER` | Yes | Number of outputs received |
| `input_count` | `INTEGER` | Yes | Number of inputs spent |

**Primary key**: `(address_id, dataset_id)`

---

## 7. Dataset Entity (Metadata)

**DuckDB table**: `datasets`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `dataset_id` | `VARCHAR` | No | UUID v4 |
| `name` | `VARCHAR` | No | User-provided name |
| `file_name` | `VARCHAR` | No | Original filename |
| `file_path` | `VARCHAR` | No | Absolute path on disk |
| `format` | `VARCHAR` | No | `csv` / `json` / `jsonl` / `parquet` |
| `size_bytes` | `BIGINT` | No | File size |
| `row_count` | `INTEGER` | Yes | Number of raw rows |
| `canonical_tx_count` | `INTEGER` | Yes | Number of canonical transactions |
| `uploaded_at` | `TIMESTAMPTZ` | No | Upload timestamp |
| `status` | `VARCHAR` | No | See dataset status enum |
| `available_fields` | `VARCHAR[]` | Yes | List of canonical fields present |
| `validation_summary` | `JSON` | Yes | Validation report summary |
| `canonical_field_map` | `JSON` | Yes | Raw column → canonical field mapping |

**Primary key**: `dataset_id`

---

## 8. Analysis Run Entity

**DuckDB table**: `analysis_runs`

| Column | Type | Nullable | Description |
|---|---|---|---|
| `analysis_id` | `VARCHAR` | No | UUID v4 |
| `dataset_id` | `VARCHAR` | No | Foreign key to `datasets` |
| `status` | `VARCHAR` | No | `pending` / `running` / `completed` / `failed` |
| `started_at` | `TIMESTAMPTZ` | Yes | Analysis start time |
| `completed_at` | `TIMESTAMPTZ` | Yes | Analysis completion time |
| `model_id` | `VARCHAR` | Yes | ML model used |
| `model_version` | `VARCHAR` | Yes | ML model version |
| `feature_schema_version` | `VARCHAR` | Yes | Feature schema version used |
| `error_message` | `VARCHAR` | Yes | Error details if failed |
| `entity_count` | `INTEGER` | Yes | Number of entities analyzed |
| `config` | `JSON` | Yes | Analysis configuration snapshot |

**Primary key**: `analysis_id`

---

## 9. ML Result Entity

**DuckDB table**: `ml_results`

Stores the ML output per entity per analysis run. See [model-output-contract.md](../ml/model-output-contract.md) for the full output schema.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `result_id` | `VARCHAR` | No | UUID v4 |
| `analysis_id` | `VARCHAR` | No | Foreign key to `analysis_runs` |
| `dataset_id` | `VARCHAR` | No | Foreign key to `datasets` |
| `entity_id` | `VARCHAR` | No | Entity being scored (address or transaction) |
| `entity_type` | `VARCHAR` | No | `address` / `transaction` |
| `anomaly_score` | `DOUBLE` | No | Model anomaly score [0.0, 1.0] |
| `risk_score` | `DOUBLE` | No | Calibrated risk score [0.0, 1.0] |
| `risk_level` | `VARCHAR` | No | `low` / `medium` / `high` / `critical` |
| `prediction_label` | `VARCHAR` | Yes | Model prediction label if classification |
| `explanation_json` | `JSON` | Yes | Structured SHAP explanations |
| `features_json` | `JSON` | Yes | Feature values used |
| `graph_evidence_json` | `JSON` | Yes | Graph features contributing to score |
| `model_id` | `VARCHAR` | No | ML model identifier |
| `model_version` | `VARCHAR` | No | ML model version |
| `predicted_at` | `TIMESTAMPTZ` | No | When prediction was made |

**Primary key**: `result_id`
**Unique constraint**: `(analysis_id, entity_id, entity_type)`

---

## 10. Canonical Schema Versioning

The canonical schema has a version identifier. When the schema changes:
1. Update this document.
2. Create a DuckDB migration.
3. Update [data-lineage.md](./data-lineage.md).
4. Notify all affected subsystems.

**Current canonical schema version**: `v1.0.0` (`IN PROGRESS`)

---

*Last updated: 2026-09-11 | Owner: All (canonical reference)*
*References: [data-dictionary.md](./data-dictionary.md) | [duckdb-schema.md](../backend/duckdb-schema.md)*

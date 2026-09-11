# Data Sources

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Authority**: This document defines what dataset types the system accepts and what assumptions are made about their content.
> See [canonical-schema.md](./canonical-schema.md) for the internal data representation after ingestion.

---

## 1. Overview

The system operates on **pre-collected, static Bitcoin transaction datasets**. It does not connect to live blockchain APIs at runtime. Datasets are uploaded by the investigator and processed offline.

The system must tolerate variability across datasets:
- Different column names for the same concept.
- Different field availability (not all datasets contain all fields).
- Different file formats.
- Different value representations (BTC vs satoshis, UNIX timestamp vs ISO datetime).

The data pipeline is responsible for mapping any valid input dataset to the [canonical schema](./canonical-schema.md).

---

## 2. Supported Input Formats

| Format | Extension | Status | Notes |
|---|---|---|---|
| CSV (comma-separated) | `.csv` | `PLANNED` | Primary expected format |
| JSON (array of objects) | `.json` | `PLANNED` | Secondary format |
| JSON Lines | `.jsonl` | `PLANNED` | One transaction per line |
| Parquet | `.parquet` | `PLANNED` | Preferred for large datasets |

**Maximum file size**: `DECISION REQUIRED` — Suggested limit of 2GB per upload, but DuckDB can handle much larger files via Parquet.

---

## 3. Known Dataset Types

### 3.1 Elliptic Bitcoin Dataset

**Description**: Academic research dataset containing Bitcoin transactions with class labels (illicit / licit / unknown).

**Source**: Elliptic (academic, offline copy required)

**Key characteristics**:
- Transaction-level features (203 features)
- Class labels available (useful for supervised learning)
- No raw transaction inputs/outputs (pre-aggregated features)
- Time step (not absolute timestamp)

**Availability of canonical fields**:

| Canonical Field | Available | Notes |
|---|---|---|
| `transactionId` | Partial | Hashed/anonymized IDs |
| `blockHeight` | No | Not included |
| `timestamp` | Partial | Time step only, not absolute datetime |
| `inputCount` | Partial | As feature |
| `outputCount` | Partial | As feature |
| `totalInputValue` | Partial | As feature (in BTC units) |
| `totalOutputValue` | Partial | As feature |
| `fee` | Partial | Derivable |
| `inputAddresses` | No | Anonymized |
| `outputAddresses` | No | Anonymized |
| `label` | Yes | `illicit`, `licit`, `unknown` |

**Use in this project**: `PLANNED` — Primary dataset for ML model training and validation.

---

### 3.2 Generic Bitcoin Transaction Export (Blockchain Explorer CSV)

**Description**: Raw transaction export from tools such as BlockSci, Blockstream, or custom scrapers.

**Key characteristics**:
- Contains raw transaction data including inputs and outputs
- Address information available
- High variability in column naming
- May contain script types

**Availability of canonical fields**: High — most canonical fields should be present but may use different column names.

---

### 3.3 Custom Investigation Dataset

**Description**: A dataset assembled specifically for a SIH demonstration, covering a specific time window of transactions.

**Status**: `PLANNED` — Will be defined when the demonstration dataset is prepared.

---

## 4. Dataset Validation Requirements

Before processing, the data pipeline validates:

1. **File format**: Is the file parseable as the declared format?
2. **Required fields**: Does the dataset contain at minimum the fields required for analysis?
3. **Field types**: Are numeric fields numeric, are timestamps parseable?
4. **Row count**: At least 1 row of data.
5. **Suspicious null rates**: If >80% of a required field is null, raise a warning.

See [data-validation.md](./data-validation.md) for the full validation specification.

---

## 5. Dataset Metadata

Every dataset registered in the system gets the following metadata stored in DuckDB:

| Field | Type | Description |
|---|---|---|
| `datasetId` | `string (UUID)` | Unique identifier for this dataset |
| `name` | `string` | User-provided name |
| `fileName` | `string` | Original filename |
| `filePath` | `string` | Storage path on disk |
| `format` | `enum` | `csv` / `json` / `jsonl` / `parquet` |
| `sizeBytes` | `integer` | File size |
| `rowCount` | `integer` | Number of records |
| `uploadedAt` | `datetime (UTC)` | Upload timestamp |
| `status` | `enum` | `uploaded` / `processing` / `ready` / `error` |
| `validationReport` | `json` | Summary of validation checks |
| `canonicalFieldMap` | `json` | Mapping from dataset columns to canonical field names |
| `availableFields` | `string[]` | List of canonical fields present in this dataset |

See [duckdb-schema.md](../backend/duckdb-schema.md) for the DuckDB table definition.

---

## 6. Field Availability Classification

Throughout the documentation, fields are classified as:

| Classification | Meaning |
|---|---|
| `REQUIRED_CANONICAL` | The canonical schema requires this field. If missing, ingestion fails. |
| `OPTIONAL_CANONICAL` | The canonical schema supports this field. Processing continues if missing. |
| `DATASET_DEPENDENT` | May or may not exist depending on the dataset type. |
| `DERIVED` | Computed during processing; never directly present in raw data. |
| `UNAVAILABLE` | Explicitly not expected in any current dataset format. |

---

## 7. Internet and Live Data Prohibition

**No live blockchain API calls are permitted at runtime.**

The system must not call:
- Blockstream API (`blockstream.info`)
- Blockchain.com API
- Any block explorer API
- Any public Bitcoin node RPC

All data is provided by the investigator as uploaded files.

See [ADR-002](../decisions/ADR-002-offline-first-architecture.md).

---

*Last updated: 2026-09-11 | Owner: ML Owner (Data Pipeline)*
*References: [canonical-schema.md](./canonical-schema.md) | [data-validation.md](./data-validation.md) | [data-dictionary.md](./data-dictionary.md)*

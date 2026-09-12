# Data Dictionary

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **This is the authoritative definition of all data fields used in the project.**
> All subsystems MUST use the canonical field names defined here.
> Do NOT define new field aliases without updating this document.
>
> See [canonical-schema.md](./canonical-schema.md) for how these fields are organized into data entities.

---

## 1. Naming Convention

All canonical field names use **camelCase** (for JSON/API surfaces) and **snake_case** (for Python/DuckDB).

| Layer | Convention | Example |
|---|---|---|
| JSON API | camelCase | `transactionId` |
| Python code | snake_case | `transaction_id` |
| DuckDB columns | snake_case | `transaction_id` |
| DuckDB tables | snake_case | `transactions` |

When both appear in this document, the camelCase form is canonical. The snake_case form is the Python/DuckDB rendering.

---

## 2. Transaction Fields

### `transactionId` / `transaction_id`

| Property | Value |
|---|---|
| Type | `string` |
| Format | Bitcoin transaction hash (64-character hex string) |
| Availability | `REQUIRED_CANONICAL` |
| Source | Raw dataset — native Bitcoin transaction ID |
| Nullable | No |
| Example | `"a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d"` |
| Notes | Also called txid, tx_hash in different datasets. Always 64 hex chars in valid Bitcoin data. |

---

### `blockHash` / `block_hash`

| Property | Value |
|---|---|
| Type | `string` |
| Format | Bitcoin block hash (64-character hex string) |
| Availability | `OPTIONAL_CANONICAL` |
| Source | Raw dataset |
| Nullable | Yes |
| Example | `"000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"` |
| Notes | May not be present in feature-level datasets like Elliptic. |

---

### `blockHeight` / `block_height`

| Property | Value |
|---|---|
| Type | `integer` |
| Range | ≥ 0 |
| Availability | `OPTIONAL_CANONICAL` |
| Source | Raw dataset or derived from block hash |
| Nullable | Yes |
| Example | `170` |
| Notes | Genesis block = 0. Monotonically increasing. |

---

### `timestamp` / `timestamp`

| Property | Value |
|---|---|
| Type | `datetime (UTC, timezone-aware)` |
| Format | ISO 8601: `"2009-01-12T03:30:25+00:00"` |
| Availability | `OPTIONAL_CANONICAL` (see note) |
| Source | Raw dataset (as UNIX epoch or ISO string) |
| Nullable | Yes |
| Example | `"2009-01-12T03:30:25+00:00"` |
| Notes | Datasets that use "time steps" instead of absolute timestamps must document this. The canonical form is always UTC datetime. If the dataset uses UNIX epoch integers, they are converted during normalization. |

---

### `inputCount` / `input_count`

| Property | Value |
|---|---|
| Type | `integer` |
| Range | ≥ 1 |
| Availability | `OPTIONAL_CANONICAL` |
| Source | Raw dataset or derived from inputs list |
| Nullable | Yes |
| Example | `2` |

---

### `outputCount` / `output_count`

| Property | Value |
|---|---|
| Type | `integer` |
| Range | ≥ 1 |
| Availability | `OPTIONAL_CANONICAL` |
| Source | Raw dataset or derived from outputs list |
| Nullable | Yes |
| Example | `3` |

---

### `totalInputValueSatoshi` / `total_input_value_satoshi`

| Property | Value |
|---|---|
| Type | `integer (satoshis)` |
| Range | ≥ 0 |
| Availability | `OPTIONAL_CANONICAL` |
| Source | Derived (sum of all input values) or raw dataset |
| Nullable | Yes |
| Conversion | 1 BTC = 100,000,000 satoshis |
| Example | `500000000` (= 5 BTC) |
| Notes | **Internal storage always in satoshis as integer** to avoid floating-point precision errors. See [Section 6: Bitcoin Value Convention](#6-bitcoin-value-convention). |

---

### `totalOutputValueSatoshi` / `total_output_value_satoshi`

| Property | Value |
|---|---|
| Type | `integer (satoshis)` |
| Range | ≥ 0 |
| Availability | `OPTIONAL_CANONICAL` |
| Source | Derived (sum of all output values) or raw dataset |
| Nullable | Yes |
| Conversion | 1 BTC = 100,000,000 satoshis |
| Example | `499800000` |

---

### `feeSatoshi` / `fee_satoshi`

| Property | Value |
|---|---|
| Type | `integer (satoshis)` |
| Range | ≥ 0 |
| Availability | `OPTIONAL_CANONICAL` — `DERIVED` if inputs and outputs are known |
| Source | `totalInputValueSatoshi - totalOutputValueSatoshi` or raw dataset |
| Nullable | Yes |
| Example | `200000` |
| Notes | Can be derived as: `fee = total_input_value - total_output_value`. If this yields negative, the data has an error. |

---

### `transactionSizeBytes` / `transaction_size_bytes`

| Property | Value |
|---|---|
| Type | `integer` |
| Range | ≥ 10 |
| Availability | `DATASET_DEPENDENT` |
| Nullable | Yes |
| Example | `374` |

---

### `label` / `label`

| Property | Value |
|---|---|
| Type | `string (enum)` |
| Values | `"illicit"`, `"licit"`, `"unknown"` |
| Availability | `DATASET_DEPENDENT` (present in Elliptic dataset only) |
| Nullable | Yes |
| Example | `"illicit"` |
| Notes | When available, used for supervised ML training. Not present in raw transaction datasets. |

---

## 3. Input Fields (Transaction Inputs)

A transaction can have multiple inputs. Each input is represented as a sub-record.

### `inputAddress` / `input_address`

| Property | Value |
|---|---|
| Type | `string` |
| Format | Bitcoin address (P2PKH, P2SH, Bech32) |
| Availability | `DATASET_DEPENDENT` |
| Nullable | Yes |
| Example | `"1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf'NA"` |
| Notes | May not be available in all dataset formats. Some datasets anonymize addresses. |

---

### `inputValueSatoshi` / `input_value_satoshi`

| Property | Value |
|---|---|
| Type | `integer (satoshis)` |
| Range | ≥ 0 |
| Availability | `DATASET_DEPENDENT` |
| Nullable | Yes |

---

### `inputSequenceNumber` / `input_sequence_number`

| Property | Value |
|---|---|
| Type | `integer` |
| Availability | `DATASET_DEPENDENT` |
| Nullable | Yes |

---

## 4. Output Fields (Transaction Outputs)

### `outputAddress` / `output_address`

| Property | Value |
|---|---|
| Type | `string` |
| Format | Bitcoin address |
| Availability | `OPTIONAL_CANONICAL` |
| Nullable | Yes |
| Example | `"3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"` |

---

### `outputValueSatoshi` / `output_value_satoshi`

| Property | Value |
|---|---|
| Type | `integer (satoshis)` |
| Range | ≥ 0 |
| Availability | `OPTIONAL_CANONICAL` |
| Nullable | Yes |

---

### `outputIndex` / `output_index`

| Property | Value |
|---|---|
| Type | `integer` |
| Range | ≥ 0 |
| Availability | `OPTIONAL_CANONICAL` |
| Nullable | Yes |
| Notes | Output index (vout) within the transaction. |

---

### `outputScriptType` / `output_script_type`

| Property | Value |
|---|---|
| Type | `string (enum)` |
| Values | `"P2PKH"`, `"P2SH"`, `"P2WPKH"`, `"P2WSH"`, `"P2TR"`, `"NONSTANDARD"`, `"UNKNOWN"` |
| Availability | `DATASET_DEPENDENT` |
| Nullable | Yes |

---

## 5. Address / Entity Fields

### `addressId` / `address_id`

| Property | Value |
|---|---|
| Type | `string` |
| Format | Bitcoin address string (same as Bitcoin address) |
| Availability | `REQUIRED_CANONICAL` (for address-level analysis) |
| Nullable | No |
| Example | `"bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"` |
| Notes | The canonical identifier for an address entity. In this system, `addressId` IS the Bitcoin address string. Do not generate a separate UUID for this unless a dataset has anonymized addresses. |

---

### `entityId` / `entity_id`

| Property | Value |
|---|---|
| Type | `string` |
| Format | UUID v4 or deterministic hash |
| Availability | `DERIVED` |
| Nullable | No |
| Notes | A higher-level entity grouping one or more addresses (e.g., a wallet cluster). If wallet clustering is not implemented, `entityId = addressId`. See [Q-007 in architecture-decisions.md](../architecture/architecture-decisions.md). |

---

### `addressType` / `address_type`

| Property | Value |
|---|---|
| Type | `string (enum)` |
| Values | `"P2PKH"`, `"P2SH"`, `"P2WPKH"`, `"P2WSH"`, `"P2TR"`, `"UNKNOWN"` |
| Availability | `DATASET_DEPENDENT` |
| Nullable | Yes |

---

## 6. Bitcoin Value Convention

> **This section is authoritative for all value representations in the system.**

**Internal canonical representation: SATOSHIS as integer.**

| Context | Unit | Type | Example |
|---|---|---|---|
| Internal storage (DuckDB) | satoshis | `BIGINT` | `500000000` |
| Python processing | satoshis | `int` or `numpy.int64` | `500000000` |
| API response | BTC (decimal string) | `string` | `"5.00000000"` |
| Frontend display | BTC | formatted string | `"5.00000000 BTC"` |

**Conversion**:
```python
# BTC to satoshis (always use this for input)
satoshis = int(round(btc_value * 100_000_000))

# Satoshis to BTC (only for API/display output)
btc_str = f"{satoshi_value / 100_000_000:.8f}"
```

**Rationale**: Floating-point arithmetic on BTC values can introduce precision errors. Storing as integers (satoshis) is precise. Never store raw BTC floats in DuckDB.

**API representation**: The API returns BTC values as **string-encoded decimal with 8 decimal places** to avoid JSON float precision issues. The frontend must not perform arithmetic on these strings without parsing to a Decimal type.

---

## 7. Identifier Convention

| Concept | Identifier Name | Type | Source |
|---|---|---|---|
| Bitcoin transaction | `transactionId` | string (hex) | Native Bitcoin |
| Bitcoin block | `blockHash` | string (hex) | Native Bitcoin |
| Block position | `blockHeight` | integer | Native Bitcoin |
| Bitcoin address | `addressId` | string | Native Bitcoin address |
| Entity (wallet cluster) | `entityId` | string (UUID or hash) | `DERIVED` |
| Dataset | `datasetId` | string (UUID v4) | System-generated |
| Analysis run | `analysisId` | string (UUID v4) | System-generated |
| ML model | `modelId` | string | Named + versioned |
| ML prediction | `predictionId` | string (UUID v4) | System-generated |
| Graph export | `graphId` | string (UUID v4) | System-generated |

---

## 8. Timestamp Convention

All timestamps in this system use **UTC timezone-aware datetime**.

| Context | Format |
|---|---|
| JSON API | ISO 8601 with timezone: `"2009-01-12T03:30:25+00:00"` |
| DuckDB | `TIMESTAMP WITH TIME ZONE` |
| Python | `datetime.datetime` with `tzinfo=timezone.utc` |
| UNIX epoch input | Converted to UTC datetime during normalization |

The **frontend** is responsible for converting UTC datetimes to the investigator's local timezone for display. The backend and ML layer must never return locale-specific formatted dates.

---

## 9. Status Enums

### Dataset Status

| Value | Meaning |
|---|---|
| `uploaded` | File received, not yet processed |
| `processing` | Pipeline is running |
| `ready` | Processing complete, available for analysis |
| `error` | Processing failed |

### Analysis Status

| Value | Meaning |
|---|---|
| `pending` | Analysis queued |
| `running` | Analysis in progress |
| `completed` | Analysis finished successfully |
| `failed` | Analysis encountered an error |

### Risk Level

| Value | Risk Score Range | Meaning |
|---|---|---|
| `low` | 0.0 – 0.319 | Low analytical priority |
| `medium` | 0.32 – 0.499 | Warrants attention |
| `high` | 0.50 – 0.669 | Significant risk indicators |
| `critical` | 0.67 – 1.00 | Highest priority for investigation |

> **Note**: Risk score thresholds are `DECISION REQUIRED` — the above values are proposed defaults. See [risk-scoring.md](../ml/risk-scoring.md).

---

*Last updated: 2026-09-11 | Owner: All (canonical reference)*
*References: [canonical-schema.md](./canonical-schema.md) | [naming-conventions.md](../development/naming-conventions.md)*

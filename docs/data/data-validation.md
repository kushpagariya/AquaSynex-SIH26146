# Data Validation Rules

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Authority**: Backend validation rules for API inputs are in [validation-rules.md](../backend/validation-rules.md).
> This document covers **data pipeline validation** — validating raw dataset files during ingestion.

---

## 1. Validation Philosophy

Validation occurs at two distinct stages:

1. **File-level validation** — Is the file parseable and structurally valid?
2. **Record-level validation** — Are individual records acceptable?

Validation errors are **non-fatal warnings** unless they affect required fields. The pipeline reports all validation issues without failing silently.

---

## 2. File-Level Validation

| Check | Rule | On Failure |
|---|---|---|
| File format | File matches declared format (CSV, JSON, Parquet) | `DATASET_ERROR` — reject |
| File not empty | At least 1 data row | `DATASET_ERROR` — reject |
| Encoding | UTF-8 or ASCII | Attempt UTF-8-with-errors; warn if fallback needed |
| CSV header | Header row present for CSV files | `DATASET_ERROR` — reject |
| JSON structure | Top-level must be array or newline-delimited | `DATASET_ERROR` — reject |
| Minimum columns | At least `transactionId` OR one identifiable transaction field | `DATASET_ERROR` — reject |

---

## 3. Required Field Rules

At minimum, the dataset must contain enough information to identify transactions. 

**Minimum viable dataset**:
- At least one column mappable to `transactionId`.

**Preferred minimum** (for useful analysis):
- `transactionId`
- At least one of: `timestamp`, `blockHeight`
- At least one of: address field, `inputCount`/`outputCount`, value field

If a dataset lacks address information, graph construction will be limited. This is reported as a warning, not an error.

---

## 4. Field-Level Validation Rules

### `transactionId`

| Rule | Constraint |
|---|---|
| Not null | Required |
| String type | Must be string |
| Length | 64 characters for real Bitcoin txids; shorter lengths warn but do not reject |
| Hex characters | Must match `[0-9a-fA-F]+`; warn on failure |
| Uniqueness | Must be unique within dataset; duplicates are logged and first occurrence kept |

### `blockHeight`

| Rule | Constraint |
|---|---|
| Type | Integer |
| Range | 0 ≤ blockHeight ≤ 1,000,000 (upper bound based on current chain; warn if exceeded) |
| Non-negative | Reject negative values |

### `timestamp`

| Rule | Constraint |
|---|---|
| Parseable | Must be parseable as ISO 8601 datetime or UNIX epoch integer |
| Range | 2009-01-03 (genesis block) ≤ timestamp ≤ current_time + 1 hour (tolerance) |
| Timezone | If no timezone info, assume UTC; log assumption |

### `totalInputValueSatoshi` / `totalOutputValueSatoshi` / `feeSatoshi`

| Rule | Constraint |
|---|---|
| Non-negative | Values < 0 are invalid; set to null and warn |
| Reasonable max | > 2.1 × 10^15 satoshis (21M BTC) is impossible; warn |
| Consistency | If all three are present: `fee = input - output`. Discrepancy > 1 satoshi → warn |
| Float input | If BTC float is detected, convert using `satoshi = round(btc * 1e8)` |

### `inputCount` / `outputCount`

| Rule | Constraint |
|---|---|
| Non-negative | 0 or negative → reject |
| Integer | Must be integer or convertible to integer |
| Reasonable max | > 10,000 → warn (possible data error) |

### `label`

| Rule | Constraint |
|---|---|
| Allowed values | `"illicit"`, `"licit"`, `"unknown"`, null |
| Case | Case-normalize to lowercase |
| Unknown values | Map to `"unknown"` and warn |

### `outputAddress` / `inputAddress`

| Rule | Constraint |
|---|---|
| String | Must be string |
| Format | Should match known Bitcoin address patterns (P2PKH, P2SH, Bech32); warn on mismatch but do not reject |
| Non-empty | Empty string treated as null |

---

## 5. Record-Level Filtering

After field validation, individual records may be:

| Action | When |
|---|---|
| **Accept** | Record passes all required field checks |
| **Warn** | Record has issues in optional fields; include in canonical data with null for problematic fields |
| **Reject** | Record has null or invalid `transactionId`; excluded from canonical data |

**Rejection rate threshold**: If >10% of records are rejected, escalate to a `DATASET_ERROR` warning at the analysis level.

---

## 6. Validation Report Structure

The data pipeline produces a validation report for each dataset. This is stored in `datasets.validation_summary`.

```json
{
  "totalRows": 1000000,
  "rejectedRows": 152,
  "warnedRows": 8430,
  "rejectionRate": 0.000152,
  "fieldCoverage": {
    "transactionId": 1.0,
    "blockHeight": 0.99,
    "timestamp": 0.98,
    "totalInputValueSatoshi": 0.87,
    "outputAddress": 0.73,
    "label": 0.0
  },
  "issues": [
    {
      "type": "DUPLICATE_TRANSACTION_ID",
      "count": 45,
      "severity": "warning",
      "message": "45 duplicate transaction IDs found; first occurrence retained"
    },
    {
      "type": "INVALID_TIMESTAMP",
      "count": 107,
      "severity": "warning",
      "message": "107 timestamps could not be parsed; set to null"
    }
  ],
  "analysisCapability": {
    "graphAnalysis": true,
    "temporalAnalysis": true,
    "valueAnalysis": true,
    "labelBasedTraining": false
  }
}
```

---

## 7. Analysis Capability Assessment

After validation, the pipeline determines what types of analysis are possible:

| Capability | Required Fields | Status if Missing |
|---|---|---|
| `graphAnalysis` | `outputAddress` or `inputAddress` | Disabled; warn |
| `temporalAnalysis` | `timestamp` | Disabled; warn |
| `valueAnalysis` | `totalInputValueSatoshi` or `totalOutputValueSatoshi` | Disabled; warn |
| `labelBasedTraining` | `label` | Disabled; unsupervised only |
| `feeAnalysis` | `feeSatoshi` (or derivable) | Disabled; warn |

---

*Last updated: 2026-09-11 | Owner: ML Owner (Data Pipeline)*
*References: [data-dictionary.md](./data-dictionary.md) | [canonical-schema.md](./canonical-schema.md) | [validation-rules.md](../backend/validation-rules.md)*

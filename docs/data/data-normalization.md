# Data Normalization

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

---

## 1. Overview

Data normalization transforms raw dataset fields into the canonical internal representation. Normalization is a pipeline step that runs after file-level validation and before canonical record production.

```
Raw field value
      │
      ▼
Type coercion
      │
      ▼
Value conversion (e.g., BTC → satoshis)
      │
      ▼
Timestamp standardization (→ UTC)
      │
      ▼
Null handling
      │
      ▼
Column renaming (→ canonical name)
      │
      ▼
Canonical record
```

---

## 2. Column Mapping

Raw datasets use various column names. The data pipeline must map them to canonical names.

The mapping is stored per-dataset in `datasets.canonical_field_map` as a JSON object.

### Common raw column name aliases

| Canonical Field | Common Raw Column Names |
|---|---|
| `transaction_id` | `txid`, `tx_id`, `tx_hash`, `hash`, `transaction_hash`, `id` |
| `block_hash` | `block_hash`, `blockhash`, `block` |
| `block_height` | `block_height`, `height`, `block_number`, `blockheight` |
| `timestamp` | `timestamp`, `time`, `block_time`, `date`, `created_at`, `tx_time` |
| `input_count` | `input_count`, `inputs`, `n_inputs`, `vin_count`, `num_inputs` |
| `output_count` | `output_count`, `outputs`, `n_outputs`, `vout_count`, `num_outputs` |
| `total_input_value_satoshi` | `total_input_value`, `input_value`, `in_value`, `total_inputs_btc` |
| `total_output_value_satoshi` | `total_output_value`, `output_value`, `out_value`, `total_outputs_btc` |
| `fee_satoshi` | `fee`, `fees`, `tx_fee`, `miner_fee` |
| `transaction_size_bytes` | `size`, `weight`, `vsize`, `byte_size` |
| `label` | `class`, `label`, `category`, `is_illicit`, `illicit` |
| `output_address` | `address`, `output_address`, `to_address`, `recipient` |
| `input_address` | `input_address`, `from_address`, `sender`, `spending_address` |

**Priority**: If multiple column aliases are present, take the most specific match (longer/more precise name wins).

---

## 3. Value Normalization Rules

### 3.1 Bitcoin Value Fields

**All Bitcoin value fields are normalized to satoshis (integer) internally.**

| Input format | Normalization |
|---|---|
| Float BTC (e.g., `1.5`) | `int(round(value * 100_000_000))` |
| Integer satoshis | Use directly |
| String BTC (e.g., `"1.5"`) | Parse to float, then convert |
| String satoshis (e.g., `"150000000"`) | Parse to integer |
| Null / missing | Set to `null`; do not default to 0 |

**Never assume missing value means 0 BTC.** A missing fee is different from a zero fee.

### 3.2 Timestamp Normalization

All timestamps are converted to UTC timezone-aware datetime objects.

| Input format | Normalization |
|---|---|
| UNIX epoch (integer, seconds) | `datetime.utcfromtimestamp(value).replace(tzinfo=timezone.utc)` |
| UNIX epoch (integer, milliseconds) | Divide by 1000 first |
| ISO 8601 with timezone | Parse directly; convert to UTC |
| ISO 8601 without timezone | Assume UTC; log assumption |
| String date `"YYYY-MM-DD"` | Parse to midnight UTC |
| "Time step" (integer ordinal) | Map to `null` timestamp; store time step separately |

**Timestamps before 2009-01-03 are invalid** (pre-genesis) and set to null with a warning.

### 3.3 Integer Fields

| Input format | Normalization |
|---|---|
| Float (e.g., `2.0`) | Convert to int if no decimal part; warn if decimal part > 0 |
| String integer (e.g., `"2"`) | Parse to integer |
| Negative | Set to null; warn |
| NaN | Set to null |

### 3.4 String Fields

| Input format | Normalization |
|---|---|
| Whitespace padding | Strip leading/trailing whitespace |
| Empty string | Convert to null |
| Mixed case (txid, addresses) | Lowercase (txids and addresses are case-insensitive in Bitcoin) |
| None / NaN | Convert to null |

### 3.5 Label Field

| Input value | Normalized value |
|---|---|
| `1`, `"1"`, `"illicit"`, `"ILLICIT"`, `True` | `"illicit"` |
| `0`, `"0"`, `"licit"`, `"LICIT"`, `"legitimate"`, `False` | `"licit"` |
| `2`, `"-1"`, `"unknown"`, `null`, missing | `"unknown"` |

---

## 4. Derived Field Computation

Some canonical fields are derived from other fields if not present in the raw data:

| Derived Field | Derivation | Condition |
|---|---|---|
| `fee_satoshi` | `total_input_value_satoshi - total_output_value_satoshi` | Both input/output values available and result ≥ 0 |
| `input_count` | `COUNT(inputs)` | Per-input records available |
| `output_count` | `COUNT(outputs)` | Per-output records available |
| `total_input_value_satoshi` | `SUM(input_value_satoshi)` | Per-input values available |
| `total_output_value_satoshi` | `SUM(output_value_satoshi)` | Per-output values available |
| `input_id` | `f"{transaction_id}:{input_index}"` | Always derived |
| `output_id` | `f"{transaction_id}:{output_index}"` | Always derived |
| `address.first_seen_timestamp` | `MIN(timestamp)` for transactions involving address | Address aggregation |
| `address.last_seen_timestamp` | `MAX(timestamp)` | Address aggregation |
| `address.total_received_satoshi` | `SUM(output_value_satoshi)` | From outputs |
| `address.total_sent_satoshi` | `SUM(input_value_satoshi)` | From inputs |

---

## 5. Normalization Output

After normalization, the pipeline produces:

1. **Canonical transaction records** — written to `transactions` DuckDB table / Parquet file.
2. **Canonical input records** (if available) — written to `transaction_inputs`.
3. **Canonical output records** (if available) — written to `transaction_outputs`.
4. **Derived address records** — written to `addresses` (aggregated from output addresses).
5. **Canonical field map** — stored in `datasets.canonical_field_map`.
6. **Validation report** — stored in `datasets.validation_summary`.

---

## 6. What Normalization Does NOT Do

Normalization does NOT:
- Filter out transactions based on risk or suspicion.
- Add ML features or graph features.
- Make analytical decisions.
- Modify the data pipeline contract without updating this document.

---

*Last updated: 2026-09-11 | Owner: ML Owner (Data Pipeline)*
*References: [data-dictionary.md](./data-dictionary.md) | [canonical-schema.md](./canonical-schema.md) | [data-validation.md](./data-validation.md)*

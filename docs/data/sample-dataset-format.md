# Sample Dataset Format

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> This document provides concrete examples of accepted dataset formats and how they map to canonical fields.

---

## 1. Minimal CSV Dataset

The minimum viable CSV dataset for transaction-level analysis (no address detail):

```csv
txid,block_height,timestamp,input_count,output_count,total_input_value,total_output_value,fee
a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d,170,1231731025,1,1,500000000,500000000,0
f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16,181,1232346882,1,2,1000000000,999900000,100000
```

**Column mappings detected**:
- `txid` → `transaction_id`
- `block_height` → `block_height`
- `timestamp` → `timestamp` (UNIX epoch)
- `input_count` → `input_count`
- `output_count` → `output_count`
- `total_input_value` → `total_input_value_satoshi` (BTC float detected → converted)
- `total_output_value` → `total_output_value_satoshi`
- `fee` → `fee_satoshi` (satoshi integer)

---

## 2. Rich Transaction CSV with Addresses

```csv
tx_hash,block_height,block_time,n_inputs,n_outputs,in_value,out_value,tx_fee,out_address_0,out_value_0,out_address_1,out_value_1
a1075db...d48d,170,2009-01-12T03:30:25Z,1,2,5.0,4.999,0.001,1A1zP1eP5QGe...,3.0,12cbQLTFMXRnSzktFkuoG3eHoMeFtpTu1,1.999
```

**Notes**:
- `block_time` → `timestamp` (ISO 8601, no timezone → assume UTC)
- `in_value` / `out_value` / `tx_fee` → float BTC → convert to satoshis
- Multi-output columns (`out_address_0`, `out_address_1`) require special handling during normalization to produce multiple output records.

---

## 3. Elliptic Dataset Format (Feature-Level)

The Elliptic dataset does not contain raw transaction fields. It provides pre-computed features.

```csv
txId,timestep,class,feature1,feature2,...,feature94
230425980,1,2,0.0,-0.0,...,0.0
5530458,-1,2,0.0,0.0,...,0.0
```

**Mappings**:
- `txId` → `transaction_id` (anonymized, not a real txid)
- `timestep` → stored as `block_height` surrogate (not a real block height)
- `class` → `label` (1 = illicit, 2 = unknown; note: no class 0 = licit in some versions)
- `feature1...feature94` → stored as pre-computed features, NOT in the canonical transaction table

**Special handling**: The Elliptic dataset is NOT normalized into the standard canonical schema because it lacks raw transaction fields. It is treated as a **pre-featurized dataset** and fed directly to the ML pipeline. The graph layer cannot be applied to this dataset.

---

## 4. JSON Array Format

```json
[
  {
    "txid": "a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d",
    "block_height": 170,
    "timestamp": "2009-01-12T03:30:25+00:00",
    "input_count": 1,
    "output_count": 1,
    "total_input_value": 50.0,
    "total_output_value": 50.0,
    "fee": 0.0,
    "outputs": [
      {
        "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf'NA",
        "value": 50.0,
        "index": 0
      }
    ]
  }
]
```

**Notes**:
- Nested `outputs` array → produces multiple `transaction_outputs` records.
- `value` is BTC float → convert to satoshis.

---

## 5. Parquet Format (Preferred for Large Datasets)

Parquet is the preferred format for large datasets (>100k transactions).

**Expected schema** (column names are examples — aliases are resolved via the canonical field map):

```
Schema:
  transaction_id: STRING
  block_height:   INT32
  timestamp:      TIMESTAMP(UTC)
  input_count:    INT32
  output_count:   INT32
  total_input_value_satoshi:  INT64
  total_output_value_satoshi: INT64
  fee_satoshi:    INT64
  label:          STRING (nullable)
```

**Advantages**:
- Column-oriented: DuckDB reads only needed columns.
- Native timestamp support.
- Integer satoshi representation avoids float conversion.
- Compressed: 10× smaller than equivalent CSV.

---

## 6. Dataset Size Guidelines

| Size | Format Recommendation | DuckDB Strategy |
|---|---|---|
| < 10K transactions | CSV or JSON | Load directly into DuckDB |
| 10K – 1M transactions | CSV or Parquet | Load into DuckDB; use Parquet for repeated access |
| 1M – 10M transactions | Parquet | Stream via DuckDB Parquet reader |
| > 10M transactions | Parquet (partitioned) | `DECISION REQUIRED` — may need partitioning strategy |

---

*Last updated: 2026-09-11 | Owner: ML Owner (Data Pipeline)*
*References: [canonical-schema.md](./canonical-schema.md) | [data-normalization.md](./data-normalization.md) | [data-sources.md](./data-sources.md)*

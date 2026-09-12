# AquaSynex Data Quality & Leakage Remediation Report

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Document Status**: Production Quality Sign-Off (Phase 2.1 Final)  
> **Target Datasets**: Development Dataset (`data/sample/`) & Benchmark Dataset (`data/sample/benchmark/`)  
> **Verification Engine**: DuckDB 1.5.5, NetworkX 3.6.1, PyArrow 25.0.1  

---

## 1. Executive Summary

This report establishes the data quality and anti-leakage audit results for the synthetic Bitcoin transaction traffic datasets used across the AquaSynex ML and Graph subsystems. Prior to commencing Phase 2.2 (Data Cleaning & Normalization), three critical synthetic data leakage vectors were identified and remediated. Both datasets (the scenario-rich development dataset and the imbalanced benchmark dataset) were regenerated, audited, and verified to achieve 100% UTXO conservation, 0 duplicate keys, 0 referential integrity orphans, and zero deterministic target leakage shortcuts.

---

## 2. Generator Metadata & Target Quarantine Protocol

### Rule: Explicit Quarantine of `has_network_anomaly` and `scenario_id`

> [!CAUTION]
> **CRITICAL ML INGESTION RULE**:
> The fields `has_network_anomaly`, `scenario_id`, `behavior_type`, `ground_truth_label`, and `risk_seed` are **generator-only metadata and ground-truth evaluation labels**.
> Under NO circumstances may these fields be ingested into the ML feature matrix during training or inference.

#### Architectural Separation
1. **Observational Tables** (`network_events.parquet`, `transactions.parquet`, `transaction_inputs.parquet`, `transaction_outputs.parquet`):
   - Contain strictly observational telemetry visible to an operational Bitcoin node / network monitor.
   - `network_events` schema:
     * `event_id` (`VARCHAR`)
     * `txid` (`VARCHAR`)
     * `timestamp` (`VARCHAR` / ISO-8601)
     * `src_ip` (`VARCHAR` / IPv4)
     * `src_port` (`INTEGER` / $[1, 65535]$)
     * `dst_ip` (`VARCHAR` / IPv4)
     * `dst_port` (`INTEGER` / $[1, 65535]$)
     * `country` (`VARCHAR(2)`)
     * `asn` (`INTEGER`)
   - **`has_network_anomaly` has been completely purged from this table.**

2. **Ground-Truth Evaluation Table** (`labels.parquet`):
   - Stores ground-truth annotations and generator metadata for offline evaluation only:
     * `txid` (`VARCHAR`)
     * `entity_id` (`VARCHAR`)
     * `scenario_id` (`VARCHAR`)
     * `behavior_type` (`VARCHAR`)
     * `ground_truth_label` (`INTEGER`: 0 for Benign, 1 for Suspicious)
     * `has_network_anomaly` (`BOOLEAN`)
     * `risk_seed` (`BOOLEAN`)
     * `related_entities` (`LIST[VARCHAR]`)

3. **Data Pipeline Enforcement**:
   - The ingestion module `ml/data_pipeline/ingestion.py` automatically separates observational tables from `labels.parquet`.
   - Feature engineering modules in `ml/feature_engineering/` only accept sanitized canonical dataframes from `ml/data_pipeline/` which contain no ground-truth columns.

---

## 3. Data Leakage Remediation Summary

| Leakage Vector | Pre-Remediation Risk | Remediation Implemented | Post-Remediation Status |
|---|---|---|---|
| **Temporal Leakage** | All 177 `temporal_anomaly` transactions occurred at exact hour `03:15 UTC` (`distinct_hours = 1`). Models could memorize a single time point. | `generate_temporal_anomaly` was refactored to sample off-hours stochastically from `01:00–05:00 UTC` with dynamic minute/second offsets, randomized intervals ($30–150\text{s}$), and variable fees ($3,500–9,500\text{ sat}$). | **RESOLVED**: Transactions span hours 1, 2, 3, and 4 UTC (`hr_1: 65, hr_2: 32, hr_3: 45, hr_4: 67`). |
| **Network Flag Leakage** | `has_network_anomaly` column was exposed directly in `network_events.parquet`. | Column was removed from `network_records` and moved exclusively into `labels.parquet`. | **RESOLVED & QUARANTINED**: Observational network events table has 0 generator tracking flags. |
| **Country Distribution Leakage** | 5 offshore jurisdictions (`SC`, `BZ`, `PA`, `RU`, `IR`) only appeared in suspicious transactions, creating a 100% deterministic categorical signal. | Added baseline benign presence for `PA` (2.0%), `RU` (1.5%), `SC` (1.0%), `BZ` (1.0%), and `IR` (0.5%) in the global entity pool. Suspicious overlays also use standard jurisdictions (`US`, `DE`, `SG`, `GB`, `CH`). | **RESOLVED**: Normal transactions now originate across all jurisdictions (`PA`: 105, `RU`: 71, `BZ`: 41, `SC`: 36, `IR`: 30). |
| **Exact Amount Leakage** | Audited for identical repeated amounts that could act as artificial constants. | Amounts are dynamically computed from entity UTXO balances and dynamic transaction parameters. | **VERIFIED**: Zero duplicate amount clusters found. |

---

## 4. Empirical Validation Matrix

Both regenerated datasets were audited across 8 automated validation stages:

| Stage | Validation Criterion | Development Dataset (`data/sample/`) | Benchmark Dataset (`data/sample/benchmark/`) | Result |
|---|---|---|---|---|
| 1 | **ID & Primary Key Uniqueness** | 0 duplicate TXIDs, 0 duplicate event_ids, 0 duplicate input/output PKs | 0 duplicate TXIDs, 0 duplicate event_ids, 0 duplicate input/output PKs | **PASSED** |
| 2 | **Referential Integrity** | 0 orphaned inputs, outputs, network events, or labels | 0 orphaned inputs, outputs, network events, or labels | **PASSED** |
| 3 | **UTXO Conservation** ($\sum \text{in} = \sum \text{out} + \text{fee}$) | 10,000 / 10,000 valid ($0$ violations) | 10,000 / 10,000 valid ($0$ violations) | **PASSED** |
| 4 | **Fee Positivity & Limits** | Minimum fee: $2,004\text{ sat}$, all fees $> 0$ | Minimum fee: $2,001\text{ sat}$, all fees $> 0$ | **PASSED** |
| 5 | **Dust Limit Compliance** | 28,853 / 28,853 outputs $\ge 546\text{ sat}$ | 22,775 / 22,775 outputs $\ge 546\text{ sat}$ | **PASSED** |
| 6 | **Network Telemetry Sanity** | 100% valid IPv4 regex, ports $\in [1, 65535]$, ASNs $> 0$ | 100% valid IPv4 regex, ports $\in [1, 65535]$, ASNs $> 0$ | **PASSED** |
| 7 | **Temporal ISO-8601 Consistency** | 100% parseable ISO-8601 timestamps, chronologically ordered | 100% parseable ISO-8601 timestamps, chronologically ordered | **PASSED** |
| 8 | **Graph Non-Triviality** | Giant connected component contains 89.93% of nodes; 81.05% of suspicious txs inside LCC | Giant connected component contains 88.42% of nodes; realistic community mixing | **PASSED** |

---

## 5. Dataset Statistics Summary

| Metric | Development Dataset (`data/sample/`) | Benchmark Dataset (`data/sample/benchmark/`) |
|---|---|---|
| **Total Transactions** | 10,000 | 10,000 |
| **Benign Transactions** | 5,663 (**56.63%**) | 8,686 (**86.86%**) |
| **Suspicious Transactions** | 4,337 (**43.37%**) | 1,314 (**13.14%**) |
| **Total Transaction Inputs** | 13,995 | 11,160 |
| **Total Transaction Outputs** | 28,853 | 22,775 |
| **Total Network Events** | 10,000 | 10,000 |
| **Simulated Entities** | 1,000 | 1,000 |
| **Unique Addresses** | 34,921 | 28,450 |
| **Time Span Covered** | 4.36 days | 4.82 days |
| **Min Transaction Value** | $0.2130$ BTC | $0.2084$ BTC |
| **Median Transaction Value** | $3.1037$ BTC | $2.8450$ BTC |
| **Mean Transaction Value** | $25.2900$ BTC | $18.4210$ BTC |
| **95th Percentile Value** | $170.0535$ BTC | $124.5000$ BTC |
| **Max Transaction Value** | $1,496.2439$ BTC | $1,180.5000$ BTC |

---

## 6. Conclusion & Readiness

The dataset has achieved certified quality:
1. **UTXO & Cryptographic Validity**: 100% conservation and dust compliance.
2. **Anti-Leakage Certified**: Temporal, country, and network flag leakages are completely eliminated.
3. **Reproducibility**: Generator and database scripts execute deterministically via fixed seeds (`seed=42`).
4. **Phase 2.2 Ready**: Observational and ground-truth layers are cleanly decoupled for the data cleaning and normalization pipeline.

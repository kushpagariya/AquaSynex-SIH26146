# AquaSynex Feature Engineering Module (Phase 2.3)

**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

This package implements the feature extraction engine that transforms canonical Bitcoin transaction and network telemetry records into a structured, explainable, and leak-free feature matrix for downstream ML anomaly detection and supervised classification.

---

## 1. Architecture & Module Structure

```
ml/feature_engineering/
├── __init__.py
├── transaction_features.py    # 15 transaction-level amounts, counts, and ratios
├── address_features.py        # 8 historical address behavior features (strict t < T_tx)
├── temporal_features.py       # 7 rolling temporal activity and cadence features (6 canonical + 1 experimental)
├── network_features.py        # 6 network transport, ASN, and IP diversity features (5 numeric + 1 categorical context)
├── feature_pipeline.py        # Master pipeline, quality auditing, and Parquet/DuckDB export
└── README.md                  # Package documentation and usage guide
```

---

## 2. Feature Matrix Specification (41 Total Columns)

The feature pipeline outputs `feature_matrix_v1.parquet` containing:
- **1 Key Column**: `transaction_id` (64-char hex identifier, not an ML feature)
- **40 Features**:
  * **15 Transaction Features**: `tx_input_count`, `tx_output_count`, `tx_input_output_ratio`, `tx_total_input_sats`, `tx_total_output_sats`, `tx_fee_sats`, `tx_size_bytes`, `tx_fee_rate_sat_per_byte`, `tx_value_balance_ratio`, `tx_avg_input_value_sats`, `tx_max_input_value_sats`, `tx_avg_output_value_sats`, `tx_max_output_value_sats`, `tx_log_total_value`, `tx_log_fee`.
  * **8 Address/Entity Behavioral Features**: `addr_hist_tx_count`, `addr_hist_total_sent_sats`, `addr_hist_total_received_sats`, `addr_hist_avg_tx_val_sats`, `addr_hist_unique_counterparties`, `addr_hist_active_days`, `addr_hist_tx_per_day`, `addr_reuse_count`.
  * **7 Temporal Cadence Features**: `time_hour_of_day`, `time_day_of_week`, `time_since_prev_global_tx_sec`, `time_since_prev_addr_tx_sec`, `time_txs_last_1m`, `time_txs_last_5m`, `time_txs_last_1h` (plus experimental `time_burst_indicator` optionally available).
  * **6 Network Telemetry Features**: `net_src_port`, `net_dst_port`, `net_is_standard_bitcoin_port`, `net_asn`, `net_hist_unique_ips_for_addr`, `net_country`.
  * **4 Relational Topological Features**: `rel_fan_in`, `rel_fan_out`, `rel_has_change_output`, `rel_change_value_ratio`.

---

## 3. Important Modeling & Preprocessing Notes

1. **Categorical Fields**:
   * `net_country` is an **observational categorical context field** and must not be passed directly as a numeric feature without encoding.
   * `net_asn` represents **network identity information** and requires appropriate categorical encoding (frequency, target, or embedding) before use in numeric ML models.
2. **Cyclic Temporal Features**:
   * `time_hour_of_day` and `time_day_of_week` are currently retained as raw observational features. Downstream model preprocessing should consider cyclic transformations ($\sin/\cos$) to preserve 24-hour and 7-day cyclical continuity.
3. **Retained Redundancies**:
   * `tx_input_count` vs `rel_fan_in` and `tx_output_count` vs `rel_fan_out` are intentionally retained at this stage. Multi-input transactions can spend from identical or distinct addresses; true redundancy will be evaluated empirically during model experimentation.
4. **Descriptive Tone**:
   * Features represent transaction intensity, pacing, network context, and address hygiene; they do not by themselves constitute proof of illicit activity.

---

## 4. Anti-Leakage Guarantee

All address-level and temporal features strictly adhere to the historical lookback constraint:
$$\text{Feature}(tx, T_{tx}) = f(\{e \mid t_e < T_{tx}\})$$

- **Zero Future Information**: No future transactions, future change spends, or subsequent network events are accessible.
- **Purely Observational**: Generator-only columns (`scenario_id`, `has_network_anomaly`, `ground_truth_label`) are strictly quarantined and forbidden from the feature matrix.

---

## 5. CLI Usage

Run feature extraction on canonical data:
```bash
python -m ml.feature_engineering.feature_pipeline \
  --input data/processed/canonical/ \
  --output data/processed/features/ \
  --db-path database/aquasynex.duckdb
```

Output:
- `data/processed/features/feature_matrix_v1.parquet`
- Registered DuckDB table: `features_v1`

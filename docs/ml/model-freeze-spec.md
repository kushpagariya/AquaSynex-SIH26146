# AquaSynex — Formal Model Freeze Specification (Phase 2.6)

**Document Version**: 1.0.0  
**Status**: APPROVED & FORMALLY FROZEN FOR PHASE 2.7 TEST EVALUATION  
**Date**: 2026-09-12  
**Dataset Reference**: `data/processed/modeling_v2/modeling_dataset.parquet` (Hardened Synthetic Benchmark `v2.0.0`)  
**Authoritative Benchmark**: `notebooks/08_official_colab_modeling.ipynb`  
**Configuration File**: `ml/modeling_experimentation/frozen_model_spec.yaml`

---

## 1. Frozen Model Architecture & Hyperparameters

The provisional winning binary architecture is **XGBoost** (`xgboost.XGBClassifier`), selected on the basis of superior discrimination (**0.9981 ROC-AUC**, **0.9976 PR-AUC**) and sub-millisecond inference latency on the out-of-time validation partition ($N = 1,500$).

### 1.1 Hyperparameter Specifications

| Parameter | Frozen Value | Architectural / Methodological Rationale |
|---|---|---|
| `model_class` | `xgboost.XGBClassifier` | Second-order gradient boosted decision trees |
| `n_estimators` | `300` | Convergence verified with zero over-specialization |
| `max_depth` | `6` | Sufficient capacity to capture high-order UTXO-graph interaction terms |
| `learning_rate` | `0.05` | Conservative shrinkage preventing step oscillation |
| `subsample` | `0.80` | Row subsampling per boosting iteration for stochastic regularization |
| `colsample_bytree` | `0.80` | Feature subspace sampling preventing single-feature over-reliance |
| `scale_pos_weight` | `1.320955` | Exactly balanced to class distribution: $(\text{len}(y) - \sum y) / \sum y = 3984 / 3016$ |
| `eval_metric` | `'logloss'` | Negative log-likelihood objective |
| `random_state` | `42` | Pinned random seed for exact deterministic reproducibility |
| `n_jobs` | `-1` | Parallelized thread execution across CPU cores |

> **Immutability Directive**: These hyperparameters are **strictly locked**. No further tuning, grid searching, or adjustments are permitted prior to or during Phase 2.7 test evaluation.

---

## 2. 46-Feature Manifest & Versioning

The model consumes **strictly the 46 canonical predictive features** defined in `data/processed/modeling_v2/feature_manifest.yaml` (v2.0.0).

### 2.1 Feature Breakdown by Domain

1. **Transaction-Level Tabular Features (13)**:
   - `tx_input_count`, `tx_output_count`, `tx_input_output_ratio`, `tx_total_input_sats`, `tx_total_output_sats`, `tx_fee_sats`, `tx_size_bytes`, `tx_fee_rate_sat_per_byte`, `tx_value_balance_ratio`, `tx_avg_input_value_sats`, `tx_max_input_value_sats`, `tx_avg_output_value_sats`, `tx_max_output_value_sats`, `tx_log_total_value`, `tx_log_fee`.
2. **Historical Address Behavioral Features (7)**:
   - `addr_hist_tx_count`, `addr_hist_total_sent_sats`, `addr_hist_total_received_sats`, `addr_hist_avg_tx_val_sats`, `addr_hist_unique_counterparties`, `addr_hist_active_days`, `addr_hist_tx_per_day`, `addr_reuse_count`.
3. **Temporal Activity Features (8)**:
   - `time_hour_of_day`, `time_day_of_week`, `time_since_prev_global_tx_sec`, `time_txs_last_1m`, `time_txs_last_5m`, `time_txs_last_1h`, `time_since_prev_addr_tx_sec`.
4. **Network Telemetry Features (5)**:
   - `net_src_port`, `net_dst_port`, `net_is_standard_bitcoin_port`, `net_hist_unique_ips_for_addr`, `net_country` (categorical), `net_asn` (categorical).
5. **Relational Topological Features (4)**:
   - `rel_fan_in`, `rel_fan_out`, `rel_has_change_output`, `rel_change_value_ratio`.
6. **Graph Historical Features (6)**:
   - `hist_in_mean_neighbor_degree`, `hist_out_mean_neighbor_degree`, `hist_component_size`, `hist_address_reuse_ratio`, `hist_cluster_size`, `hist_cluster_tx_count`.

### 2.2 Excluded Columns (Strict Quarantine)
The following columns are **strictly excluded** from ML model inputs:
- `transaction_id` (Unique identifier)
- `timestamp_epoch_sec` (Temporal anchor)
- `hist_cluster_id` (High-cardinality grouping/entity key)
- `graph_fan_in`, `graph_fan_out`, `graph_unique_in_addrs`, `graph_unique_out_addrs` (Exact duplicates of tabular features)
- `target_binary`, `target_multiclass` (Ground truth labels)
- `temporal_split` (Partition assignment)

---

## 3. Preprocessing Pipeline Specification

To guarantee zero data leakage across partitions, the preprocessing transformations are defined as follows:

1. **Partition Protocol**:
   - `df_train`: `temporal_split == 'train'` ($N = 7,000$, rows $0$ to $6,999$ chronologically).
   - `df_val`: `temporal_split == 'val'` ($N = 1,500$, rows $7,000$ to $8,499$ chronologically).
   - `df_test`: `temporal_split == 'test'` ($N = 1,500$, rows $8,500$ to $9,999$ chronologically).
2. **Numeric Transformation**:
   - Class: `sklearn.preprocessing.RobustScaler(with_centering=True, with_scaling=True, quantile_range=(25.0, 75.0))`
   - Applied to: 44 numeric features
   - Fit Rule: **Fit strictly on `df_train`**. `df_val` and `df_test` are transformed using the train-fitted scaler without updating median or IQR parameters.
3. **Categorical Transformation**:
   - Class: `sklearn.preprocessing.OneHotEncoder(handle_unknown='ignore', sparse_output=False)`
   - Applied to: `['net_country', 'net_asn']`
   - Fit Rule: **Fit strictly on `df_train`**. Unseen categories in validation or test partitions evaluate to all-zero vectors (`handle_unknown='ignore'`).
4. **Post-Transformation Dimensionality**:
   - Dense representation: 44 scaled numeric features + 27 categorical binary columns = **71 total features**.

---

## 4. Operating Thresholds & Deterministic Selection Rules

Decision thresholds were calibrated strictly on the validation partition ($N = 1,500$); test partition labels were not accessed during threshold calibration.

### 4.1 Frozen Threshold Table

| Operating Point | Threshold ($\tau$) | Validation Precision | Validation Recall | Validation F1 | Target Use-Case |
|---|---|---|---|---|---|
| **Default Baseline** | `0.50` | 0.9702 | 0.9763 | 0.9733 | Balanced general transaction surveillance |
| **$F_1$-Optimal** | `0.32` | 0.9632 | **0.9921** | **0.9775** | Maximum Anomaly Capture / Compliance Auditing (only 5 FN out of 634) |
| **High-Precision $R_{95}$** | `0.67` | **0.9821** | 0.9543 | 0.9680 | Low False-Alarm Escalation (only 11 FP across 866 benign transactions) |

### 4.2 Selection Rules
- **$F_1$-Optimal Rule**: $\tau^*_{F_1} = \arg\max_{\tau \in [0.01, 0.99]} F_1(\tau)$.
- **$R_{95}$ Rule**: Among all candidate thresholds $\tau$ where $\text{Recall}(\tau) \ge 0.95$, select the threshold maximizing $\text{Precision}(\tau)$. If tied, select highest $F_1(\tau)$.

---

## 5. Multiclass Configuration (11 Scenarios)

The secondary multi-class scenario attribution model is frozen with the following specification:
- **Model**: `catboost.CatBoostClassifier`
- **Target**: `target_multiclass`
- **Classes (11)**: `amount_anomaly`, `benign_high_volume`, `coordinated_activity`, `high_fan_in`, `high_fan_out`, `mixing_like`, `normal`, `peeling_chain`, `rapid_multihop`, `temporal_anomaly`, `transaction_burst`.
- **Hyperparameters**: `iterations=350, depth=6, learning_rate=0.06, loss_function='MultiClass', eval_metric='MultiClass', random_seed=42, verbose=0`.
- **Validation Metrics**: Top-1 Accuracy = **96.60%**, Macro F1 = **0.9566**, Log-Loss = **0.1002**.

---

## 6. SHAP / Explainability Configuration

- **Method**: Exact Tree SHAP via XGBoost native `pred_contribs=True` (and `shap.TreeExplainer` interface).
- **Target**: Frozen binary XGBoost model.
- **Reference**: Expected log-odds margin value (bias term).
- **Verified Drivers**: Top-5 features on validation:
  1. `hist_out_mean_neighbor_degree` (Graph recipient connectivity)
  2. `time_since_prev_global_tx_sec` (Inter-arrival timing cadence)
  3. `time_day_of_week` (Weekly behavioral pattern)
  4. `time_txs_last_1m` (Short-window burst velocity)
  5. `rel_change_value_ratio` (Change output fraction)

---

## 7. Phase 2.7 Test Unblinding Protocol & Constraints

> [!WARNING]
> **One-Shot Evaluation Rule**:
> - The held-out test partition ($N = 1,500$) must be unblinded **exactly ONCE** in Phase 2.7.
> - No iterative parameter tuning, feature selection, threshold re-calibration, or re-training will be performed after observing test set results.
> - The final model evaluation on test will be reported side-by-side with validation metrics to assess temporal degradation and out-of-distribution stability.
> - Once evaluated, the model and preprocessing pipeline will be serialized to `models/production_model_v1.bin` (or `.json`) and signed off.

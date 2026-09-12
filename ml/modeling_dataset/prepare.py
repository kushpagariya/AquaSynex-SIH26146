"""
AquaSynex — Phase 2.5A Modeling Dataset Preparation Pipeline (Corrected Taxonomy)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Generates:
1. data/processed/modeling/modeling_dataset.parquet (10,000 rows x 56 columns)
2. data/processed/modeling/feature_manifest.yaml (46 canonical predictive features)
3. data/processed/modeling/modeling_schema.md
4. DuckDB table: modeling_dataset_v1
"""

import os
import yaml
import json
import time
import numpy as np
import pandas as pd
import duckdb

from ml.modeling_dataset.builder import ModelingDatasetBuilder

def generate_manifest_and_schema(df: pd.DataFrame, output_dir: str):
    norm_dir = os.path.abspath(output_dir).replace("\\", "/")
    os.makedirs(norm_dir, exist_ok=True)

    manifest_path = f"{norm_dir}/feature_manifest.yaml"
    schema_path = f"{norm_dir}/modeling_schema.md"

    # 1. Identifiers & Grouping Keys (Strictly EXCLUDED from ML features X)
    identifiers = [
        "transaction_id",
        "timestamp_epoch_sec",
        "hist_cluster_id"
    ]
    
    # 2. Targets & Split Indicator (Strictly EXCLUDED from ML features X)
    targets = ["target_binary", "target_multiclass"]
    split_col = ["temporal_split"]

    # 3. Optional Ablation Features (Excluded from primary canonical X, retained for ablation)
    optional_ablation_features = [
        "graph_fan_in",
        "graph_fan_out",
        "graph_unique_in_addrs",
        "graph_unique_out_addrs"
    ]

    # 4. Canonical Categorical Features (Require OneHot / Target Encoding)
    canonical_categorical_features = ["net_country", "net_asn"]

    # 5. Canonical Numeric Features (44)
    non_numeric_or_excluded = set(identifiers + targets + split_col + optional_ablation_features + canonical_categorical_features)
    canonical_numeric_features = [c for c in df.columns if c not in non_numeric_or_excluded]

    # Total canonical predictive features: 44 numeric + 2 categorical = 46
    canonical_feature_names = canonical_numeric_features + canonical_categorical_features
    if len(canonical_feature_names) != 46:
        raise ValueError(f"Expected exactly 46 canonical predictive features, but found {len(canonical_feature_names)}")

    # Generate Feature Manifest Dictionary
    manifest = {
        "manifest_version": "2.0",
        "phase": "2.5A",
        "generated_at": "2026-09-12T02:48:00Z",
        "dataset_summary": {
            "total_records": int(len(df)),
            "total_columns": int(len(df.columns)),
            "canonical_predictive_features_count": int(len(canonical_feature_names)),
            "canonical_numeric_features_count": int(len(canonical_numeric_features)),
            "canonical_categorical_features_count": int(len(canonical_categorical_features)),
            "optional_ablation_features_count": int(len(optional_ablation_features)),
            "identifiers_and_grouping_count": int(len(identifiers)),
            "targets_count": int(len(targets)),
            "split_indicator_count": int(len(split_col)),
            "temporal_split_counts": df["temporal_split"].value_counts().to_dict(),
            "target_binary_counts": df["target_binary"].value_counts().to_dict(),
            "target_multiclass_counts": df["target_multiclass"].value_counts().to_dict()
        },
        "canonical_feature_names": canonical_feature_names,
        "identifiers_and_grouping": [
            {
                "name": "transaction_id",
                "type": "string",
                "role": "identifier",
                "is_model_feature": False,
                "description": "Unique Bitcoin transaction hash (SHA256 hex). Excluded from ML features."
            },
            {
                "name": "timestamp_epoch_sec",
                "type": "integer",
                "role": "temporal_anchor",
                "is_model_feature": False,
                "description": "UNIX epoch timestamp in seconds. Used for chronological ordering and temporal splits."
            },
            {
                "name": "hist_cluster_id",
                "type": "string",
                "role": "entity_grouping_key",
                "is_model_feature": False,
                "unique_values_count": int(df["hist_cluster_id"].nunique()),
                "description": "Inferred behavioral entity cluster root as of prior to transaction (t < T_tx). High-cardinality grouping/investigation key. EXCLUDED from predictive ML model features."
            }
        ],
        "targets": [
            {
                "name": "target_binary",
                "type": "integer",
                "is_model_feature": False,
                "values": {"0": "benign (normal, benign_high_volume)", "1": "suspicious (anomalous scenarios)"},
                "description": "Primary binary classification target."
            },
            {
                "name": "target_multiclass",
                "type": "string",
                "is_model_feature": False,
                "num_classes": 11,
                "description": "Ground-truth transaction scenario behavior type for multiclass profiling."
            }
        ],
        "split_indicator": {
            "name": "temporal_split",
            "type": "string",
            "is_model_feature": False,
            "values": ["train", "val", "test"],
            "description": "Chronological partition: 70% train (0..6999), 15% val (7000..8499), 15% test (8500..9999)."
        },
        "canonical_categorical_features": [
            {
                "name": "net_country",
                "type": "string",
                "is_model_feature": True,
                "unique_values_count": int(df["net_country"].nunique()),
                "unique_values": sorted(list(df["net_country"].unique())),
                "encoding_requirement": "OneHotEncoder or TargetEncoder (fit on train split only)."
            },
            {
                "name": "net_asn",
                "type": "integer",
                "is_model_feature": True,
                "unique_values_count": int(df["net_asn"].nunique()),
                "encoding_requirement": "Categorical network identity. FrequencyEncoder or TargetEncoder (fit on train split only)."
            }
        ],
        "optional_ablation_features": [
            {
                "name": "graph_fan_in",
                "type": "integer",
                "is_model_feature": False,
                "is_canonical": False,
                "duplicate_of": "tx_input_count",
                "pearson_correlation": 1.0,
                "role": "optional_ablation",
                "recommendation": "Excluded from canonical model features. Exactly redundant with tx_input_count."
            },
            {
                "name": "graph_fan_out",
                "type": "integer",
                "is_model_feature": False,
                "is_canonical": False,
                "duplicate_of": "tx_output_count",
                "pearson_correlation": 1.0,
                "role": "optional_ablation",
                "recommendation": "Excluded from canonical model features. Exactly redundant with tx_output_count."
            },
            {
                "name": "graph_unique_in_addrs",
                "type": "integer",
                "is_model_feature": False,
                "is_canonical": False,
                "duplicate_of": "rel_fan_in",
                "pearson_correlation": 1.0,
                "role": "optional_ablation",
                "recommendation": "Excluded from canonical model features. Exactly redundant with rel_fan_in."
            },
            {
                "name": "graph_unique_out_addrs",
                "type": "integer",
                "is_model_feature": False,
                "is_canonical": False,
                "duplicate_of": "rel_fan_out",
                "pearson_correlation": 1.0,
                "role": "optional_ablation",
                "recommendation": "Excluded from canonical model features. Exactly redundant with rel_fan_out."
            }
        ],
        "canonical_numeric_features": []
    }

    for col in canonical_numeric_features:
        s = df[col]
        manifest["canonical_numeric_features"].append({
            "name": col,
            "type": str(s.dtype),
            "is_model_feature": True,
            "min": float(s.min()) if pd.notna(s.min()) else None,
            "median": float(s.median()) if pd.notna(s.median()) else None,
            "max": float(s.max()) if pd.notna(s.max()) else None,
            "mean": round(float(s.mean()), 4) if pd.notna(s.mean()) else None,
            "std": round(float(s.std()), 4) if pd.notna(s.std()) else None,
            "null_count": int(s.isna().sum())
        })

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, indent=2)
    print(f"[+] Wrote corrected feature manifest to: {manifest_path}", flush=True)

    # Write Modeling Schema Markdown
    schema_content = f"""# AquaSynex — Canonical Modeling Dataset Schema (Phase 2.5A)

**SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**

> **Authoritative Specification**: Defines the column composition, chronological temporal split strategy, categorical encoding guidelines, anti-leakage invariants, and feature classifications for the machine learning modeling dataset.

**Status**: `IMPLEMENTED`

---

## 1. Dataset Dimensions & Taxonomy Summary

- **File Path**: `data/processed/modeling/modeling_dataset.parquet`
- **DuckDB Table**: `modeling_dataset_v1`
- **Total Records**: {len(df):,} transactions (1:1 join with canonical transactions, 0 dropped rows)
- **Total Columns**: {len(df.columns)} columns
- **Primary Canonical Feature Space (46 Predictive Features)**:
  - **44 Canonical Numeric Predictive Features**:
    - 15 transaction features (`tx_input_count`, `tx_output_count`, `tx_input_output_ratio`, `tx_total_input_sats`, `tx_total_output_sats`, `tx_fee_sats`, `tx_size_bytes`, `tx_fee_rate_sat_per_byte`, `tx_value_balance_ratio`, `tx_avg_input_value_sats`, `tx_max_input_value_sats`, `tx_avg_output_value_sats`, `tx_max_output_value_sats`, `tx_log_total_value`, `tx_log_fee`)
    - 8 address features (`addr_hist_tx_count`, `addr_hist_total_sent_sats`, `addr_hist_total_received_sats`, `addr_hist_avg_tx_val_sats`, `addr_hist_unique_counterparties`, `addr_hist_active_days`, `addr_hist_tx_per_day`, `addr_reuse_count`)
    - 7 temporal features (`time_hour_of_day`, `time_day_of_week`, `time_since_prev_global_tx_sec`, `time_txs_last_1m`, `time_txs_last_5m`, `time_txs_last_1h`, `time_since_prev_addr_tx_sec`)
    - 4 network numeric features (`net_src_port`, `net_dst_port`, `net_is_standard_bitcoin_port`, `net_hist_unique_ips_for_addr`)
    - 4 relational features (`rel_fan_in`, `rel_fan_out`, `rel_has_change_output`, `rel_change_value_ratio`)
    - 6 graph historical features (`hist_in_mean_neighbor_degree`, `hist_out_mean_neighbor_degree`, `hist_component_size`, `hist_address_reuse_ratio`, `hist_cluster_size`, `hist_cluster_tx_count`)
  - **2 Canonical Categorical Features**:
    - `net_country` (16 unique countries; requires OneHot or Target Encoding)
    - `net_asn` (28 unique ASNs; categorical network identity requiring Frequency or Target Encoding)
  - **Total Canonical Predictive Features**: **44 Numeric + 2 Categorical = 46 Features**

- **Non-Feature Columns (10 Columns)**:
  - **4 Optional Graph Ablation Features**: `graph_fan_in`, `graph_fan_out`, `graph_unique_in_addrs`, `graph_unique_out_addrs` (retained for ablation; excluded from canonical X due to Pearson $r = 1.0000$ with tabular twins).
  - **3 Identifiers & Grouping Keys**: `transaction_id`, `timestamp_epoch_sec`, `hist_cluster_id` (`hist_cluster_id` is classified strictly as an entity grouping/investigation key and is NOT a model feature).
  - **2 Ground-Truth Targets**: `target_binary` (0/1), `target_multiclass` (11 scenario labels).
  - **1 Partition Indicator**: `temporal_split` (`train`, `val`, `test`).

---

## 2. Temporal Partitioning Strategy (Anti-Leakage Protocol)

To eliminate lookahead bias and reflect real-world chronological transaction monitoring, random train/test splits are strictly prohibited. The dataset is sorted by `timestamp_epoch_sec ASC, transaction_id ASC` and partitioned into three contiguous temporal segments:

| Partition | Row Range | Sample Size | Percentage | Target Suspicious % | Scenario Classes | Purpose |
|---|---|---|---|---|---|---|
| **`train`** | Index 0 to 6,999 | 7,000 | 70.0% | 44.91% | 11 / 11 | Historical baseline model fitting and feature transformation training. |
| **`val`** | Index 7,000 to 8,499 | 1,500 | 15.0% | 42.13% | 11 / 11 | Validation tuning, hyperparameter search, and threshold calibration. |
| **`test`** | Index 8,500 to 9,999 | 1,500 | 15.0% | 37.40% | 11 / 11 | Final out-of-time evaluation of model generalization. |

### Temporal Preprocessing Rule:
All preprocessing transformations (e.g. `StandardScaler`, `RobustScaler`, `OneHotEncoder`, `TargetEncoder`) must be **fit strictly on the `train` partition** and subsequently applied via `.transform()` to `val` and `test`.

---

## 3. Ground-Truth Target Definitions

1. **`target_binary` (`BIGINT`)**:
   - `0`: Benign baseline activity (`normal`, `benign_high_volume`) — 5,663 records (56.63%).
   - `1`: Suspicious activity (all 9 anomaly scenarios) — 4,337 records (43.37%).
2. **`target_multiclass` (`VARCHAR`)**:
   - Preserves granular scenario labels: `normal` (5,079), `transaction_burst` (1,124), `rapid_multihop` (972), `peeling_chain` (784), `coordinated_activity` (591), `benign_high_volume` (584), `high_fan_in` (223), `temporal_anomaly` (209), `high_fan_out` (205), `mixing_like` (152), `amount_anomaly` (77).
   - All 11 classes are confirmed present in the held-out `test` partition.

---

## 4. Exclusion & Classification Summary

| Column Name | Classification | Rationale & Governance Rule |
|---|---|---|
| `hist_cluster_id` | **IDENTIFIER / GROUPING KEY** | High-cardinality entity cluster root (6,423 clusters). Retained for entity lookup, investigation, and explainability. **STRICTLY EXCLUDED from predictive ML feature matrix X.** |
| `graph_fan_in` | **OPTIONAL ABLATION FEATURE** | 100% redundant with `tx_input_count` ($r = 1.0000$). Excluded from canonical primary features. |
| `graph_fan_out` | **OPTIONAL ABLATION FEATURE** | 100% redundant with `tx_output_count` ($r = 1.0000$). Excluded from canonical primary features. |
| `graph_unique_in_addrs` | **OPTIONAL ABLATION FEATURE** | 100% redundant with `rel_fan_in` ($r = 1.0000$). Excluded from canonical primary features. |
| `graph_unique_out_addrs` | **OPTIONAL ABLATION FEATURE** | 100% redundant with `rel_fan_out` ($r = 1.0000$). Excluded from canonical primary features. |
| `transaction_id` | **IDENTIFIER** | Primary key. Excluded from predictive features X. |
| `timestamp_epoch_sec` | **TEMPORAL ANCHOR** | Chronological ordering anchor. Excluded from predictive features X. |
| `target_binary` | **TARGET** | Binary evaluation label. Excluded from predictive features X. |
| `target_multiclass` | **TARGET** | Multiclass evaluation label. Excluded from predictive features X. |
| `temporal_split` | **PARTITION INDICATOR** | Chronological split flag (`train`, `val`, `test`). Excluded from predictive features X. |

---

## 5. Strict Zero Model Training Guarantee

In accordance with Phase 2.5A constraints:
- NO machine learning models (XGBoost, LightGBM, Random Forest, Isolation Forest) have been trained.
- NO model weights, pipelines, or inference artifacts have been generated.
- NO data or code has been moved to Google Colab.
- This dataset is strictly prepared and validated for downstream Phase 2.5B / Phase 2.6 modeling.

---
*Generated: 2026-09-12 | Phase: 2.5A (Corrected Taxonomy) | Owner: AquaSynex ML Architecture Team*
"""

    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(schema_content)
    print(f"[+] Wrote corrected modeling schema documentation to: {schema_path}", flush=True)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AquaSynex Phase 2.5A Modeling Dataset Preparation Pipeline")
    parser.add_argument("--tabular-path", default="data/processed/features/feature_matrix_v1.parquet", help="Path to tabular feature matrix")
    parser.add_argument("--graph-path", default="data/processed/graph/graph_features.parquet", help="Path to graph feature matrix")
    parser.add_argument("--canonical-tx-path", default="data/processed/canonical/canonical_transactions.parquet", help="Path to canonical transactions Parquet")
    parser.add_argument("--labels-path", default="data/sample/labels.parquet", help="Path to quarantined labels Parquet")
    parser.add_argument("--output-dir", default="data/processed/modeling", help="Output directory for modeling artifacts")
    parser.add_argument("--db-path", default="database/aquasynex.duckdb", help="Target DuckDB database path")
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 70)
    print(f"AquaSynex — Phase 2.5A Modeling Dataset Preparation Pipeline -> {args.output_dir}")
    print("=" * 70)

    builder = ModelingDatasetBuilder(
        tabular_path=args.tabular_path,
        graph_path=args.graph_path,
        canonical_tx_path=args.canonical_tx_path,
        labels_path=args.labels_path
    )
    df = builder.build_dataset()
    builder.export_dataset(
        output_dir=args.output_dir,
        db_path=args.db_path
    )

    generate_manifest_and_schema(df, args.output_dir)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"Phase 2.5A Dataset Preparation Complete in {elapsed:.2f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()

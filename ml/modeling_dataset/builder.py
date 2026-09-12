"""
AquaSynex — Modeling Dataset Preparation Builder (Phase 2.5A)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Responsibilities:
1. Join tabular feature matrix (Phase 2.3) and graph feature matrix (Phase 2.4) on transaction_id.
2. Integrate canonical transaction timestamps for strict chronological ordering.
3. Attach ground-truth evaluation targets (binary target_binary and multiclass target_multiclass).
4. Enforce strict quarantine: zero generator metadata (scenario_id, has_network_anomaly, risk_seed, related_entities).
5. Annotate chronological temporal splits (70% train, 15% val, 15% test).
6. Export canonical modeling dataset to Parquet and register in DuckDB.
"""

import os
import argparse
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import duckdb

class ModelingDatasetBuilder:
    def __init__(
        self,
        tabular_path: str = "data/processed/features/feature_matrix_v1.parquet",
        graph_path: str = "data/processed/graph/graph_features.parquet",
        canonical_tx_path: str = "data/processed/canonical/canonical_transactions.parquet",
        labels_path: str = "data/sample/labels.parquet"
    ):
        self.tabular_path = os.path.abspath(tabular_path).replace("\\", "/")
        self.graph_path = os.path.abspath(graph_path).replace("\\", "/")
        self.canonical_tx_path = os.path.abspath(canonical_tx_path).replace("\\", "/")
        self.labels_path = os.path.abspath(labels_path).replace("\\", "/")
        self.df_modeling: pd.DataFrame = pd.DataFrame()

    def build_dataset(self) -> pd.DataFrame:
        """
        Execute the 1:1 chronological join and audit validation.
        """
        print("[*] Loading and joining feature matrices...", flush=True)
        con = duckdb.connect()

        # Verify source files exist
        for p in [self.tabular_path, self.graph_path, self.canonical_tx_path, self.labels_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Required dataset input not found: {p}")

        query = f"""
        SELECT 
            -- Identifiers & Temporal Anchor
            t.transaction_id,
            c.timestamp_epoch_sec,
            
            -- Targets (quarantined from features, preserved for supervised evaluation)
            CAST(l.ground_truth_label AS BIGINT) AS target_binary,
            CAST(l.behavior_type AS VARCHAR) AS target_multiclass,
            
            -- Tabular Transaction Features (15)
            t.tx_input_count,
            t.tx_output_count,
            t.tx_input_output_ratio,
            t.tx_total_input_sats,
            t.tx_total_output_sats,
            t.tx_fee_sats,
            t.tx_size_bytes,
            t.tx_fee_rate_sat_per_byte,
            t.tx_value_balance_ratio,
            t.tx_avg_input_value_sats,
            t.tx_max_input_value_sats,
            t.tx_avg_output_value_sats,
            t.tx_max_output_value_sats,
            t.tx_log_total_value,
            t.tx_log_fee,
            
            -- Tabular Address Features (8)
            t.addr_hist_tx_count,
            t.addr_hist_total_sent_sats,
            t.addr_hist_total_received_sats,
            t.addr_hist_avg_tx_val_sats,
            t.addr_hist_unique_counterparties,
            t.addr_hist_active_days,
            t.addr_hist_tx_per_day,
            t.addr_reuse_count,
            
            -- Tabular Temporal Features (7)
            t.time_hour_of_day,
            t.time_day_of_week,
            t.time_since_prev_global_tx_sec,
            t.time_txs_last_1m,
            t.time_txs_last_5m,
            t.time_txs_last_1h,
            t.time_since_prev_addr_tx_sec,
            
            -- Tabular Network Features (6)
            t.net_src_port,
            t.net_dst_port,
            t.net_is_standard_bitcoin_port,
            t.net_asn,
            t.net_hist_unique_ips_for_addr,
            t.net_country,
            
            -- Tabular Relational Features (4)
            t.rel_fan_in,
            t.rel_fan_out,
            t.rel_has_change_output,
            t.rel_change_value_ratio,
            
            -- Graph Features (11)
            g.graph_fan_in,
            g.graph_fan_out,
            g.graph_unique_in_addrs,
            g.graph_unique_out_addrs,
            g.hist_in_mean_neighbor_degree,
            g.hist_out_mean_neighbor_degree,
            g.hist_component_size,
            g.hist_address_reuse_ratio,
            g.hist_cluster_id,
            g.hist_cluster_size,
            g.hist_cluster_tx_count
        FROM read_parquet('{self.tabular_path}') t
        JOIN read_parquet('{self.graph_path}') g ON t.transaction_id = g.transaction_id
        JOIN read_parquet('{self.canonical_tx_path}') c ON t.transaction_id = c.transaction_id
        JOIN read_parquet('{self.labels_path}') l ON t.transaction_id = l.txid
        ORDER BY c.timestamp_epoch_sec ASC, t.transaction_id ASC
        """

        tab_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.tabular_path}')").fetchone()[0]
        graph_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.graph_path}')").fetchone()[0]
        can_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.canonical_tx_path}')").fetchone()[0]
        lbl_cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.labels_path}')").fetchone()[0]

        df = con.execute(query).df()
        con.close()

        total_rows = len(df)
        if not (total_rows == tab_cnt == graph_cnt == can_cnt == lbl_cnt) or total_rows == 0:
            raise ValueError(
                f"Inner join dropped rows or input counts mismatch: tabular={tab_cnt}, graph={graph_cnt}, "
                f"canonical={can_cnt}, labels={lbl_cnt}, joined={total_rows}"
            )

        # Assert no duplicate transaction_ids
        if df["transaction_id"].duplicated().any():
            raise ValueError("Duplicate transaction_id detected in combined modeling dataset.")

        # Assign chronological temporal split indicator
        # 70% Train (0..6999), 15% Validation (7000..8499), 15% Test (8500..9999)
        split_labels = []
        for i in range(total_rows):
            if i < int(total_rows * 0.70):
                split_labels.append("train")
            elif i < int(total_rows * 0.85):
                split_labels.append("val")
            else:
                split_labels.append("test")

        df["temporal_split"] = split_labels
        self.df_modeling = df

        print(f"[+] Modeling dataset constructed: {df.shape[0]:,} rows x {df.shape[1]} columns.", flush=True)
        print(f"    - Temporal splits: {df['temporal_split'].value_counts().to_dict()}", flush=True)
        return self.df_modeling

    def export_dataset(
        self,
        output_dir: str = "data/processed/modeling",
        db_path: str = "database/aquasynex.duckdb"
    ):
        """
        Export modeling dataset to Parquet and register in DuckDB.
        """
        norm_dir = os.path.abspath(output_dir).replace("\\", "/")
        os.makedirs(norm_dir, exist_ok=True)
        out_parquet = f"{norm_dir}/modeling_dataset.parquet"

        con = duckdb.connect()
        con.register("model_view", self.df_modeling)
        con.execute(f"COPY model_view TO '{out_parquet}' (FORMAT PARQUET)")
        con.unregister("model_view")
        con.close()
        print(f"[+] Exported modeling dataset to: {out_parquet}", flush=True)

        if db_path and os.path.exists(os.path.dirname(os.path.abspath(db_path))):
            norm_db = os.path.abspath(db_path).replace("\\", "/")
            con_db = duckdb.connect(norm_db)
            con_db.execute(f"CREATE OR REPLACE TABLE modeling_dataset_v1 AS SELECT * FROM read_parquet('{out_parquet}')")
            row_cnt = con_db.execute("SELECT COUNT(*) FROM modeling_dataset_v1").fetchone()[0]
            con_db.close()
            print(f"[+] Registered modeling_dataset_v1 in DuckDB: {row_cnt:,} rows.", flush=True)

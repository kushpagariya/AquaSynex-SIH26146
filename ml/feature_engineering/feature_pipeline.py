"""
AquaSynex — Feature Engineering Pipeline (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Orchestrates the extraction, validation, and export of the canonical v1 feature matrix.
Integrates:
- 15 Transaction-level features
- 8 Address/entity behavioral features (strict historical lookback t < T_tx)
- 7 Temporal cadence features (rolling windows)
- 6 Network telemetry features (5 numerical + 1 categorical context)
- 4 Relational topological features
Total: 40 features + 1 transaction_id key = 41 total feature-matrix columns.
"""

import os
import time
import argparse
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
import duckdb

from ml.feature_engineering.transaction_features import TransactionFeatureExtractor
from ml.feature_engineering.address_features import AddressFeatureExtractor
from ml.feature_engineering.temporal_features import TemporalFeatureExtractor
from ml.feature_engineering.network_features import NetworkFeatureExtractor

FORBIDDEN_LEAKAGE_COLUMNS = {
    "scenario_id",
    "has_network_anomaly",
    "behavior_type",
    "ground_truth_label",
    "risk_seed",
    "related_entities"
}

class FeatureEngineeringPipeline:
    def __init__(self, version: str = "v1.0.0"):
        self.version = version
        self.tx_extractor = TransactionFeatureExtractor()
        self.addr_extractor = AddressFeatureExtractor()
        self.temp_extractor = TemporalFeatureExtractor()
        self.net_extractor = NetworkFeatureExtractor()

    def build_feature_matrix(
        self, 
        canonical_data: Dict[str, pd.DataFrame],
        include_experimental: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Extract all feature groups and merge into a unified feature matrix.
        Performs automated quality checks (NaNs, Infs, Leakage, Variance).
        """
        start_time = time.time()
        print("[*] Starting Feature Engineering Pipeline (version: {})...".format(self.version), flush=True)

        # 1. Extract feature groups
        print("  [1/5] Extracting transaction-level features...", flush=True)
        f_tx = self.tx_extractor.extract(canonical_data)

        print("  [2/5] Extracting historical address behavioral features (t < T_tx)...", flush=True)
        f_addr = self.addr_extractor.extract(canonical_data)

        print("  [3/5] Extracting temporal activity features...", flush=True)
        f_temp = self.temp_extractor.extract(canonical_data, include_experimental=include_experimental)

        print("  [4/5] Extracting network telemetry features...", flush=True)
        f_net = self.net_extractor.extract(canonical_data)

        print("  [5/5] Extracting relational topological features...", flush=True)
        f_rel = self._extract_relational_features(canonical_data)

        # 2. Merge all features on transaction_id
        matrix = f_tx.merge(f_addr, on="transaction_id", how="left")
        matrix = matrix.merge(f_temp, on="transaction_id", how="left")
        matrix = matrix.merge(f_net, on="transaction_id", how="left")
        matrix = matrix.merge(f_rel, on="transaction_id", how="left")

        # 3. Quality and Integrity Checks
        quality_report = self._audit_feature_quality(matrix)

        elapsed = time.time() - start_time
        print(f"[+] Feature matrix assembled in {elapsed:.2f}s: {matrix.shape[0]:,} rows, {matrix.shape[1]} columns.", flush=True)
        return matrix, quality_report

    def _extract_relational_features(self, canonical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract graph-independent relational features (fan-in, fan-out, change ratio).
        """
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())
        df_out = canonical_data.get("transaction_outputs", pd.DataFrame())

        in_addr_col = "input_address" if "input_address" in df_in.columns else "address"
        out_addr_col = "output_address" if "output_address" in df_out.columns else "address"
        out_val_col = "output_value_satoshi" if "output_value_satoshi" in df_out.columns else "amount_satoshi"

        fan_in = df_in.groupby("transaction_id")[in_addr_col].nunique().reset_index()
        fan_in.rename(columns={in_addr_col: "rel_fan_in"}, inplace=True)

        fan_out = df_out.groupby("transaction_id")[out_addr_col].nunique().reset_index()
        fan_out.rename(columns={out_addr_col: "rel_fan_out"}, inplace=True)

        # Change output identification
        if "is_change" in df_out.columns:
            change_df = df_out[df_out["is_change"] == True].groupby("transaction_id")[out_val_col].sum().reset_index()
            change_df.rename(columns={out_val_col: "change_sats"}, inplace=True)
        else:
            change_df = pd.DataFrame(columns=["transaction_id", "change_sats"])

        rel = pd.DataFrame({"transaction_id": df_tx["transaction_id"].copy()})
        rel = rel.merge(fan_in, on="transaction_id", how="left")
        rel = rel.merge(fan_out, on="transaction_id", how="left")
        rel = rel.merge(change_df, on="transaction_id", how="left")

        rel["rel_fan_in"] = rel["rel_fan_in"].fillna(1).astype(int)
        rel["rel_fan_out"] = rel["rel_fan_out"].fillna(1).astype(int)
        rel["rel_has_change_output"] = rel["change_sats"].notna().astype(int)
        
        tot_out = df_tx.set_index("transaction_id")["total_output_value_satoshi"].reindex(rel["transaction_id"]).values
        chg_sats = rel["change_sats"].fillna(0).values
        rel["rel_change_value_ratio"] = np.clip(chg_sats / np.maximum(tot_out, 1), 0.0, 1.0).astype(float)
        rel.drop(columns=["change_sats"], inplace=True)

        return rel

    def _audit_feature_quality(self, matrix: pd.DataFrame) -> Dict[str, Any]:
        """
        Verify that feature matrix contains no NaNs, infinite values, or leakage columns.
        """
        report = {
            "nan_counts": {},
            "inf_counts": {},
            "constant_columns": [],
            "leakage_columns_found": [],
            "is_clean": True
        }

        # Check for leakage columns
        leakage = [c for c in matrix.columns if c in FORBIDDEN_LEAKAGE_COLUMNS]
        if leakage:
            report["leakage_columns_found"] = leakage
            report["is_clean"] = False
            raise ValueError(f"CRITICAL LEAKAGE DETECTED: Forbidden columns in feature matrix: {leakage}")

        # Check for NaNs and Infs in numerical columns
        num_cols = matrix.select_dtypes(include=[np.number]).columns
        for c in num_cols:
            n_nan = int(matrix[c].isna().sum())
            if n_nan > 0:
                report["nan_counts"][c] = n_nan
                report["is_clean"] = False
            n_inf = int(np.isinf(matrix[c]).sum())
            if n_inf > 0:
                report["inf_counts"][c] = n_inf
                report["is_clean"] = False
            if matrix[c].std() < 1e-8:
                report["constant_columns"].append(c)

        return report

    def export_feature_matrix(
        self, 
        matrix: pd.DataFrame, 
        output_dir: str, 
        filename: str = "feature_matrix_v1.parquet"
    ):
        """
        Save feature matrix to Parquet format via DuckDB zero-copy export.
        """
        norm_output_dir = os.path.abspath(output_dir).replace("\\", "/")
        os.makedirs(norm_output_dir, exist_ok=True)
        parquet_path = f"{norm_output_dir}/{filename}"

        con = duckdb.connect()
        con.register("feature_view", matrix)
        con.execute(f"COPY feature_view TO '{parquet_path}' (FORMAT PARQUET)")
        con.unregister("feature_view")
        con.close()
        print(f"[+] Successfully exported feature matrix to: {parquet_path}", flush=True)

    def register_in_duckdb(
        self, 
        matrix: pd.DataFrame, 
        db_path: str, 
        table_name: str = "features_v1"
    ):
        """
        Register feature matrix in DuckDB database.
        """
        norm_db = os.path.abspath(db_path).replace("\\", "/")
        con = duckdb.connect(norm_db)
        con.register("feature_view", matrix)
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM feature_view")
        con.unregister("feature_view")
        con.close()
        print(f"[+] Successfully registered feature table '{table_name}' in DuckDB: {norm_db}", flush=True)

def run_feature_pipeline(
    canonical_dir: str = "data/processed/canonical/",
    output_dir: str = "data/processed/features/",
    db_path: str = "database/aquasynex.duckdb"
) -> pd.DataFrame:
    norm_dir = os.path.abspath(canonical_dir).replace("\\", "/")
    con = duckdb.connect()
    
    canonical_data = {
        "transactions": con.execute(f"SELECT * FROM '{norm_dir}/canonical_transactions.parquet'").fetchdf(),
        "transaction_inputs": con.execute(f"SELECT * FROM '{norm_dir}/canonical_transaction_inputs.parquet'").fetchdf(),
        "transaction_outputs": con.execute(f"SELECT * FROM '{norm_dir}/canonical_transaction_outputs.parquet'").fetchdf(),
        "network_events": con.execute(f"SELECT * FROM '{norm_dir}/canonical_network_events.parquet'").fetchdf()
    }
    con.close()

    pipeline = FeatureEngineeringPipeline(version="v1.0.0")
    matrix, report = pipeline.build_feature_matrix(canonical_data)

    if not report.get("is_clean", True):
        raise ValueError(
            f"Feature matrix failed quality auditing: {report.get('issues', [])}. "
            f"Nulls: {report.get('null_counts', {})}, Infs: {report.get('inf_counts', {})}"
        )

    pipeline.export_feature_matrix(matrix, output_dir)
    pipeline.register_in_duckdb(matrix, db_path)

    return matrix

def main():
    parser = argparse.ArgumentParser(description="AquaSynex Phase 2.3 Feature Engineering Pipeline")
    parser.add_argument("--input", type=str, default="data/processed/canonical/", help="Canonical data directory")
    parser.add_argument("--output", type=str, default="data/processed/features/", help="Feature matrix output directory")
    parser.add_argument("--db-path", type=str, default="database/aquasynex.duckdb", help="Target DuckDB database path")
    args = parser.parse_args()

    run_feature_pipeline(
        canonical_dir=args.input,
        output_dir=args.output,
        db_path=args.db_path
    )

if __name__ == "__main__":
    main()

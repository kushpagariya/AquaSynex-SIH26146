"""
AquaSynex — Data Ingestion Module (Phase 2.2)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Responsibilities:
- Ingest raw and synthetic Bitcoin transaction records from Parquet files or DuckDB.
- Enforce strict quarantine: separate observational transaction/network data
  from ground-truth labels and generator-only metadata (e.g., scenario_id, has_network_anomaly).
- Guarantee raw data preservation: read-only access with zero writes to source folders.
- Cross-platform path compatibility (Windows / Linux).
"""

import os
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import duckdb

# Columns designated strictly as ground-truth / generator metadata (FORBIDDEN in observational ML data)
GENERATOR_METADATA_COLUMNS = {
    "scenario_id",
    "has_network_anomaly",
    "behavior_type",
    "ground_truth_label",
    "risk_seed",
    "related_entities"
}

class DataIngestionEngine:
    def __init__(self, dataset_id: str = "synthetic_v1"):
        self.dataset_id = dataset_id

    def load_from_parquet_dir(
        self, 
        data_dir: str
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Load datasets from a directory containing Parquet files.
        Returns:
            observational_data: Dict of DataFrames (transactions, inputs, outputs, network_events)
            quarantined_metadata: Dict of DataFrames (labels, generator tracking metadata)
        """
        normalized_dir = os.path.abspath(data_dir).replace("\\", "/")
        if not os.path.exists(normalized_dir):
            raise FileNotFoundError(f"Source dataset directory does not exist: {normalized_dir}")

        con = duckdb.connect()
        tables_to_read = [
            ("transactions", "transactions.parquet"),
            ("transaction_inputs", "transaction_inputs.parquet"),
            ("transaction_outputs", "transaction_outputs.parquet"),
            ("network_events", "network_events.parquet"),
            ("labels", "labels.parquet")
        ]

        raw_dfs = {}
        for table_name, file_name in tables_to_read:
            file_path = os.path.join(normalized_dir, file_name).replace("\\", "/")
            if os.path.exists(file_path):
                raw_dfs[table_name] = con.execute(f"SELECT * FROM '{file_path}'").fetchdf()
            else:
                raw_dfs[table_name] = pd.DataFrame()
        con.close()

        # Check for alternative consolidated format (sih_transactions.parquet) if tables missing
        if raw_dfs["transactions"].empty:
            sih_path = os.path.join(normalized_dir, "sih_transactions.parquet").replace("\\", "/")
            if os.path.exists(sih_path):
                con = duckdb.connect()
                raw_dfs["sih_transactions"] = con.execute(f"SELECT * FROM '{sih_path}'").fetchdf()
                con.close()

        return self._quarantine_and_split(raw_dfs)

    def load_from_duckdb(
        self, 
        db_path: str
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Load datasets directly from a DuckDB database file.
        """
        normalized_db = os.path.abspath(db_path).replace("\\", "/")
        if not os.path.exists(normalized_db):
            raise FileNotFoundError(f"DuckDB database file not found: {normalized_db}")

        con = duckdb.connect(normalized_db, read_only=True)
        raw_dfs = {}
        for table in ["transactions", "transaction_inputs", "transaction_outputs", "network_events", "labels"]:
            try:
                raw_dfs[table] = con.execute(f"SELECT * FROM {table}").fetchdf()
            except Exception:
                raw_dfs[table] = pd.DataFrame()
        con.close()

        return self._quarantine_and_split(raw_dfs)

    def _quarantine_and_split(
        self, 
        raw_dfs: Dict[str, pd.DataFrame]
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
        """
        Splits ingested data into clean observational datasets and quarantined metadata.
        Guarantees that generator-only fields are never present in observational datasets.
        """
        observational = {}
        quarantined = {}

        # 1. Labels and ground-truth metadata
        if "labels" in raw_dfs and not raw_dfs["labels"].empty:
            quarantined["labels"] = raw_dfs["labels"].copy()

        # 2. Observational tables: strip any residual generator metadata columns
        for table_name in ["transactions", "transaction_inputs", "transaction_outputs", "network_events"]:
            if table_name in raw_dfs and not raw_dfs[table_name].empty:
                df = raw_dfs[table_name].copy()
                # Find any generator metadata columns that leaked in
                cols_to_drop = [c for c in df.columns if c in GENERATOR_METADATA_COLUMNS]
                if cols_to_drop:
                    # Save quarantined columns before removing
                    id_col = "txid" if "txid" in df.columns else df.columns[0]
                    save_cols = [id_col] + [c for c in cols_to_drop if c != id_col]
                    quarantined[f"{table_name}_generator_meta"] = df[save_cols].copy()
                    df = df.drop(columns=cols_to_drop)
                observational[table_name] = df
            else:
                observational[table_name] = pd.DataFrame()

        # 3. Handle consolidated sih_transactions if present
        if "sih_transactions" in raw_dfs and not raw_dfs["sih_transactions"].empty:
            sih_df = raw_dfs["sih_transactions"].copy()
            cols_to_drop = [c for c in sih_df.columns if c in GENERATOR_METADATA_COLUMNS]
            if cols_to_drop:
                id_col = "txid" if "txid" in sih_df.columns else sih_df.columns[0]
                save_cols = [id_col] + [c for c in cols_to_drop if c != id_col]
                quarantined["sih_generator_meta"] = sih_df[save_cols].copy()
                sih_df = sih_df.drop(columns=cols_to_drop)
            observational["sih_transactions"] = sih_df

        return observational, quarantined

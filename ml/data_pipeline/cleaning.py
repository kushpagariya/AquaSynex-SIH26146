"""
AquaSynex — Data Cleaning Module (Phase 2.2)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Responsibilities:
- Deduplicate records across all observational entities.
- Trim whitespace and standardize hex casing (lowercase txids, addresses).
- Handle missing values and impute derivable fields (fee, input_count, output_count).
- Filter or repair corrupt records without modifying raw source files.
- Produce clean data structures ready for canonical normalization.
"""

from typing import Dict, Tuple, Any, List
import pandas as pd
import numpy as np

class DataCleaningEngine:
    def __init__(self):
        self.cleaning_stats: Dict[str, Any] = {}

    def clean(self, observational_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Execute full data cleaning workflow on observational tables.
        Returns a dictionary of cleaned DataFrames.
        """
        cleaned = {}
        stats = {
            "dropped_duplicates": {},
            "null_imputations": {},
            "casing_standardized": 0
        }

        # 1. Clean Transactions
        if "transactions" in observational_data and not observational_data["transactions"].empty:
            df_tx = observational_data["transactions"].copy()
            init_tx_len = len(df_tx)

            # Drop missing essential primary keys
            df_tx = df_tx.dropna(subset=["txid"])
            
            # String canonicalization: strip whitespace and lowercase txid
            df_tx["txid"] = df_tx["txid"].astype(str).str.strip().str.lower()
            if "block_hash" in df_tx.columns:
                df_tx["block_hash"] = df_tx["block_hash"].astype(str).str.strip().str.lower()

            # Deduplication
            df_tx = df_tx.drop_duplicates(subset=["txid"], keep="first")
            stats["dropped_duplicates"]["transactions"] = init_tx_len - len(df_tx)

            # Missing value imputation
            if "fee_satoshi" in df_tx.columns:
                missing_fees = df_tx["fee_satoshi"].isna()
                if missing_fees.any():
                    # Impute fee as in - out if both are present
                    derivable = missing_fees & df_tx["total_input_value_satoshi"].notna() & df_tx["total_output_value_satoshi"].notna()
                    df_tx.loc[derivable, "fee_satoshi"] = (
                        df_tx.loc[derivable, "total_input_value_satoshi"] - df_tx.loc[derivable, "total_output_value_satoshi"]
                    )
                    stats["null_imputations"]["fee_satoshi"] = int(derivable.sum())

            cleaned["transactions"] = df_tx
        else:
            cleaned["transactions"] = pd.DataFrame()

        # 2. Clean Transaction Inputs
        if "transaction_inputs" in observational_data and not observational_data["transaction_inputs"].empty:
            df_in = observational_data["transaction_inputs"].copy()
            init_in_len = len(df_in)

            df_in = df_in.dropna(subset=["txid", "input_index"])
            df_in["txid"] = df_in["txid"].astype(str).str.strip().str.lower()
            if "address" in df_in.columns:
                df_in["address"] = df_in["address"].astype(str).str.strip()
            if "previous_transaction_id" in df_in.columns:
                df_in["previous_transaction_id"] = df_in["previous_transaction_id"].astype(str).str.strip().str.lower()

            # Deduplication
            df_in = df_in.drop_duplicates(subset=["txid", "input_index"], keep="first")
            stats["dropped_duplicates"]["transaction_inputs"] = init_in_len - len(df_in)

            # Filter orphans if transactions exist
            if not cleaned["transactions"].empty:
                valid_txids = set(cleaned["transactions"]["txid"])
                df_in = df_in[df_in["txid"].isin(valid_txids)].copy()

            cleaned["transaction_inputs"] = df_in
        else:
            cleaned["transaction_inputs"] = pd.DataFrame()

        # 3. Clean Transaction Outputs
        if "transaction_outputs" in observational_data and not observational_data["transaction_outputs"].empty:
            df_out = observational_data["transaction_outputs"].copy()
            init_out_len = len(df_out)

            df_out = df_out.dropna(subset=["txid", "output_index"])
            df_out["txid"] = df_out["txid"].astype(str).str.strip().str.lower()
            if "address" in df_out.columns:
                df_out["address"] = df_out["address"].astype(str).str.strip()

            # Deduplication
            df_out = df_out.drop_duplicates(subset=["txid", "output_index"], keep="first")
            stats["dropped_duplicates"]["transaction_outputs"] = init_out_len - len(df_out)

            # Filter orphans
            if not cleaned["transactions"].empty:
                valid_txids = set(cleaned["transactions"]["txid"])
                df_out = df_out[df_out["txid"].isin(valid_txids)].copy()

            cleaned["transaction_outputs"] = df_out
        else:
            cleaned["transaction_outputs"] = pd.DataFrame()

        # 4. Clean Network Events
        if "network_events" in observational_data and not observational_data["network_events"].empty:
            df_net = observational_data["network_events"].copy()
            init_net_len = len(df_net)

            df_net = df_net.dropna(subset=["event_id", "txid"])
            df_net["event_id"] = df_net["event_id"].astype(str).str.strip()
            df_net["txid"] = df_net["txid"].astype(str).str.strip().str.lower()
            df_net["src_ip"] = df_net["src_ip"].astype(str).str.strip()
            df_net["dst_ip"] = df_net["dst_ip"].astype(str).str.strip()
            df_net["country"] = df_net["country"].astype(str).str.strip().str.upper()

            # Deduplication
            df_net = df_net.drop_duplicates(subset=["event_id"], keep="first")
            stats["dropped_duplicates"]["network_events"] = init_net_len - len(df_net)

            # Default port imputation if null
            if df_net["dst_port"].isna().any():
                null_count = int(df_net["dst_port"].isna().sum())
                df_net["dst_port"] = df_net["dst_port"].fillna(8333).astype(int)
                stats["null_imputations"]["dst_port"] = null_count

            # Filter orphans
            if not cleaned["transactions"].empty:
                valid_txids = set(cleaned["transactions"]["txid"])
                df_net = df_net[df_net["txid"].isin(valid_txids)].copy()

            cleaned["network_events"] = df_net
        else:
            cleaned["network_events"] = pd.DataFrame()

        self.cleaning_stats = stats
        return cleaned

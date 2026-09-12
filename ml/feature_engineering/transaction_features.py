"""
AquaSynex — Transaction-Level Feature Extractor (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Computes 15 canonical transaction-level features:
- Core counts: input_count, output_count, input_output_ratio
- Satoshi values: total_input_sats, total_output_sats, fee_sats
- Statistical distributions: avg_input_value_sats, avg_output_value_sats, max_input_value_sats, max_output_value_sats
- Rates and ratios: fee_rate_sat_per_byte, value_balance_ratio, size_bytes
- Log transforms: log_total_value, log_fee
"""

from typing import Dict
import numpy as np
import pandas as pd

class TransactionFeatureExtractor:
    def extract(self, canonical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract transaction-level features from canonical tables.
        Returns a DataFrame indexed by transaction_id.
        """
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())
        df_out = canonical_data.get("transaction_outputs", pd.DataFrame())

        if df_tx.empty:
            raise ValueError("canonical_transactions table is missing or empty.")

        features = pd.DataFrame()
        features["transaction_id"] = df_tx["transaction_id"].copy()

        # 1. Structural counts
        features["tx_input_count"] = df_tx["input_count"].astype(int)
        features["tx_output_count"] = df_tx["output_count"].astype(int)
        features["tx_input_output_ratio"] = (
            features["tx_input_count"] / np.maximum(features["tx_output_count"], 1)
        ).astype(float)

        # 2. Values in Satoshis
        features["tx_total_input_sats"] = df_tx["total_input_value_satoshi"].astype("int64")
        features["tx_total_output_sats"] = df_tx["total_output_value_satoshi"].astype("int64")
        features["tx_fee_sats"] = df_tx["fee_satoshi"].astype("int64")

        # 3. Size & Rates
        features["tx_size_bytes"] = df_tx["transaction_size_bytes"].fillna(250).astype(int)
        features["tx_fee_rate_sat_per_byte"] = (
            features["tx_fee_sats"] / np.maximum(features["tx_size_bytes"], 1)
        ).astype(float)

        features["tx_value_balance_ratio"] = np.clip(
            features["tx_total_output_sats"] / np.maximum(features["tx_total_input_sats"], 1),
            0.0, 1.0
        ).astype(float)

        # 4. Input aggregations (max and average)
        if not df_in.empty:
            in_val_col = "input_value_satoshi" if "input_value_satoshi" in df_in.columns else "amount_satoshi"
            in_aggs = df_in.groupby("transaction_id")[in_val_col].agg(["mean", "max"]).reset_index()
            in_aggs.rename(columns={"mean": "tx_avg_input_value_sats", "max": "tx_max_input_value_sats"}, inplace=True)
            features = features.merge(in_aggs, on="transaction_id", how="left")
        else:
            features["tx_avg_input_value_sats"] = features["tx_total_input_sats"] / np.maximum(features["tx_input_count"], 1)
            features["tx_max_input_value_sats"] = features["tx_total_input_sats"]

        # 5. Output aggregations (max and average)
        if not df_out.empty:
            out_val_col = "output_value_satoshi" if "output_value_satoshi" in df_out.columns else "amount_satoshi"
            out_aggs = df_out.groupby("transaction_id")[out_val_col].agg(["mean", "max"]).reset_index()
            out_aggs.rename(columns={"mean": "tx_avg_output_value_sats", "max": "tx_max_output_value_sats"}, inplace=True)
            features = features.merge(out_aggs, on="transaction_id", how="left")
        else:
            features["tx_avg_output_value_sats"] = features["tx_total_output_sats"] / np.maximum(features["tx_output_count"], 1)
            features["tx_max_output_value_sats"] = features["tx_total_output_sats"]

        # 6. Log transforms for heavy-tailed amount features
        features["tx_log_total_value"] = np.log1p(np.maximum(features["tx_total_output_sats"], 0)).astype(float)
        features["tx_log_fee"] = np.log1p(np.maximum(features["tx_fee_sats"], 0)).astype(float)

        # Fill any missing aggregation values
        features["tx_avg_input_value_sats"] = features["tx_avg_input_value_sats"].fillna(0.0).astype(float)
        features["tx_max_input_value_sats"] = features["tx_max_input_value_sats"].fillna(0).astype("int64")
        features["tx_avg_output_value_sats"] = features["tx_avg_output_value_sats"].fillna(0.0).astype(float)
        features["tx_max_output_value_sats"] = features["tx_max_output_value_sats"].fillna(0).astype("int64")

        return features

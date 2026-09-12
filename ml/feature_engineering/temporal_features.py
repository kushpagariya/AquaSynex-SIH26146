"""
AquaSynex — Temporal Feature Extractor (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Computes 6 canonical temporal features:
- time_hour_of_day (0–23)
- time_day_of_week (0–6)
- time_since_prev_global_tx_sec
- time_since_prev_addr_tx_sec
- time_txs_last_1m
- time_txs_last_5m
- time_txs_last_1h

Also optionally computes the experimental feature:
- time_burst_indicator (binary threshold flag: time_since_prev_addr_tx_sec < 10)
  kept strictly experimental and outside the canonical matrix.
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd

class TemporalFeatureExtractor:
    def extract(
        self, 
        canonical_data: Dict[str, pd.DataFrame],
        include_experimental: bool = False
    ) -> pd.DataFrame:
        """
        Extract temporal activity features with strict chronological lookback.
        """
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())

        if df_tx.empty:
            raise ValueError("canonical_transactions table is missing or empty.")

        # Sort chronologically
        tx_sorted = df_tx.sort_values(by=["timestamp_epoch_sec", "transaction_id"]).copy()

        # Build primary sender mapping
        primary_senders = {}
        if not df_in.empty:
            in_addr_col = "input_address" if "input_address" in df_in.columns else "address"
            first_inputs = df_in.sort_values(by=["transaction_id", "input_index"]).drop_duplicates(
                subset=["transaction_id"], keep="first"
            )
            for _, r in first_inputs.iterrows():
                primary_senders[r["transaction_id"]] = str(r[in_addr_col]).strip()

        ts_series = pd.to_datetime(tx_sorted["timestamp"], utc=True)
        epochs = tx_sorted["timestamp_epoch_sec"].values

        features = pd.DataFrame()
        features["transaction_id"] = tx_sorted["transaction_id"].values

        # 1. Diurnal and Calendar Features
        features["time_hour_of_day"] = ts_series.dt.hour.values.astype(int)
        features["time_day_of_week"] = ts_series.dt.dayofweek.values.astype(int)

        # 2. Global Stream Time Delta
        prev_global_epochs = np.roll(epochs, 1)
        global_deltas = epochs - prev_global_epochs
        global_deltas[0] = 0.0  # First transaction baseline
        features["time_since_prev_global_tx_sec"] = np.maximum(global_deltas, 0.0).astype(float)

        # 3. Rolling Window Velocity via O(log N) Binary Search
        # Strictly look back: window [T - window_sec, T)
        # side='left' on T finds index of first occurrence of T, ensuring strictly t < T
        txs_1m = []
        txs_5m = []
        txs_1h = []

        for idx, t in enumerate(epochs):
            # Left bound of current timestamp strictly excludes future data
            left_curr = np.searchsorted(epochs, t, side="left")
            idx_1m = np.searchsorted(epochs, t - 60, side="left")
            idx_5m = np.searchsorted(epochs, t - 300, side="left")
            idx_1h = np.searchsorted(epochs, t - 3600, side="left")

            txs_1m.append(max(0, left_curr - idx_1m))
            txs_5m.append(max(0, left_curr - idx_5m))
            txs_1h.append(max(0, left_curr - idx_1h))

        features["time_txs_last_1m"] = np.array(txs_1m, dtype=int)
        features["time_txs_last_5m"] = np.array(txs_5m, dtype=int)
        features["time_txs_last_1h"] = np.array(txs_1h, dtype=int)

        # 4. Address-Specific Pacing
        last_addr_seen = {}
        addr_deltas = []
        for txid, t in zip(features["transaction_id"].values, epochs):
            sender = primary_senders.get(txid, None)
            if sender and sender in last_addr_seen:
                delta = max(0.0, float(t - last_addr_seen[sender]))
            else:
                delta = 86400.0  # Impute 24 hours for fresh address
            addr_deltas.append(delta)

            if sender:
                last_addr_seen[sender] = t

        features["time_since_prev_addr_tx_sec"] = np.array(addr_deltas, dtype=float)

        # 5. Optional Experimental Feature
        if include_experimental:
            features["time_burst_indicator"] = (features["time_since_prev_addr_tx_sec"] < 10.0).astype(int)

        return features

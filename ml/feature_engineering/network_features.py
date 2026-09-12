"""
AquaSynex — Network Telemetry Feature Extractor (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Computes 5 canonical network features:
- net_src_port (ephemeral client port)
- net_dst_port (peer listening port)
- net_is_standard_bitcoin_port (1 if dst_port == 8333, else 0)
- net_asn (Autonomous System Number)
- net_hist_unique_ips_for_addr (IP churn: unique IPs previously used by this sender with t < T_tx)

DESIGN NOTE:
In accordance with ML audit guidelines, hardcoded port-to-proxy rules (e.g. 443/8080 as Tor)
and hand-crafted offshore country lists are strictly forbidden and excluded.
"""

from typing import Dict, Set
import numpy as np
import pandas as pd

class NetworkFeatureExtractor:
    def extract(self, canonical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract network-layer features from canonical network events.
        """
        df_net = canonical_data.get("network_events", pd.DataFrame())
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())

        if df_net.empty:
            raise ValueError("canonical_network_events table is missing or empty.")

        # Map primary sender
        primary_senders = {}
        if not df_in.empty:
            in_addr_col = "input_address" if "input_address" in df_in.columns else "address"
            first_inputs = df_in.sort_values(by=["transaction_id", "input_index"]).drop_duplicates(
                subset=["transaction_id"], keep="first"
            )
            for _, r in first_inputs.iterrows():
                primary_senders[r["transaction_id"]] = str(r[in_addr_col]).strip()

        # Sort network events chronologically
        net_sorted = df_net.sort_values(by=["timestamp_epoch_sec", "transaction_id"]).copy()

        # Track historical IP diversity per sender (t < T_tx)
        addr_ip_history: Dict[str, Set[str]] = {}
        hist_ip_counts = []

        for _, row in net_sorted.iterrows():
            txid = row["transaction_id"]
            src_ip = str(row["src_ip"]).strip()
            sender = primary_senders.get(txid, f"unknown_{txid[:8]}")

            # Read historical IPs prior to current event
            prior_ips = addr_ip_history.get(sender, set())
            hist_ip_counts.append(len(prior_ips))

            # Update history for future transactions
            if sender not in addr_ip_history:
                addr_ip_history[sender] = set()
            addr_ip_history[sender].add(src_ip)

        net_sorted["net_hist_unique_ips_for_addr"] = hist_ip_counts

        # If transaction table is provided, retain last event before/at transaction timestamp
        if not df_tx.empty and "timestamp_epoch_sec" in df_tx.columns:
            tx_col = "transaction_id" if "transaction_id" in df_tx.columns else "txid"
            tx_ts_map = df_tx.set_index(tx_col)["timestamp_epoch_sec"].to_dict()
            tx_epochs = net_sorted["transaction_id"].map(tx_ts_map)
            valid_mask = tx_epochs.isna() | (net_sorted["timestamp_epoch_sec"] <= tx_epochs)
            if valid_mask.any():
                net_sorted = net_sorted[valid_mask].copy()

        # Reduce to exactly one row per transaction by retaining the last event
        net_sorted = net_sorted.drop_duplicates(subset=["transaction_id"], keep="last").copy()

        # Fill established defaults before integer casts
        src_port_filled = net_sorted["src_port"].fillna(0).astype(int)
        dst_port_filled = net_sorted["dst_port"].fillna(8333).astype(int)
        asn_filled = net_sorted["asn"].fillna(0).astype("int64")

        features = pd.DataFrame()
        features["transaction_id"] = net_sorted["transaction_id"].values
        features["net_src_port"] = src_port_filled.values
        features["net_dst_port"] = dst_port_filled.values
        features["net_is_standard_bitcoin_port"] = (dst_port_filled.values == 8333).astype(int)
        features["net_asn"] = asn_filled.values
        features["net_hist_unique_ips_for_addr"] = net_sorted["net_hist_unique_ips_for_addr"].fillna(0).astype(int).values

        # Optional observational country string retained for context/analysis
        if "country" in net_sorted.columns:
            features["net_country"] = net_sorted["country"].fillna("UNKNOWN").astype(str).values

        return features

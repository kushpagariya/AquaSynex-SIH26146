"""
AquaSynex — Address & Entity Behavioral Feature Extractor (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Computes 8 historical address behavioral features for the primary spending address:
- addr_hist_tx_count
- addr_hist_total_sent_sats
- addr_hist_total_received_sats
- addr_hist_avg_tx_val_sats
- addr_hist_unique_counterparties
- addr_hist_active_days
- addr_hist_tx_per_day
- addr_reuse_count

STRICT ANTI-LEAKAGE ENFORCEMENT:
Features for transaction T occurring at timestamp T_tx strictly use historical
activity where t < T_tx. Future transactions are completely inaccessible.
"""

from typing import Dict, Set
import numpy as np
import pandas as pd

class AddressFeatureExtractor:
    def extract(self, canonical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract historical behavioral features with strict t < T_tx lookback.
        Returns DataFrame indexed by transaction_id.
        """
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())
        df_out = canonical_data.get("transaction_outputs", pd.DataFrame())

        if df_tx.empty:
            raise ValueError("canonical_transactions table is missing or empty.")

        # Sort transactions chronologically by epoch timestamp
        tx_sorted = df_tx.sort_values(by=["timestamp_epoch_sec", "transaction_id"]).copy()

        # Build mapping of transaction_id to primary spending address (input index 0)
        # and set of output recipient addresses
        in_addr_col = "input_address" if "input_address" in df_in.columns else "address"
        in_val_col = "input_value_satoshi" if "input_value_satoshi" in df_in.columns else "amount_satoshi"
        out_addr_col = "output_address" if "output_address" in df_out.columns else "address"
        out_val_col = "output_value_satoshi" if "output_value_satoshi" in df_out.columns else "amount_satoshi"

        primary_senders = {}
        if not df_in.empty:
            df_in_sorted = df_in.sort_values(by=["transaction_id", "input_index"])
            first_inputs = df_in_sorted.drop_duplicates(subset=["transaction_id"], keep="first")
            for _, r in first_inputs.iterrows():
                primary_senders[r["transaction_id"]] = str(r[in_addr_col]).strip()

        # Map counterparties per transaction
        tx_recipients = {}
        if not df_out.empty:
            for txid, group in df_out.groupby("transaction_id"):
                tx_recipients[txid] = set(group[out_addr_col].astype(str).str.strip().tolist())

        # Address state tracking dictionaries: address -> state
        # State: first_seen_epoch, tx_count, total_sent, total_received, counterparties_set, input_count
        first_seen = {}
        hist_tx_count = {}
        hist_sent = {}
        hist_received = {}
        hist_counterparties = {}
        hist_input_count = {}

        results = []

        for _, tx_row in tx_sorted.iterrows():
            txid = tx_row["transaction_id"]
            ts = tx_row["timestamp_epoch_sec"]
            sender = primary_senders.get(txid, f"unknown_sender_{txid[:8]}")
            recips = tx_recipients.get(txid, set())
            val_out = tx_row["total_output_value_satoshi"]

            # 1. Read historical values BEFORE updating state (Strict t < T_tx)
            prior_count = hist_tx_count.get(sender, 0)
            prior_sent = hist_sent.get(sender, 0)
            prior_recv = hist_received.get(sender, 0)
            prior_cps = len(hist_counterparties.get(sender, set()))
            prior_first = first_seen.get(sender, ts)
            prior_in_reuse = hist_input_count.get(sender, 0)

            active_days = max(0.0, (ts - prior_first) / 86400.0) if prior_count > 0 else 0.0
            tx_per_day = prior_count / max(active_days, 1.0) if prior_count > 0 else 0.0
            avg_val = float(prior_sent) / float(max(prior_count, 1)) if prior_count > 0 else 0.0

            results.append({
                "transaction_id": txid,
                "addr_hist_tx_count": int(prior_count),
                "addr_hist_total_sent_sats": int(prior_sent),
                "addr_hist_total_received_sats": int(prior_recv),
                "addr_hist_avg_tx_val_sats": float(avg_val),
                "addr_hist_unique_counterparties": int(prior_cps),
                "addr_hist_active_days": float(active_days),
                "addr_hist_tx_per_day": float(tx_per_day),
                "addr_reuse_count": int(prior_in_reuse)
            })

            # 2. Update address state for future transactions
            if sender not in first_seen:
                first_seen[sender] = ts
            hist_tx_count[sender] = prior_count + 1
            hist_sent[sender] = prior_sent + val_out
            hist_input_count[sender] = prior_in_reuse + 1

            if sender not in hist_counterparties:
                hist_counterparties[sender] = set()
            hist_counterparties[sender].update(recips)

            # Also record received values for recipients
            for recip in recips:
                if recip not in first_seen:
                    first_seen[recip] = ts
                hist_received[recip] = hist_received.get(recip, 0) + (val_out // max(len(recips), 1))
                if recip not in hist_counterparties:
                    hist_counterparties[recip] = set()
                hist_counterparties[recip].add(sender)

        feature_df = pd.DataFrame(results)
        return feature_df

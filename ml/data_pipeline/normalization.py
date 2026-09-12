"""
AquaSynex — Data Normalization Module (Phase 2.2)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Responsibilities:
- Normalize timestamps into UTC datetimes and Unix epoch seconds.
- Scale amounts: exact satoshis, BTC equivalents, fee rates, and log transforms.
- Normalize nested raw structures into canonical relational schemas conforming to docs/data/canonical-schema.md.
- Ensure cross-platform Parquet export and DuckDB integration.
"""

import os
import datetime
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import duckdb

SATOSHIS_PER_BTC = 100_000_000

class DataNormalizationEngine:
    def __init__(self, dataset_id: str = "synthetic_v1"):
        self.dataset_id = dataset_id

    def normalize(
        self, 
        cleaned_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Transform cleaned observational records into the canonical schema.
        """
        canonical = {}
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Check if we need to decompose consolidated sih_transactions
        if "sih_transactions" in cleaned_data and not cleaned_data["sih_transactions"].empty and cleaned_data.get("transactions", pd.DataFrame()).empty:
            return self._decompose_sih_to_canonical(cleaned_data["sih_transactions"])

        # 1. Normalize Transactions
        df_tx = cleaned_data.get("transactions", pd.DataFrame())
        if not df_tx.empty:
            tx_norm = df_tx.copy()
            
            # Canonical column naming
            if "txid" in tx_norm.columns and "transaction_id" not in tx_norm.columns:
                tx_norm["transaction_id"] = tx_norm["txid"]
            
            tx_norm["dataset_id"] = self.dataset_id

            # Timestamp normalization
            tx_norm["timestamp"] = pd.to_datetime(tx_norm["timestamp"], utc=True)
            tx_norm["timestamp_epoch_sec"] = tx_norm["timestamp"].astype("int64") // 10**9

            # Amount calculations
            tx_norm["total_input_btc"] = tx_norm["total_input_value_satoshi"] / SATOSHIS_PER_BTC
            tx_norm["total_output_btc"] = tx_norm["total_output_value_satoshi"] / SATOSHIS_PER_BTC
            tx_norm["fee_btc"] = tx_norm["fee_satoshi"] / SATOSHIS_PER_BTC

            # Ratios and Rates
            size_safe = np.maximum(tx_norm["transaction_size_bytes"].fillna(250).values, 1)
            tx_norm["fee_rate_sat_per_byte"] = tx_norm["fee_satoshi"].values / size_safe

            in_safe = np.maximum(tx_norm["total_input_value_satoshi"].values, 1)
            tx_norm["value_balance_ratio"] = np.clip(
                tx_norm["total_output_value_satoshi"].values / in_safe, 0.0, 1.0
            )

            # Log scaling for heavy-tailed amount distributions
            tx_norm["log_total_value_satoshi"] = np.log1p(tx_norm["total_output_value_satoshi"].values)
            tx_norm["log_fee_satoshi"] = np.log1p(tx_norm["fee_satoshi"].values)

            tx_norm["ingested_at"] = now_utc

            # Ensure correct column ordering
            canonical_cols = [
                "transaction_id", "dataset_id", "timestamp", "timestamp_epoch_sec",
                "input_count", "output_count", "total_input_value_satoshi",
                "total_output_value_satoshi", "fee_satoshi", "transaction_size_bytes",
                "total_input_btc", "total_output_btc", "fee_btc",
                "fee_rate_sat_per_byte", "value_balance_ratio",
                "log_total_value_satoshi", "log_fee_satoshi", "ingested_at"
            ]
            # Keep any extra optional columns (e.g. txid)
            canonical_cols_present = [c for c in canonical_cols if c in tx_norm.columns]
            extra_cols = [c for c in tx_norm.columns if c not in canonical_cols_present]
            canonical["transactions"] = tx_norm[canonical_cols_present + extra_cols]
        else:
            canonical["transactions"] = pd.DataFrame()

        # 2. Normalize Transaction Inputs
        df_in = cleaned_data.get("transaction_inputs", pd.DataFrame())
        if not df_in.empty:
            in_norm = df_in.copy()
            if "txid" in in_norm.columns and "transaction_id" not in in_norm.columns:
                in_norm["transaction_id"] = in_norm["txid"]
            in_norm["dataset_id"] = self.dataset_id

            # Canonical surrogate primary key
            if "input_id" not in in_norm.columns:
                in_norm["input_id"] = in_norm["transaction_id"] + ":" + in_norm["input_index"].astype(int).astype(str)

            # Address column normalization
            if "address" in in_norm.columns and "input_address" not in in_norm.columns:
                in_norm["input_address"] = in_norm["address"]

            # Value column normalization
            if "amount_satoshi" in in_norm.columns and "input_value_satoshi" not in in_norm.columns:
                in_norm["input_value_satoshi"] = in_norm["amount_satoshi"]

            in_norm["input_value_btc"] = in_norm["input_value_satoshi"] / SATOSHIS_PER_BTC

            canonical_in_cols = [
                "input_id", "transaction_id", "dataset_id", "input_index",
                "input_address", "input_value_satoshi", "input_value_btc"
            ]
            canonical_in_cols_present = [c for c in canonical_in_cols if c in in_norm.columns]
            extra_in_cols = [c for c in in_norm.columns if c not in canonical_in_cols_present]
            canonical["transaction_inputs"] = in_norm[canonical_in_cols_present + extra_in_cols]
        else:
            canonical["transaction_inputs"] = pd.DataFrame()

        # 3. Normalize Transaction Outputs
        df_out = cleaned_data.get("transaction_outputs", pd.DataFrame())
        if not df_out.empty:
            out_norm = df_out.copy()
            if "txid" in out_norm.columns and "transaction_id" not in out_norm.columns:
                out_norm["transaction_id"] = out_norm["txid"]
            out_norm["dataset_id"] = self.dataset_id

            # Canonical surrogate primary key
            if "output_id" not in out_norm.columns:
                out_norm["output_id"] = out_norm["transaction_id"] + ":" + out_norm["output_index"].astype(int).astype(str)

            # Address column normalization
            if "address" in out_norm.columns and "output_address" not in out_norm.columns:
                out_norm["output_address"] = out_norm["address"]

            # Value column normalization
            if "amount_satoshi" in out_norm.columns and "output_value_satoshi" not in out_norm.columns:
                out_norm["output_value_satoshi"] = out_norm["amount_satoshi"]

            out_norm["output_value_btc"] = out_norm["output_value_satoshi"] / SATOSHIS_PER_BTC

            canonical_out_cols = [
                "output_id", "transaction_id", "dataset_id", "output_index",
                "output_address", "output_value_satoshi", "output_value_btc"
            ]
            if "is_change" in out_norm.columns:
                canonical_out_cols.append("is_change")
            canonical_out_cols_present = [c for c in canonical_out_cols if c in out_norm.columns]
            extra_out_cols = [c for c in out_norm.columns if c not in canonical_out_cols_present]
            canonical["transaction_outputs"] = out_norm[canonical_out_cols_present + extra_out_cols]
        else:
            canonical["transaction_outputs"] = pd.DataFrame()

        # 4. Normalize Network Events
        df_net = cleaned_data.get("network_events", pd.DataFrame())
        if not df_net.empty:
            net_norm = df_net.copy()
            if "txid" in net_norm.columns and "transaction_id" not in net_norm.columns:
                net_norm["transaction_id"] = net_norm["txid"]
            net_norm["dataset_id"] = self.dataset_id

            net_norm["timestamp"] = pd.to_datetime(net_norm["timestamp"], utc=True)
            net_norm["timestamp_epoch_sec"] = net_norm["timestamp"].astype("int64") // 10**9

            canonical_net_cols = [
                "event_id", "transaction_id", "dataset_id", "timestamp", "timestamp_epoch_sec",
                "src_ip", "src_port", "dst_ip", "dst_port", "country", "asn"
            ]
            extra_net_cols = [c for c in net_norm.columns if c not in canonical_net_cols]
            canonical["network_events"] = net_norm[canonical_net_cols + extra_net_cols]
        else:
            canonical["network_events"] = pd.DataFrame()

        return canonical

    def _decompose_sih_to_canonical(self, df_sih: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Decomposes consolidated nested SIH format (arrays of inputs/outputs) into
        relational canonical entities.
        """
        tx_rows = []
        in_rows = []
        out_rows = []
        net_rows = []
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for _, row in df_sih.iterrows():
            txid = str(row["txid"]).strip().lower()
            ts = pd.to_datetime(row["timestamp"], utc=True)
            ts_epoch = int(ts.timestamp())
            
            in_addrs = list(row["input_addresses"])
            in_amts = list(row["input_amounts"])
            out_addrs = list(row["output_addresses"])
            out_amts = list(row["output_amounts"])
            fee = int(row["fee"])

            tot_in = sum(in_amts)
            tot_out = sum(out_amts)
            size = 10 + len(in_addrs) * 148 + len(out_addrs) * 34

            tx_rows.append({
                "transaction_id": txid,
                "txid": txid,
                "dataset_id": self.dataset_id,
                "timestamp": ts,
                "timestamp_epoch_sec": ts_epoch,
                "input_count": len(in_addrs),
                "output_count": len(out_addrs),
                "total_input_value_satoshi": tot_in,
                "total_output_value_satoshi": tot_out,
                "fee_satoshi": fee,
                "transaction_size_bytes": size,
                "total_input_btc": tot_in / SATOSHIS_PER_BTC,
                "total_output_btc": tot_out / SATOSHIS_PER_BTC,
                "fee_btc": fee / SATOSHIS_PER_BTC,
                "fee_rate_sat_per_byte": fee / max(size, 1),
                "value_balance_ratio": min(tot_out / max(tot_in, 1), 1.0),
                "log_total_value_satoshi": np.log1p(tot_out),
                "log_fee_satoshi": np.log1p(fee),
                "ingested_at": now_utc
            })

            for idx, (addr, amt) in enumerate(zip(in_addrs, in_amts)):
                in_rows.append({
                    "input_id": f"{txid}:{idx}",
                    "transaction_id": txid,
                    "txid": txid,
                    "dataset_id": self.dataset_id,
                    "input_index": idx,
                    "input_address": str(addr).strip(),
                    "input_value_satoshi": int(amt),
                    "input_value_btc": int(amt) / SATOSHIS_PER_BTC
                })

            for idx, (addr, amt) in enumerate(zip(out_addrs, out_amts)):
                out_rows.append({
                    "output_id": f"{txid}:{idx}",
                    "transaction_id": txid,
                    "txid": txid,
                    "dataset_id": self.dataset_id,
                    "output_index": idx,
                    "output_address": str(addr).strip(),
                    "output_value_satoshi": int(amt),
                    "output_value_btc": int(amt) / SATOSHIS_PER_BTC
                })

            net_rows.append({
                "event_id": f"EVT_{txid[:16]}",
                "transaction_id": txid,
                "txid": txid,
                "dataset_id": self.dataset_id,
                "timestamp": ts,
                "timestamp_epoch_sec": ts_epoch,
                "src_ip": str(row["src_ip"]).strip(),
                "src_port": int(row["src_port"]),
                "dst_ip": str(row["dst_ip"]).strip(),
                "dst_port": int(row["dst_port"]),
                "country": str(row["country"]).strip().upper(),
                "asn": int(row["asn"])
            })

        return {
            "transactions": pd.DataFrame(tx_rows),
            "transaction_inputs": pd.DataFrame(in_rows),
            "transaction_outputs": pd.DataFrame(out_rows),
            "network_events": pd.DataFrame(net_rows)
        }

    def export_to_parquet(
        self, 
        canonical_data: Dict[str, pd.DataFrame], 
        output_dir: str
    ):
        """
        Save canonical DataFrames to Parquet files using DuckDB zero-copy export.
        Cross-platform (Linux / Windows).
        """
        norm_output_dir = os.path.abspath(output_dir).replace("\\", "/")
        os.makedirs(norm_output_dir, exist_ok=True)

        con = duckdb.connect()
        for table_name, df in canonical_data.items():
            if not df.empty:
                parquet_path = f"{norm_output_dir}/canonical_{table_name}.parquet"
                # Register df and write parquet via DuckDB
                con.register("temp_export_view", df)
                con.execute(f"COPY temp_export_view TO '{parquet_path}' (FORMAT PARQUET)")
                con.unregister("temp_export_view")
        con.close()

    def register_in_duckdb(
        self, 
        canonical_data: Dict[str, pd.DataFrame], 
        db_path: str,
        table_prefix: str = "canonical_"
    ):
        """
        Register canonical tables into an analytical DuckDB database file.
        """
        norm_db = os.path.abspath(db_path).replace("\\", "/")
        os.makedirs(os.path.dirname(norm_db), exist_ok=True)

        con = duckdb.connect(norm_db)
        for table_name, df in canonical_data.items():
            if not df.empty:
                full_table_name = f"{table_prefix}{table_name}"
                con.register("temp_register_view", df)
                con.execute(f"CREATE OR REPLACE TABLE {full_table_name} AS SELECT * FROM temp_register_view")
                con.unregister("temp_register_view")
        con.close()

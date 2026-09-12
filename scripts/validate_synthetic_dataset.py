#!/usr/bin/env python3
"""
AquaSynex — Synthetic Dataset Validation Suite for SIH26146
AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Validates schema correctness, UTXO conservation, referential integrity,
network layer validity, and graph connectivity across generated Parquet tables.
"""

import os
import sys
import re
import ipaddress
import argparse
import datetime
from typing import Dict, List, Set, Any

import duckdb
import pandas as pd
import networkx as nx

IPV4_PATTERN = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")

class DatasetValidator:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict[str, Any] = {}

    def log_error(self, message: str):
        self.errors.append(message)

    def log_warning(self, message: str):
        self.warnings.append(message)

    def load_table(self, filename: str) -> pd.DataFrame:
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            self.log_error(f"Missing required dataset file: {filename}")
            return pd.DataFrame()
        try:
            clean_path = filepath.replace("\\", "/")
            return duckdb.sql(f"SELECT * FROM '{clean_path}'").df()
        except Exception as e:
            self.log_error(f"Failed to read Parquet file {filename}: {e}")
            return pd.DataFrame()

    def run_all_checks(self) -> bool:
        print(f"[*] Starting dataset validation on directory: {self.data_dir}...", flush=True)
        
        # Load tables
        df_tx = self.load_table("transactions.parquet")
        df_in = self.load_table("transaction_inputs.parquet")
        df_out = self.load_table("transaction_outputs.parquet")
        df_net = self.load_table("network_events.parquet")
        df_ent = self.load_table("entities.parquet")
        df_lbl = self.load_table("labels.parquet")
        df_sih = self.load_table("sih_transactions.parquet")

        if self.errors:
            print(f"[!] Critical file loading errors encountered. Aborting remaining checks.", flush=True)
            return False

        self.stats["tx_count"] = len(df_tx)
        self.stats["in_count"] = len(df_in)
        self.stats["out_count"] = len(df_out)
        self.stats["net_count"] = len(df_net)
        self.stats["ent_count"] = len(df_ent)
        self.stats["lbl_count"] = len(df_lbl)
        self.stats["sih_count"] = len(df_sih)

        # 1. Uniqueness & Primary Key Checks
        print("  [1/8] Verifying ID uniqueness & primary keys...", flush=True)
        if df_tx["txid"].duplicated().any():
            dup_tx = df_tx[df_tx["txid"].duplicated()]["txid"].tolist()[:5]
            self.log_error(f"Duplicate TXIDs found in transactions: {dup_tx}")
            
        if df_net["event_id"].duplicated().any():
            self.log_error("Duplicate event_ids found in network_events")
            
        if df_ent["entity_id"].duplicated().any():
            self.log_error("Duplicate entity_ids found in entities")
            
        in_pk_dups = df_in.duplicated(subset=["txid", "input_index"]).sum()
        if in_pk_dups > 0:
            self.log_error(f"Duplicate (txid, input_index) found in inputs: {in_pk_dups}")
            
        out_pk_dups = df_out.duplicated(subset=["txid", "output_index"]).sum()
        if out_pk_dups > 0:
            self.log_error(f"Duplicate (txid, output_index) found in outputs: {out_pk_dups}")

        # 2. Referential Integrity
        print("  [2/8] Verifying referential integrity across relational tables...", flush=True)
        txid_set = set(df_tx["txid"])
        
        orphan_in = set(df_in["txid"]) - txid_set
        if orphan_in:
            self.log_error(f"{len(orphan_in)} orphaned inputs reference non-existent TXIDs")
            
        orphan_out = set(df_out["txid"]) - txid_set
        if orphan_out:
            self.log_error(f"{len(orphan_out)} orphaned outputs reference non-existent TXIDs")
            
        orphan_net = set(df_net["txid"]) - txid_set
        if orphan_net:
            self.log_error(f"{len(orphan_net)} orphaned network events reference non-existent TXIDs")
        missing_net = txid_set - set(df_net["txid"])
        if missing_net:
            self.log_error(f"{len(missing_net)} transactions missing corresponding network events")
        dup_net = df_net["txid"].duplicated().sum()
        if dup_net > 0:
            self.log_error(f"{dup_net} duplicate network events detected per txid")
            
        orphan_lbl = set(df_lbl["txid"]) - txid_set
        if orphan_lbl:
            self.log_error(f"{len(orphan_lbl)} orphaned labels reference non-existent TXIDs")
        missing_lbl = txid_set - set(df_lbl["txid"])
        if missing_lbl:
            self.log_error(f"{len(missing_lbl)} transactions missing corresponding labels")
        dup_lbl = df_lbl["txid"].duplicated().sum()
        if dup_lbl > 0:
            self.log_error(f"{dup_lbl} duplicate labels detected per txid")

        # 3. Bitcoin UTXO Conservation Checks
        print("  [3/8] Verifying Bitcoin conservation rules (in = out + fee)...", flush=True)
        # Check transaction table aggregate conservation
        calc_in = df_tx["total_output_value_satoshi"] + df_tx["fee_satoshi"]
        conservation_mismatches = (df_tx["total_input_value_satoshi"] != calc_in).sum()
        if conservation_mismatches > 0:
            self.log_error(f"{conservation_mismatches} transactions violate aggregate conservation (total_in != total_out + fee)")

        # Verify sum of inputs matches transaction total_in
        in_sums = df_in.groupby("txid")["amount_satoshi"].sum()
        tx_in_sums = df_tx.set_index("txid")["total_input_value_satoshi"]
        s1, s2 = in_sums.align(tx_in_sums)
        in_sum_diffs = (s1 != s2).sum()
        if in_sum_diffs > 0:
            self.log_error(f"{in_sum_diffs} transactions have input sum mismatches with transaction record")

        # Verify sum of outputs matches transaction total_out
        out_sums = df_out.groupby("txid")["amount_satoshi"].sum()
        tx_out_sums = df_tx.set_index("txid")["total_output_value_satoshi"]
        s3, s4 = out_sums.align(tx_out_sums)
        out_sum_diffs = (s3 != s4).sum()
        if out_sum_diffs > 0:
            self.log_error(f"{out_sum_diffs} transactions have output sum mismatches with transaction record")

        # Non-negative amounts and fees
        if (df_tx["fee_satoshi"] < 0).any():
            self.log_error("Negative fees detected in transactions")
        if (df_in["amount_satoshi"] <= 0).any():
            self.log_error("Zero or negative satoshi amounts in inputs")
        if (df_out["amount_satoshi"] <= 0).any():
            self.log_error("Zero or negative satoshi amounts in outputs")

        # 4. Network Layer Validation
        print("  [4/8] Verifying network layer metadata (IP, port, ASN, country)...", flush=True)
        for ip_col in ["src_ip", "dst_ip"]:
            invalid_ips = 0
            for ip in df_net[ip_col]:
                if not IPV4_PATTERN.match(str(ip)):
                    invalid_ips += 1
            if invalid_ips > 0:
                self.log_error(f"{invalid_ips} invalid IPv4 addresses detected in {ip_col}")

        # Port ranges
        for port_col in ["src_port", "dst_port"]:
            invalid_ports = ((df_net[port_col] < 1) | (df_net[port_col] > 65535)).sum()
            if invalid_ports > 0:
                self.log_error(f"{invalid_ports} invalid ports (<1 or >65535) in {port_col}")

        # Country codes
        invalid_countries = (df_net["country"].str.len() != 2).sum()
        if invalid_countries > 0:
            self.log_error(f"{invalid_countries} invalid country codes (must be 2 chars)")

        # ASNs
        if (df_net["asn"] <= 0).any():
            self.log_error("Invalid non-positive ASNs detected")

        # 5. Timestamp & Temporal Checks
        print("  [5/8] Verifying timestamps and ISO 8601 parsing...", flush=True)
        try:
            pd.to_datetime(df_tx["timestamp"], format="ISO8601")
            pd.to_datetime(df_net["timestamp"], format="ISO8601")
        except Exception as e:
            self.log_error(f"Malformed ISO8601 timestamps: {e}")

        # 6. Consolidated SIH Schema Checks
        print("  [6/8] Verifying consolidated SIH challenge schema...", flush=True)
        sih_expected_cols = [
            "txid", "timestamp", "input_addresses", "output_addresses",
            "input_amounts", "output_amounts", "fee", "script_type",
            "src_ip", "src_port", "dst_ip", "dst_port", "country", "asn"
        ]
        missing_sih_cols = set(sih_expected_cols) - set(df_sih.columns)
        if missing_sih_cols:
            self.log_error(f"Missing SIH schema columns: {missing_sih_cols}")

        # 7. Scenario Traceability & Labels Checks
        print("  [7/8] Verifying scenario traceability and ground-truth labels...", flush=True)
        lbl_classes = set(df_lbl["ground_truth_label"].unique())
        if not {0, 1}.issubset(lbl_classes):
            self.log_error(f"Labels must contain both benign (0) and suspicious (1) classes. Found: {lbl_classes}")

        # Check benign high volume is labeled 0
        bhv_labels = df_lbl[df_lbl["behavior_type"] == "benign_high_volume"]["ground_truth_label"].unique()
        if len(bhv_labels) > 0 and (bhv_labels != [0]).any():
            self.log_error("benign_high_volume transactions must be labeled 0 (benign)")

        # Check normal is labeled 0
        norm_labels = df_lbl[df_lbl["behavior_type"] == "normal"]["ground_truth_label"].unique()
        if len(norm_labels) > 0 and (norm_labels != [0]).any():
            self.log_error("normal transactions must be labeled 0 (benign)")

        # 8. Graph Topological Connectivity Check
        print("  [8/8] Constructing NetworkX graph to verify non-trivial topology...", flush=True)
        G = nx.DiGraph()
        for _, row in df_out.head(2000).iterrows():
            G.add_edge(row["txid"], row["address"], weight=row["amount_satoshi"])
        for _, row in df_in.head(2000).iterrows():
            G.add_edge(row["address"], row["txid"], weight=row["amount_satoshi"])

        self.stats["graph_nodes"] = G.number_of_nodes()
        self.stats["graph_edges"] = G.number_of_edges()
        
        # Weakly connected components
        components = list(nx.weakly_connected_components(G))
        self.stats["connected_components"] = len(components)
        largest_comp_size = len(max(components, key=len)) if components else 0
        self.stats["largest_component_size"] = largest_comp_size

        if G.number_of_nodes() == 0 or G.number_of_edges() == 0:
            self.log_error("Graph is empty!")
        if largest_comp_size < 10:
            self.log_warning("Largest connected component in sample is unusually small")

        # Summary
        print("\n" + "=" * 60, flush=True)
        if not self.errors:
            print(">>> VALIDATION PASSED <<<", flush=True)
        else:
            print(">>> VALIDATION FAILED <<<", flush=True)
        print("=" * 60, flush=True)
        print(f"Transactions           : {self.stats.get('tx_count', 0):,}", flush=True)
        print(f"Transaction Inputs     : {self.stats.get('in_count', 0):,}", flush=True)
        print(f"Transaction Outputs    : {self.stats.get('out_count', 0):,}", flush=True)
        print(f"Network Event Records  : {self.stats.get('net_count', 0):,}", flush=True)
        print(f"Entities               : {self.stats.get('ent_count', 0):,}", flush=True)
        print(f"Ground-Truth Labels    : {self.stats.get('lbl_count', 0):,}", flush=True)
        print(f"SIH Consolidated Tx    : {self.stats.get('sih_count', 0):,}", flush=True)
        print(f"Graph Sample Nodes     : {self.stats.get('graph_nodes', 0):,}", flush=True)
        print(f"Graph Sample Edges     : {self.stats.get('graph_edges', 0):,}", flush=True)
        print(f"Connected Components   : {self.stats.get('connected_components', 0):,} (largest: {self.stats.get('largest_component_size', 0):,} nodes)", flush=True)
        print(f"Integrity Errors       : {len(self.errors)}", flush=True)
        print(f"Warnings               : {len(self.warnings)}", flush=True)

        if self.errors:
            print("\nErrors encountered:", flush=True)
            for err in self.errors:
                print(f"  [x] {err}", flush=True)

        if self.warnings:
            print("\nWarnings:", flush=True)
            for warn in self.warnings:
                print(f"  [!] {warn}", flush=True)

        return len(self.errors) == 0

def main():
    parser = argparse.ArgumentParser(description="Validate Synthetic Bitcoin Dataset")
    parser.add_argument("--data-dir", type=str, default="data/sample/", help="Path to generated dataset folder")
    args = parser.parse_args()

    validator = DatasetValidator(data_dir=args.data_dir)
    success = validator.run_all_checks()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

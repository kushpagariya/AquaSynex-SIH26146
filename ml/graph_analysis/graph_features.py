"""
AquaSynex — Historical Graph Feature Extractor (Phase 2.4)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Extracts strictly historical graph features from the canonical dataset:
- graph_fan_in: Transaction input degree (intrinsic to transaction)
- graph_fan_out: Transaction output degree (intrinsic to transaction)
- graph_unique_in_addrs: Number of distinct input addresses
- graph_unique_out_addrs: Number of distinct output addresses
- hist_in_mean_neighbor_degree: Mean degree of incoming address nodes strictly prior to transaction (t < T_tx)
- hist_out_mean_neighbor_degree: Mean degree of outgoing address nodes strictly prior to transaction (t < T_tx)
- hist_component_size: Connected component size in bipartite graph snapshot G_t (t <= T_tx)
- hist_address_reuse_ratio: Proportion of input addresses previously observed (t < T_tx)
- hist_cluster_id: Inferred behavioral entity cluster identifier prior to transaction (t < T_tx)
- hist_cluster_size: Entity cluster size prior to transaction (t < T_tx)
- hist_cluster_tx_count: Entity cluster transaction count prior to transaction (t < T_tx)

TEMPORAL LEAKAGE RULE:
All historical features are evaluated strictly before (or at snapshot for component size)
the transaction timestamp. Future topology is never accessible.
"""

import os
from typing import Dict, List, Set, Any
import numpy as np
import pandas as pd
import duckdb

from ml.graph_analysis.entity_clustering import TemporalEntityClusterer


class GraphComponentTracker:
    """
    Streaming Disjoint-Set tracker to compute weakly connected component size
    of bipartite graph G_t snapshot (t <= T_tx) without future leakage.
    """
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.size: Dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.size[item] = 1
            return item

        path = []
        curr = item
        while self.parent[curr] != curr:
            path.append(curr)
            curr = self.parent[curr]
        for node in path:
            self.parent[node] = curr
        return curr

    def union(self, item1: str, item2: str) -> str:
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 == root2:
            return root1

        if self.size[root1] < self.size[root2]:
            root1, root2 = root2, root1

        self.parent[root2] = root1
        self.size[root1] += self.size[root2]
        return root1

    def get_component_size(self, item: str) -> int:
        root = self.find(item)
        return self.size.get(root, 1)


class GraphFeatureExtractor:
    """
    Computes streaming historical graph features for all transactions.
    """
    def __init__(self):
        self.comp_tracker = GraphComponentTracker()
        self.addr_history_degree: Dict[str, int] = {}
        self.clusterer = TemporalEntityClusterer()

    def extract_features(self, canonical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Extract chronological graph features from canonical tables.
        """
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())
        df_out = canonical_data.get("transaction_outputs", pd.DataFrame())

        if df_tx.empty:
            raise ValueError("canonical_transactions table is missing or empty.")

        tx_id_col = "transaction_id" if "transaction_id" in df_tx.columns else "txid"
        in_tx_col = "transaction_id" if "transaction_id" in df_in.columns else "txid"
        out_tx_col = "transaction_id" if "transaction_id" in df_out.columns else "txid"
        in_addr_col = "input_address" if "input_address" in df_in.columns else "address"
        out_addr_col = "output_address" if "output_address" in df_out.columns else "address"

        # 1. Sort transactions strictly chronologically
        df_tx_sorted = df_tx.sort_values(
            by=["timestamp_epoch_sec", tx_id_col],
            ascending=[True, True]
        ).reset_index(drop=True)

        # 2. Extract cluster features via TemporalEntityClusterer
        print("[*] Running chronological entity clustering...", flush=True)
        cluster_features_df = self.clusterer.process_transactions_chronologically(
            df_tx=df_tx_sorted,
            df_in=df_in,
            df_out=df_out
        )

        # 3. Pre-group inputs and outputs by transaction_id
        inputs_by_tx: Dict[str, List[str]] = {}
        if not df_in.empty:
            for _, r in df_in.iterrows():
                txid = str(r[in_tx_col]).strip().lower()
                addr = str(r[in_addr_col]).strip()
                if addr and addr not in ("None", "nan"):
                    inputs_by_tx.setdefault(txid, []).append(addr)

        outputs_by_tx: Dict[str, List[str]] = {}
        if not df_out.empty:
            for _, r in df_out.iterrows():
                txid = str(r[out_tx_col]).strip().lower()
                addr = str(r[out_addr_col]).strip()
                if addr and addr not in ("None", "nan"):
                    outputs_by_tx.setdefault(txid, []).append(addr)

        # 4. Stream transactions and compute historical topological features
        print("[*] Computing historical bipartite graph features...", flush=True)
        self.comp_tracker = GraphComponentTracker()
        self.addr_history_degree = {}

        graph_records = []

        for _, tx_row in df_tx_sorted.iterrows():
            txid = str(tx_row[tx_id_col]).strip().lower()
            tx_node = f"tx_{txid}"
            
            in_addrs = inputs_by_tx.get(txid, [])
            out_addrs = outputs_by_tx.get(txid, [])

            unique_in_addrs = list(set(in_addrs))
            unique_out_addrs = list(set(out_addrs))

            fan_in = len(in_addrs)
            fan_out = len(out_addrs)

            # HISTORICAL FEATURE A: Neighbor degree prior to transaction (t < T_tx)
            if unique_in_addrs:
                in_neighbor_degrees = [self.addr_history_degree.get(a, 0) for a in unique_in_addrs]
                hist_in_mean_neighbor_deg = float(np.mean(in_neighbor_degrees))
            else:
                hist_in_mean_neighbor_deg = 0.0

            if unique_out_addrs:
                out_neighbor_degrees = [self.addr_history_degree.get(a, 0) for a in unique_out_addrs]
                hist_out_mean_neighbor_deg = float(np.mean(out_neighbor_degrees))
            else:
                hist_out_mean_neighbor_deg = 0.0

            # HISTORICAL FEATURE B: Address reuse ratio (t < T_tx)
            if in_addrs:
                reused_count = sum(1 for a in in_addrs if self.addr_history_degree.get(a, 0) > 0)
                hist_reuse_ratio = float(reused_count / len(in_addrs))
            else:
                hist_reuse_ratio = 0.0

            # SNAPSHOT FEATURE C: Weakly connected component size at snapshot (t <= T_tx)
            # Register transaction node and union with all its input/output addresses
            self.comp_tracker.find(tx_node)
            for a in unique_in_addrs:
                a_node = f"addr_{a}"
                self.comp_tracker.find(a_node)
                self.comp_tracker.union(tx_node, a_node)

            for a in unique_out_addrs:
                a_node = f"addr_{a}"
                self.comp_tracker.find(a_node)
                self.comp_tracker.union(tx_node, a_node)

            hist_comp_size = self.comp_tracker.get_component_size(tx_node)

            # UPDATE STATE: Increment address observation degree for future transactions
            for a in in_addrs:
                self.addr_history_degree[a] = self.addr_history_degree.get(a, 0) + 1
            for a in out_addrs:
                self.addr_history_degree[a] = self.addr_history_degree.get(a, 0) + 1

            graph_records.append({
                "transaction_id": txid,
                "graph_fan_in": int(fan_in),
                "graph_fan_out": int(fan_out),
                "graph_unique_in_addrs": int(len(unique_in_addrs)),
                "graph_unique_out_addrs": int(len(unique_out_addrs)),
                "hist_in_mean_neighbor_degree": round(hist_in_mean_neighbor_deg, 4),
                "hist_out_mean_neighbor_degree": round(hist_out_mean_neighbor_deg, 4),
                "hist_component_size": int(hist_comp_size),
                "hist_address_reuse_ratio": round(hist_reuse_ratio, 4)
            })

        graph_features_df = pd.DataFrame(graph_records)

        # Merge topological features with entity clustering features
        merged_df = graph_features_df.merge(cluster_features_df, on="transaction_id", how="left")

        # Sort back by transaction_id to match canonical table order
        merged_df = merged_df.sort_values(by="transaction_id").reset_index(drop=True)

        print(f"[+] Graph features generated successfully: {len(merged_df):,} rows x {len(merged_df.columns)} columns.", flush=True)
        return merged_df

    def export_graph_features(self, df_features: pd.DataFrame, output_dir: str):
        """
        Export graph feature table to Parquet via DuckDB.
        """
        norm_dir = os.path.abspath(output_dir).replace("\\", "/")
        os.makedirs(norm_dir, exist_ok=True)
        output_file = f"{norm_dir}/graph_features.parquet"

        con = duckdb.connect()
        con.register("gf_view", df_features)
        con.execute(f"COPY gf_view TO '{output_file}' (FORMAT PARQUET)")
        con.unregister("gf_view")
        con.close()
        print(f"[+] Exported graph features to: {output_file}", flush=True)

"""
AquaSynex — Bipartite Bitcoin Transaction Graph Builder (Phase 2.4)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Constructs a directed bipartite graph:
    Address --INPUT_TO--> Transaction --OUTPUT_TO--> Address

Node Types:
- "address": Represents a unique Bitcoin address (prefixed: 'addr_<address>')
- "transaction": Represents a verified Bitcoin transaction (prefixed: 'tx_<transaction_id>')

Edge Types:
- "INPUT_TO": Value flow from spending address into transaction (attrs: amount_satoshi, input_index, timestamp_epoch_sec)
- "OUTPUT_TO": Value flow from transaction to recipient/change address (attrs: amount_satoshi, output_index, is_change, timestamp_epoch_sec)
"""

import os
import argparse
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import networkx as nx
import duckdb

class BipartiteGraphBuilder:
    def __init__(self):
        self.G: nx.DiGraph = nx.DiGraph()
        self.nodes_df: pd.DataFrame = pd.DataFrame()
        self.edges_df: pd.DataFrame = pd.DataFrame()

    def build_graph(self, canonical_data: Dict[str, pd.DataFrame]) -> nx.DiGraph:
        """
        Build the directed bipartite NetworkX graph from canonical transaction records.
        """
        df_tx = canonical_data.get("transactions", pd.DataFrame())
        df_in = canonical_data.get("transaction_inputs", pd.DataFrame())
        df_out = canonical_data.get("transaction_outputs", pd.DataFrame())

        if df_tx.empty:
            raise ValueError("canonical_transactions table is missing or empty.")

        self.G = nx.DiGraph()
        
        # 1. Add Transaction Nodes
        tx_id_col = "transaction_id" if "transaction_id" in df_tx.columns else "txid"
        for _, r in df_tx.iterrows():
            txid = str(r[tx_id_col]).strip().lower()
            node_id = f"tx_{txid}"
            ts = int(r["timestamp_epoch_sec"]) if "timestamp_epoch_sec" in r and pd.notna(r["timestamp_epoch_sec"]) else 0
            fee = int(r["fee_satoshi"]) if "fee_satoshi" in r and pd.notna(r["fee_satoshi"]) else 0
            val_out = int(r["total_output_value_satoshi"]) if "total_output_value_satoshi" in r and pd.notna(r["total_output_value_satoshi"]) else 0
            in_cnt = int(r["input_count"]) if "input_count" in r and pd.notna(r["input_count"]) else 1
            out_cnt = int(r["output_count"]) if "output_count" in r and pd.notna(r["output_count"]) else 1

            self.G.add_node(
                node_id,
                node_type="transaction",
                identifier=txid,
                timestamp_epoch_sec=ts,
                fee_satoshi=fee,
                total_output_value_satoshi=val_out,
                input_count=in_cnt,
                output_count=out_cnt
            )

        # 2. Add Address Nodes & Input Edges (Address --INPUT_TO--> Transaction)
        in_tx_col = "transaction_id" if "transaction_id" in df_in.columns else "txid"
        in_addr_col = "input_address" if "input_address" in df_in.columns else "address"
        in_val_col = "input_value_satoshi" if "input_value_satoshi" in df_in.columns else "amount_satoshi"

        edge_rows = []
        if not df_in.empty:
            # Join with tx timestamps for temporal edge weighting
            tx_ts_map = {str(k).strip().lower(): v for k, v in df_tx.set_index(tx_id_col)["timestamp_epoch_sec"].to_dict().items()}
            for _, r in df_in.iterrows():
                txid = str(r[in_tx_col]).strip().lower()
                addr = str(r[in_addr_col]).strip()
                if not addr or addr == "None" or addr == "nan":
                    continue
                
                addr_node = f"addr_{addr}"
                tx_node = f"tx_{txid}"
                amt = int(r[in_val_col]) if in_val_col in r and pd.notna(r[in_val_col]) else 0
                idx = int(r["input_index"]) if "input_index" in r and pd.notna(r["input_index"]) else 0
                ts = tx_ts_map.get(txid, 0)

                # Add address node if not already present
                if addr_node not in self.G:
                    self.G.add_node(addr_node, node_type="address", identifier=addr, first_seen_epoch=ts, last_seen_epoch=ts)
                else:
                    cur_first = self.G.nodes[addr_node].get("first_seen_epoch", ts)
                    cur_last = self.G.nodes[addr_node].get("last_seen_epoch", ts)
                    self.G.nodes[addr_node]["first_seen_epoch"] = min(cur_first, ts)
                    self.G.nodes[addr_node]["last_seen_epoch"] = max(cur_last, ts)

                # Add directed edge Address -> Transaction
                self.G.add_edge(
                    addr_node,
                    tx_node,
                    edge_type="INPUT_TO",
                    amount_satoshi=amt,
                    index=idx,
                    timestamp_epoch_sec=ts
                )
                edge_rows.append({
                    "edge_id": f"{addr_node}->{tx_node}:{idx}",
                    "source": addr_node,
                    "target": tx_node,
                    "edge_type": "INPUT_TO",
                    "amount_satoshi": amt,
                    "index": idx,
                    "is_change": False,
                    "timestamp_epoch_sec": ts
                })

        # 3. Add Output Edges (Transaction --OUTPUT_TO--> Address)
        out_tx_col = "transaction_id" if "transaction_id" in df_out.columns else "txid"
        out_addr_col = "output_address" if "output_address" in df_out.columns else "address"
        out_val_col = "output_value_satoshi" if "output_value_satoshi" in df_out.columns else "amount_satoshi"

        if not df_out.empty:
            tx_ts_map = {str(k).strip().lower(): v for k, v in df_tx.set_index(tx_id_col)["timestamp_epoch_sec"].to_dict().items()}
            for _, r in df_out.iterrows():
                txid = str(r[out_tx_col]).strip().lower()
                addr = str(r[out_addr_col]).strip()
                if not addr or addr == "None" or addr == "nan":
                    continue

                tx_node = f"tx_{txid}"
                addr_node = f"addr_{addr}"
                amt = int(r[out_val_col]) if out_val_col in r and pd.notna(r[out_val_col]) else 0
                idx = int(r["output_index"]) if "output_index" in r and pd.notna(r["output_index"]) else 0
                is_chg = bool(r["is_change"]) if "is_change" in r and pd.notna(r["is_change"]) else False
                ts = tx_ts_map.get(txid, 0)

                # Add address node if not already present
                if addr_node not in self.G:
                    self.G.add_node(addr_node, node_type="address", identifier=addr, first_seen_epoch=ts, last_seen_epoch=ts)
                else:
                    cur_first = self.G.nodes[addr_node].get("first_seen_epoch", ts)
                    cur_last = self.G.nodes[addr_node].get("last_seen_epoch", ts)
                    self.G.nodes[addr_node]["first_seen_epoch"] = min(cur_first, ts)
                    self.G.nodes[addr_node]["last_seen_epoch"] = max(cur_last, ts)

                # Add directed edge Transaction -> Address
                self.G.add_edge(
                    tx_node,
                    addr_node,
                    edge_type="OUTPUT_TO",
                    amount_satoshi=amt,
                    index=idx,
                    is_change=is_chg,
                    timestamp_epoch_sec=ts
                )
                edge_rows.append({
                    "edge_id": f"{tx_node}->{addr_node}:{idx}",
                    "source": tx_node,
                    "target": addr_node,
                    "edge_type": "OUTPUT_TO",
                    "amount_satoshi": amt,
                    "index": idx,
                    "is_change": is_chg,
                    "timestamp_epoch_sec": ts
                })

        # 4. Construct DataFrames for export
        node_rows = []
        for n, d in self.G.nodes(data=True):
            node_rows.append({
                "node_id": n,
                "node_type": d.get("node_type", "unknown"),
                "identifier": d.get("identifier", ""),
                "timestamp_epoch_sec": d.get("timestamp_epoch_sec", 0),
                "in_degree": self.G.in_degree(n),
                "out_degree": self.G.out_degree(n),
                "total_degree": self.G.degree(n)
            })

        self.nodes_df = pd.DataFrame(node_rows)
        self.edges_df = pd.DataFrame(edge_rows)

        print(f"[+] Bipartite Graph Built: {self.G.number_of_nodes():,} nodes ({len(self.nodes_df[self.nodes_df['node_type'] == 'address']):,} addresses, {len(self.nodes_df[self.nodes_df['node_type'] == 'transaction']):,} transactions), {self.G.number_of_edges():,} directed edges.", flush=True)
        return self.G

    def export_graph_tables(self, output_dir: str):
        """
        Export node and edge tables to Parquet format via DuckDB.
        """
        norm_dir = os.path.abspath(output_dir).replace("\\", "/")
        os.makedirs(norm_dir, exist_ok=True)

        con = duckdb.connect()
        if not self.nodes_df.empty:
            con.register("nodes_view", self.nodes_df)
            con.execute(f"COPY nodes_view TO '{norm_dir}/nodes.parquet' (FORMAT PARQUET)")
            con.unregister("nodes_view")

        if not self.edges_df.empty:
            con.register("edges_view", self.edges_df)
            con.execute(f"COPY edges_view TO '{norm_dir}/edges.parquet' (FORMAT PARQUET)")
            con.unregister("edges_view")
        con.close()
        print(f"[+] Successfully exported nodes.parquet and edges.parquet to: {norm_dir}", flush=True)

"""
AquaSynex — Post-Hoc Macroscopic Graph Metrics (Phase 2.4)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Computes full-graph macroscopic topological statistics for offline exploratory
analysis and architectural auditing.

STRICT ANTI-LEAKAGE BOUNDARY:
The statistics produced by this module (e.g. full-graph PageRank, static giant component)
evaluate the ENTIRE dataset topology post-hoc.
THEY ARE STRICTLY EXCLUDED FROM THE ML FEATURE MATRIX AND USED SOLELY FOR:
1. Architectural health checks and dataset complexity audits.
2. Exploratory network visualization (Notebook 03).
3. Summary reporting in data/processed/graph/graph_summary.json.
"""

import os
import json
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import networkx as nx

class MacroscopicGraphMetrics:
    def __init__(self, G: nx.DiGraph):
        self.G = G
        self.summary: Dict[str, Any] = {}

    def compute_all_metrics(self) -> Dict[str, Any]:
        """
        Compute full macroscopic graph statistics.
        """
        print("[*] Computing macroscopic graph statistics (post-hoc)...", flush=True)
        G = self.G
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()

        if total_nodes == 0:
            return {"error": "Graph is empty"}

        # 1. Node Breakdown
        addr_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "address"]
        tx_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "transaction"]

        # 2. Degree Distributions
        addr_in_degs = [G.in_degree(n) for n in addr_nodes] if addr_nodes else [0]
        addr_out_degs = [G.out_degree(n) for n in addr_nodes] if addr_nodes else [0]
        addr_tot_degs = [G.degree(n) for n in addr_nodes] if addr_nodes else [0]

        tx_in_degs = [G.in_degree(n) for n in tx_nodes] if tx_nodes else [0]
        tx_out_degs = [G.out_degree(n) for n in tx_nodes] if tx_nodes else [0]

        def get_percentiles(vals: List[int]) -> Dict[str, float]:
            if not vals:
                return {"min": 0, "p25": 0, "median": 0, "p75": 0, "p95": 0, "max": 0}
            arr = np.array(vals)
            return {
                "min": int(np.min(arr)),
                "p25": float(np.percentile(arr, 25)),
                "median": float(np.median(arr)),
                "p75": float(np.percentile(arr, 75)),
                "p95": float(np.percentile(arr, 95)),
                "max": int(np.max(arr))
            }

        # 3. Connected Components
        wccs = list(nx.weakly_connected_components(G))
        wcc_sizes = sorted([len(c) for c in wccs], reverse=True)
        giant_wcc_size = wcc_sizes[0] if wcc_sizes else 0
        giant_wcc_fraction = float(giant_wcc_size / total_nodes) if total_nodes > 0 else 0.0

        sccs = list(nx.strongly_connected_components(G))
        scc_sizes = sorted([len(c) for c in sccs], reverse=True)
        giant_scc_size = scc_sizes[0] if scc_sizes else 0

        # 4. Post-Hoc PageRank (Strictly Exploratory)
        print("    - Computing full-graph PageRank...", flush=True)
        try:
            pagerank_dict = nx.pagerank(G, alpha=0.85, max_iter=100)
            pr_values = list(pagerank_dict.values())
            top_10_pr = sorted(pagerank_dict.items(), key=lambda x: x[1], reverse=True)[:10]
            pr_summary = {
                "min": float(np.min(pr_values)),
                "median": float(np.median(pr_values)),
                "p95": float(np.percentile(pr_values, 95)),
                "max": float(np.max(pr_values)),
                "top_10_nodes": [{"node_id": k, "pagerank": round(v, 6)} for k, v in top_10_pr]
            }
        except Exception as e:
            pr_summary = {"error": str(e)}
            pagerank_dict = {}

        # 5. Community Detection (Louvain modularity on undirected projection)
        print("    - Computing community detection...", flush=True)
        try:
            G_undir = G.to_undirected()
            communities = nx.community.louvain_communities(G_undir, seed=42)
            comm_sizes = sorted([len(c) for c in communities], reverse=True)
            modularity = nx.community.modularity(G_undir, communities)
            comm_summary = {
                "num_communities": len(communities),
                "modularity": round(float(modularity), 4),
                "top_5_community_sizes": comm_sizes[:5]
            }
        except Exception as e:
            comm_summary = {"error": str(e)}

        self.summary = {
            "graph_type": "directed_bipartite_bitcoin_graph",
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "address_nodes_count": len(addr_nodes),
            "transaction_nodes_count": len(tx_nodes),
            "density": float(nx.density(G)),
            "weakly_connected_components": {
                "total_components": len(wccs),
                "giant_component_size": giant_wcc_size,
                "giant_component_fraction": round(giant_wcc_fraction, 4),
                "top_5_component_sizes": wcc_sizes[:5]
            },
            "strongly_connected_components": {
                "total_components": len(sccs),
                "giant_scc_size": giant_scc_size
            },
            "degree_distribution": {
                "address_total_degree": get_percentiles(addr_tot_degs),
                "address_in_degree": get_percentiles(addr_in_degs),
                "address_out_degree": get_percentiles(addr_out_degs),
                "transaction_in_degree": get_percentiles(tx_in_degs),
                "transaction_out_degree": get_percentiles(tx_out_degs)
            },
            "post_hoc_pagerank_summary": pr_summary,
            "community_structure": comm_summary
        }

        print("[+] Macroscopic graph statistics computed successfully.", flush=True)
        return self.summary

    def export_summary(self, output_dir: str):
        """
        Export summary to JSON.
        """
        norm_dir = os.path.abspath(output_dir).replace("\\", "/")
        os.makedirs(norm_dir, exist_ok=True)
        summary_path = f"{norm_dir}/graph_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2)
        print(f"[+] Exported graph summary to: {summary_path}", flush=True)

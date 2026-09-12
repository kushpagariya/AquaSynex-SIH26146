"""
AquaSynex — Phase 2.4 Graph Analysis Pipeline Runner
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Executes:
1. Bipartite Graph Construction (Address -> Transaction -> Address)
2. Parquet export of nodes.parquet and edges.parquet
3. Chronological Entity Clustering (Multi-Input & Change heuristics)
4. Historical Future-Invariant Graph Feature Extraction (11 features + transaction_id)
5. Parquet export of graph_features.parquet
6. Post-Hoc Macroscopic Metrics & Community Detection -> graph_summary.json
7. DuckDB table registration: graph_nodes_v1, graph_edges_v1, graph_features_v1, graph_address_clusters_v1
"""

import os
import sys
import time
import argparse
import pandas as pd
import duckdb

from ml.graph_analysis.graph_builder import BipartiteGraphBuilder
from ml.graph_analysis.entity_clustering import TemporalEntityClusterer
from ml.graph_analysis.graph_features import GraphFeatureExtractor
from ml.graph_analysis.graph_metrics import MacroscopicGraphMetrics


def run_graph_pipeline(
    canonical_dir: str = "data/processed/canonical",
    db_path: str = "database/aquasynex.duckdb",
    output_dir: str = "data/processed/graph"
):
    start_time = time.time()
    print("=" * 70)
    print("AquaSynex — Phase 2.4 Graph Analysis & Link Analysis Pipeline")
    print("=" * 70)

    norm_canonical_dir = os.path.abspath(canonical_dir).replace("\\", "/")
    norm_output_dir = os.path.abspath(output_dir).replace("\\", "/")
    norm_db_path = os.path.abspath(db_path).replace("\\", "/")
    os.makedirs(norm_output_dir, exist_ok=True)

    # 1. Load canonical data
    print(f"[*] Loading canonical dataset from: {norm_canonical_dir}...")
    con = duckdb.connect(norm_db_path)
    
    # Load canonical tables directly
    df_tx = con.execute("SELECT * FROM canonical_transactions").df()
    df_in = con.execute("SELECT * FROM canonical_transaction_inputs").df()
    df_out = con.execute("SELECT * FROM canonical_transaction_outputs").df()

    print(f"    - Transactions: {len(df_tx):,} rows")
    print(f"    - Inputs:       {len(df_in):,} rows")
    print(f"    - Outputs:      {len(df_out):,} rows")

    canonical_dict = {
        "transactions": df_tx,
        "transaction_inputs": df_in,
        "transaction_outputs": df_out
    }

    # 2. Build Bipartite Graph
    print("\n[1/4] Constructing directed bipartite graph...")
    builder = BipartiteGraphBuilder()
    G = builder.build_graph(canonical_dict)
    builder.export_graph_tables(norm_output_dir)

    # 3. Extract Historical Future-Invariant Graph Features
    print("\n[2/4] Extracting chronological historical graph features...")
    extractor = GraphFeatureExtractor()
    df_features = extractor.extract_features(canonical_dict)
    extractor.export_graph_features(df_features, norm_output_dir)

    # 4. Export Address Cluster Summary (Post-Hoc inspection)
    print("\n[3/4] Exporting inferred address clusters summary...")
    df_clusters = extractor.clusterer.get_final_cluster_summary()
    clusters_path = f"{norm_output_dir}/address_to_cluster.parquet"
    con.register("cluster_view", df_clusters)
    con.execute(f"COPY cluster_view TO '{clusters_path}' (FORMAT PARQUET)")
    con.unregister("cluster_view")
    print(f"[+] Exported {len(df_clusters):,} clustered addresses to: {clusters_path}")

    # 5. Compute Post-Hoc Macroscopic Metrics & Communities
    print("\n[4/4] Computing post-hoc macroscopic metrics and community structure...")
    metrics_calc = MacroscopicGraphMetrics(G)
    summary = metrics_calc.compute_all_metrics()
    metrics_calc.export_summary(norm_output_dir)

    # 6. Register in DuckDB
    print("\n[*] Registering graph artifacts in DuckDB database...")
    nodes_parquet = f"{norm_output_dir}/nodes.parquet"
    edges_parquet = f"{norm_output_dir}/edges.parquet"
    features_parquet = f"{norm_output_dir}/graph_features.parquet"

    con.execute(f"CREATE OR REPLACE TABLE graph_nodes_v1 AS SELECT * FROM read_parquet('{nodes_parquet}')")
    con.execute(f"CREATE OR REPLACE TABLE graph_edges_v1 AS SELECT * FROM read_parquet('{edges_parquet}')")
    con.execute(f"CREATE OR REPLACE TABLE graph_features_v1 AS SELECT * FROM read_parquet('{features_parquet}')")
    con.execute(f"CREATE OR REPLACE TABLE graph_address_clusters_v1 AS SELECT * FROM read_parquet('{clusters_path}')")

    # Verify DuckDB tables
    node_cnt = con.execute("SELECT COUNT(*) FROM graph_nodes_v1").fetchone()[0]
    edge_cnt = con.execute("SELECT COUNT(*) FROM graph_edges_v1").fetchone()[0]
    feat_cnt = con.execute("SELECT COUNT(*) FROM graph_features_v1").fetchone()[0]
    clust_cnt = con.execute("SELECT COUNT(*) FROM graph_address_clusters_v1").fetchone()[0]

    con.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"Phase 2.4 Pipeline Complete in {elapsed:.2f}s")
    print("=" * 70)
    print(f"  - Graph Nodes (graph_nodes_v1):           {node_cnt:,}")
    print(f"  - Graph Edges (graph_edges_v1):           {edge_cnt:,}")
    print(f"  - Graph Features (graph_features_v1):     {feat_cnt:,} rows x {len(df_features.columns)} cols")
    print(f"  - Clustered Addresses (clusters_v1):      {clust_cnt:,}")
    print(f"  - Macroscopic Summary:                    {norm_output_dir}/graph_summary.json")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AquaSynex Phase 2.4 Graph Analysis Pipeline")
    parser.add_argument("--canonical-dir", default="data/processed/canonical", help="Path to canonical Parquet directory")
    parser.add_argument("--db-path", default="database/aquasynex.duckdb", help="Path to DuckDB database")
    parser.add_argument("--output-dir", default="data/processed/graph", help="Output directory for graph artifacts")
    args = parser.parse_args()

    run_graph_pipeline(
        canonical_dir=args.canonical_dir,
        db_path=args.db_path,
        output_dir=args.output_dir
    )

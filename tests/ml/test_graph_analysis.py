"""
Unit & Integration Tests for AquaSynex Graph Analysis Pipeline (Phase 2.4)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Tests:
1. test_bipartite_graph_structure: Node and edge schema validation.
2. test_entity_clustering_multi_input: Multi-input heuristic clustering.
3. test_entity_clustering_change_output: Change address heuristic linking.
4. test_temporal_clustering_state_evolution: Chronological state evolution.
5. test_future_invariance_clustering: Proves future transactions do not leak into past cluster features.
6. test_future_invariance_neighbor_degree: Proves future transactions do not alter past historical neighbor degrees.
7. test_future_invariance_component_size: Proves future transactions do not back-propagate to past snapshot component sizes.
8. test_future_invariance_address_reuse: Proves future transactions do not alter past historical address reuse ratios.
9. test_macroscopic_metrics_isolation: Verifies post-hoc metrics are quarantined from ML feature tables.
10. test_graph_feature_pipeline_export: End-to-end graph feature extraction and Parquet export.
"""

import os
import shutil
import tempfile
import unittest
import numpy as np
import pandas as pd
import networkx as nx

from ml.graph_analysis.graph_builder import BipartiteGraphBuilder
from ml.graph_analysis.entity_clustering import TemporalEntityClusterer, UnionFind
from ml.graph_analysis.graph_features import GraphFeatureExtractor
from ml.graph_analysis.graph_metrics import MacroscopicGraphMetrics


class TestGraphAnalysis(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tx1 = "1" * 64
        self.tx2 = "2" * 64
        self.tx3 = "3" * 64

        # Mock chronological transactions
        self.mock_tx = pd.DataFrame([
            {
                "transaction_id": self.tx1,
                "timestamp_epoch_sec": 1000,
                "input_count": 2,
                "output_count": 2,
                "total_input_value_satoshi": 50000,
                "total_output_value_satoshi": 48000,
                "fee_satoshi": 2000
            },
            {
                "transaction_id": self.tx2,
                "timestamp_epoch_sec": 2000,
                "input_count": 1,
                "output_count": 2,
                "total_input_value_satoshi": 30000,
                "total_output_value_satoshi": 29000,
                "fee_satoshi": 1000
            },
            {
                "transaction_id": self.tx3,
                "timestamp_epoch_sec": 3000,
                "input_count": 2,
                "output_count": 1,
                "total_input_value_satoshi": 70000,
                "total_output_value_satoshi": 68000,
                "fee_satoshi": 2000
            }
        ])

        # Mock inputs
        self.mock_in = pd.DataFrame([
            {"transaction_id": self.tx1, "input_index": 0, "input_address": "addr_A", "input_value_satoshi": 25000},
            {"transaction_id": self.tx1, "input_index": 1, "input_address": "addr_B", "input_value_satoshi": 25000},
            {"transaction_id": self.tx2, "input_index": 0, "input_address": "addr_C", "input_value_satoshi": 30000},
            {"transaction_id": self.tx3, "input_index": 0, "input_address": "addr_A", "input_value_satoshi": 35000},
            {"transaction_id": self.tx3, "input_index": 1, "input_address": "addr_D", "input_value_satoshi": 35000},
        ])

        # Mock outputs
        self.mock_out = pd.DataFrame([
            {"transaction_id": self.tx1, "output_index": 0, "output_address": "addr_C", "output_value_satoshi": 30000, "is_change": False},
            {"transaction_id": self.tx1, "output_index": 1, "output_address": "addr_E", "output_value_satoshi": 18000, "is_change": True},
            {"transaction_id": self.tx2, "output_index": 0, "output_address": "addr_F", "output_value_satoshi": 20000, "is_change": False},
            {"transaction_id": self.tx2, "output_index": 1, "output_address": "addr_G", "output_value_satoshi": 9000, "is_change": True},
            {"transaction_id": self.tx3, "output_index": 0, "output_address": "addr_H", "output_value_satoshi": 68000, "is_change": False},
        ])

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bipartite_graph_structure(self):
        """Verify bipartite graph schema, node types, and edge attributes."""
        builder = BipartiteGraphBuilder()
        G = builder.build_graph({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        self.assertIsInstance(G, nx.DiGraph)
        self.assertEqual(G.nodes[f"tx_{self.tx1}"]["node_type"], "transaction")
        self.assertEqual(G.nodes["addr_addr_A"]["node_type"], "address")

        # Edge from Address to Tx
        self.assertTrue(G.has_edge("addr_addr_A", f"tx_{self.tx1}"))
        self.assertEqual(G["addr_addr_A"][f"tx_{self.tx1}"]["edge_type"], "INPUT_TO")

        # Edge from Tx to Address
        self.assertTrue(G.has_edge(f"tx_{self.tx1}", "addr_addr_C"))
        self.assertEqual(G[f"tx_{self.tx1}"]["addr_addr_C"]["edge_type"], "OUTPUT_TO")

    def test_entity_clustering_multi_input(self):
        """Verify Multi-Input heuristic merges co-spent addresses."""
        clusterer = TemporalEntityClusterer()
        clusterer.process_transactions_chronologically(
            df_tx=self.mock_tx[self.mock_tx["transaction_id"] == self.tx1],
            df_in=self.mock_in[self.mock_in["transaction_id"] == self.tx1],
            df_out=self.mock_out[self.mock_out["transaction_id"] == self.tx1]
        )

        root_a = clusterer.uf.find("addr_A")
        root_b = clusterer.uf.find("addr_B")
        self.assertEqual(root_a, root_b, "Co-spent inputs addr_A and addr_B must share the same cluster root.")

    def test_entity_clustering_change_output(self):
        """Verify change output is merged with input cluster."""
        clusterer = TemporalEntityClusterer()
        clusterer.process_transactions_chronologically(
            df_tx=self.mock_tx[self.mock_tx["transaction_id"] == self.tx1],
            df_in=self.mock_in[self.mock_in["transaction_id"] == self.tx1],
            df_out=self.mock_out[self.mock_out["transaction_id"] == self.tx1]
        )

        root_a = clusterer.uf.find("addr_A")
        root_e = clusterer.uf.find("addr_E")  # addr_E was marked is_change = True
        self.assertEqual(root_a, root_e, "Change output addr_E must be merged into input cluster.")

    def test_temporal_clustering_state_evolution(self):
        """Verify cluster size and tx count increment correctly over chronological stream."""
        clusterer = TemporalEntityClusterer()
        df_feat = clusterer.process_transactions_chronologically(
            df_tx=self.mock_tx,
            df_in=self.mock_in,
            df_out=self.mock_out
        )

        # tx1 is first time addr_A is seen: hist_cluster_tx_count must be 0
        tx1_row = df_feat[df_feat["transaction_id"] == self.tx1].iloc[0]
        self.assertEqual(tx1_row["hist_cluster_tx_count"], 0)

        # tx3 spends addr_A again: hist_cluster_tx_count must reflect prior activity
        tx3_row = df_feat[df_feat["transaction_id"] == self.tx3].iloc[0]
        self.assertGreater(tx3_row["hist_cluster_tx_count"], 0)
        self.assertGreater(tx3_row["hist_cluster_size"], 1)

    def test_future_invariance_clustering(self):
        """
        MANDATORY ANTI-LEAKAGE PROOF:
        Adding future transactions must NOT alter cluster features of past transactions.
        """
        clusterer = TemporalEntityClusterer()
        # Run 1: On transactions 1 and 2 only
        df_early = clusterer.process_transactions_chronologically(
            df_tx=self.mock_tx.iloc[:2],
            df_in=self.mock_in[self.mock_in["transaction_id"].isin([self.tx1, self.tx2])],
            df_out=self.mock_out[self.mock_out["transaction_id"].isin([self.tx1, self.tx2])]
        )

        # Run 2: On all transactions (including tx3 which merges addr_A with addr_D)
        df_all = clusterer.process_transactions_chronologically(
            df_tx=self.mock_tx,
            df_in=self.mock_in,
            df_out=self.mock_out
        )

        # Assert tx1 and tx2 features are strictly identical
        tx1_early = df_early[df_early["transaction_id"] == self.tx1].iloc[0]
        tx1_all = df_all[df_all["transaction_id"] == self.tx1].iloc[0]

        self.assertEqual(tx1_early["hist_cluster_size"], tx1_all["hist_cluster_size"])
        self.assertEqual(tx1_early["hist_cluster_tx_count"], tx1_all["hist_cluster_tx_count"])
        self.assertEqual(tx1_early["hist_cluster_id"], tx1_all["hist_cluster_id"])

        tx2_early = df_early[df_early["transaction_id"] == self.tx2].iloc[0]
        tx2_all = df_all[df_all["transaction_id"] == self.tx2].iloc[0]

        self.assertEqual(tx2_early["hist_cluster_size"], tx2_all["hist_cluster_size"])
        self.assertEqual(tx2_early["hist_cluster_tx_count"], tx2_all["hist_cluster_tx_count"])

    def test_future_invariance_neighbor_degree(self):
        """MANDATORY ANTI-LEAKAGE PROOF: Neighbor degrees are strictly historical."""
        extractor = GraphFeatureExtractor()

        # Run on early slice
        feat_early = extractor.extract_features({
            "transactions": self.mock_tx.iloc[:2],
            "transaction_inputs": self.mock_in[self.mock_in["transaction_id"].isin([self.tx1, self.tx2])],
            "transaction_outputs": self.mock_out[self.mock_out["transaction_id"].isin([self.tx1, self.tx2])]
        })

        # Run on full slice (where addr_A appears again in tx3)
        feat_all = extractor.extract_features({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        tx1_early = feat_early[feat_early["transaction_id"] == self.tx1].iloc[0]
        tx1_all = feat_all[feat_all["transaction_id"] == self.tx1].iloc[0]

        self.assertEqual(tx1_early["hist_in_mean_neighbor_degree"], tx1_all["hist_in_mean_neighbor_degree"])
        self.assertEqual(tx1_early["hist_out_mean_neighbor_degree"], tx1_all["hist_out_mean_neighbor_degree"])

    def test_future_invariance_component_size(self):
        """MANDATORY ANTI-LEAKAGE PROOF: Snapshot component size is future-invariant."""
        extractor = GraphFeatureExtractor()

        feat_early = extractor.extract_features({
            "transactions": self.mock_tx.iloc[:2],
            "transaction_inputs": self.mock_in[self.mock_in["transaction_id"].isin([self.tx1, self.tx2])],
            "transaction_outputs": self.mock_out[self.mock_out["transaction_id"].isin([self.tx1, self.tx2])]
        })

        feat_all = extractor.extract_features({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        tx1_early = feat_early[feat_early["transaction_id"] == self.tx1].iloc[0]
        tx1_all = feat_all[feat_all["transaction_id"] == self.tx1].iloc[0]

        self.assertEqual(tx1_early["hist_component_size"], tx1_all["hist_component_size"])

    def test_future_invariance_address_reuse(self):
        """MANDATORY ANTI-LEAKAGE PROOF: Address reuse ratio is future-invariant."""
        extractor = GraphFeatureExtractor()

        feat_early = extractor.extract_features({
            "transactions": self.mock_tx.iloc[:2],
            "transaction_inputs": self.mock_in[self.mock_in["transaction_id"].isin([self.tx1, self.tx2])],
            "transaction_outputs": self.mock_out[self.mock_out["transaction_id"].isin([self.tx1, self.tx2])]
        })

        feat_all = extractor.extract_features({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        tx1_early = feat_early[feat_early["transaction_id"] == self.tx1].iloc[0]
        tx1_all = feat_all[feat_all["transaction_id"] == self.tx1].iloc[0]

        self.assertEqual(tx1_early["hist_address_reuse_ratio"], tx1_all["hist_address_reuse_ratio"])

    def test_macroscopic_metrics_isolation(self):
        """Verify macroscopic metrics are produced for auditing, but absent from ML features."""
        builder = BipartiteGraphBuilder()
        G = builder.build_graph({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        metrics = MacroscopicGraphMetrics(G)
        summary = metrics.compute_all_metrics()

        self.assertIn("post_hoc_pagerank_summary", summary)
        self.assertIn("weakly_connected_components", summary)
        self.assertIn("giant_component_fraction", summary["weakly_connected_components"])

        extractor = GraphFeatureExtractor()
        df_feat = extractor.extract_features({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        # STRICT ASSERTION: PageRank and giant component flags MUST NOT exist in ML feature DataFrame
        self.assertNotIn("graph_pagerank", df_feat.columns)
        self.assertNotIn("graph_pagerank_tx", df_feat.columns)
        self.assertNotIn("graph_is_giant_component", df_feat.columns)
        self.assertNotIn("is_giant_component", df_feat.columns)

    def test_graph_feature_pipeline_export(self):
        """Verify graph feature extraction runs end-to-end and exports cleanly to Parquet."""
        extractor = GraphFeatureExtractor()
        df_feat = extractor.extract_features({
            "transactions": self.mock_tx,
            "transaction_inputs": self.mock_in,
            "transaction_outputs": self.mock_out
        })

        self.assertEqual(len(df_feat), 3)
        expected_cols = [
            "transaction_id",
            "graph_fan_in",
            "graph_fan_out",
            "graph_unique_in_addrs",
            "graph_unique_out_addrs",
            "hist_in_mean_neighbor_degree",
            "hist_out_mean_neighbor_degree",
            "hist_component_size",
            "hist_address_reuse_ratio",
            "hist_cluster_id",
            "hist_cluster_size",
            "hist_cluster_tx_count"
        ]
        for col in expected_cols:
            self.assertIn(col, df_feat.columns, f"Column {col} must be present in graph features.")

        extractor.export_graph_features(df_feat, self.temp_dir)
        exported_file = os.path.join(self.temp_dir, "graph_features.parquet")
        self.assertTrue(os.path.exists(exported_file))


if __name__ == "__main__":
    unittest.main()

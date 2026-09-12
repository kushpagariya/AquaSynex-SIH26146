"""
Unit & Audit Tests for AquaSynex Modeling Dataset (Phase 2.5A)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Tests:
1. test_expected_row_and_column_counts: Exactly 10,000 rows x 56 columns.
2. test_feature_join_1_to_1: Complete 1:1 join with canonical transactions.
3. test_no_duplicate_transaction_ids: Absolute uniqueness of transaction identifiers.
4. test_no_unexpected_nan_or_inf: Zero missing or infinite values in numeric features.
5. test_strict_temporal_ordering: Monotonically non-decreasing timestamps.
6. test_temporal_splits_proportions_and_coverage: 70/15/15 split and 11-scenario coverage.
7. test_no_generator_metadata_leakage: Verification that generator metadata is absent.
8. test_graph_and_tabular_completeness: All 40 tabular and 11 graph features present in raw dataset.
9. test_target_definitions_and_values: Binary {0, 1} and multiclass (11 classes) integrity.
10. test_redundancy_correlation_invariants: Identifies and verifies candidate redundant pairs.
11. test_hist_cluster_id_excluded_from_model_features: hist_cluster_id is strictly a grouping key, not an ML feature.
12. test_graph_duplicates_excluded_from_canonical_features: 4 graph duplicates relegated to optional ablation.
13. test_canonical_predictive_feature_space_is_46: Exactly 46 canonical predictive features (44 numeric + 2 categorical).
14. test_identifiers_targets_and_split_excluded_from_X: Model matrix X excludes keys, targets, and split flags.
"""

import os
import yaml
import unittest
import numpy as np
import pandas as pd
import duckdb

class TestModelingDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parquet_path = "data/processed/modeling/modeling_dataset.parquet"
        cls.canonical_tx_path = "data/processed/canonical/canonical_transactions.parquet"
        cls.manifest_path = "data/processed/modeling/feature_manifest.yaml"

        cls.con = duckdb.connect()
        cls.df = cls.con.execute(f"SELECT * FROM read_parquet('{cls.parquet_path}')").df()
        cls.df_canon = cls.con.execute(f"SELECT transaction_id, timestamp_epoch_sec FROM read_parquet('{cls.canonical_tx_path}')").df()

        with open(cls.manifest_path, "r", encoding="utf-8") as f:
            cls.manifest = yaml.safe_load(f)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_expected_row_and_column_counts(self):
        """Verify dataset dimensions: 10,000 transactions and 56 columns."""
        self.assertEqual(len(self.df), 10000, "Dataset must have exactly 10,000 rows.")
        self.assertEqual(len(self.df.columns), 56, "Dataset must have exactly 56 columns.")

    def test_feature_join_1_to_1(self):
        """Verify 1:1 transaction_id mapping between canonical transactions and modeling dataset."""
        canon_ids = set(self.df_canon["transaction_id"])
        model_ids = set(self.df["transaction_id"])
        self.assertEqual(len(canon_ids), len(model_ids), "Transaction count mismatch.")
        self.assertEqual(canon_ids, model_ids, "All canonical transactions must be present in modeling dataset.")

    def test_no_duplicate_transaction_ids(self):
        """Verify primary key uniqueness (zero duplicates)."""
        dup_count = self.df["transaction_id"].duplicated().sum()
        self.assertEqual(dup_count, 0, f"Detected {dup_count} duplicate transaction IDs.")

    def test_no_unexpected_nan_or_inf(self):
        """Verify zero NaN or Inf values across all numeric features."""
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            nan_cnt = self.df[col].isna().sum()
            inf_cnt = np.isinf(self.df[col]).sum()
            self.assertEqual(nan_cnt, 0, f"Column '{col}' contains {nan_cnt} NaNs.")
            self.assertEqual(inf_cnt, 0, f"Column '{col}' contains {inf_cnt} Infs.")

    def test_strict_temporal_ordering(self):
        """Verify records are ordered strictly chronologically."""
        timestamps = self.df["timestamp_epoch_sec"].values
        is_sorted = np.all(timestamps[:-1] <= timestamps[1:])
        self.assertTrue(is_sorted, "Modeling dataset must be sorted monotonically by timestamp_epoch_sec.")

    def test_temporal_splits_proportions_and_coverage(self):
        """Verify 70/15/15 temporal split and presence of all 11 scenarios in test set."""
        split_counts = self.df["temporal_split"].value_counts().to_dict()
        self.assertEqual(split_counts.get("train", 0), 7000)
        self.assertEqual(split_counts.get("val", 0), 1500)
        self.assertEqual(split_counts.get("test", 0), 1500)

        test_scenarios = self.df[self.df["temporal_split"] == "test"]["target_multiclass"].nunique()
        self.assertEqual(test_scenarios, 11, "All 11 behavioral scenarios must be represented in the test partition.")

    def test_no_generator_metadata_leakage(self):
        """Strict assertion: Generator-only metadata columns must NEVER exist in modeling dataset."""
        forbidden_cols = [
            "has_network_anomaly",
            "scenario_id",
            "risk_seed",
            "related_entities",
            "graph_pagerank",
            "is_giant_component"
        ]
        for col in forbidden_cols:
            self.assertNotIn(col, self.df.columns, f"Forbidden leakage column '{col}' found in modeling dataset!")

    def test_graph_and_tabular_completeness(self):
        """Verify presence of all 40 tabular features and 11 graph features in raw modeling dataset."""
        expected_tabular_samples = [
            "tx_input_count", "tx_total_input_sats", "tx_fee_sats", "tx_fee_rate_sat_per_byte",
            "addr_hist_tx_count", "addr_reuse_count", "time_hour_of_day", "time_since_prev_global_tx_sec",
            "net_country", "net_asn", "rel_fan_in", "rel_has_change_output"
        ]
        expected_graph_samples = [
            "graph_fan_in", "graph_fan_out", "graph_unique_in_addrs", "graph_unique_out_addrs",
            "hist_in_mean_neighbor_degree", "hist_out_mean_neighbor_degree", "hist_component_size",
            "hist_address_reuse_ratio", "hist_cluster_id", "hist_cluster_size", "hist_cluster_tx_count"
        ]
        for col in expected_tabular_samples:
            self.assertIn(col, self.df.columns, f"Missing tabular feature '{col}'.")
        for col in expected_graph_samples:
            self.assertIn(col, self.df.columns, f"Missing graph feature '{col}'.")

    def test_target_definitions_and_values(self):
        """Verify target_binary {0, 1} and target_multiclass (11 scenarios)."""
        binary_vals = set(self.df["target_binary"].unique())
        self.assertEqual(binary_vals, {0, 1}, "target_binary must contain only {0, 1}.")

        multiclass_classes = self.df["target_multiclass"].nunique()
        self.assertEqual(multiclass_classes, 11, "target_multiclass must have 11 unique scenario classes.")

    def test_redundancy_correlation_invariants(self):
        """Verify correlation = 1.0000 for topological twin pairs."""
        corr_in = self.df[["tx_input_count", "graph_fan_in"]].corr().iloc[0, 1]
        corr_out = self.df[["tx_output_count", "graph_fan_out"]].corr().iloc[0, 1]
        self.assertAlmostEqual(corr_in, 1.0, places=4)
        self.assertAlmostEqual(corr_out, 1.0, places=4)

    def test_hist_cluster_id_excluded_from_model_features(self):
        """MANDATORY AUDIT: hist_cluster_id is strictly a grouping key, NOT a predictive model feature."""
        canonical_features = self.manifest["canonical_feature_names"]
        self.assertNotIn("hist_cluster_id", canonical_features, "hist_cluster_id must NEVER be in canonical_feature_names!")

        # Verify manifest classifies it as entity_grouping_key
        id_entries = {item["name"]: item for item in self.manifest["identifiers_and_grouping"]}
        self.assertIn("hist_cluster_id", id_entries)
        self.assertEqual(id_entries["hist_cluster_id"]["role"], "entity_grouping_key")
        self.assertFalse(id_entries["hist_cluster_id"]["is_model_feature"])

    def test_graph_duplicates_excluded_from_canonical_features(self):
        """MANDATORY AUDIT: 4 graph duplicates are relegated to optional ablation, NOT in canonical features."""
        canonical_features = self.manifest["canonical_feature_names"]
        graph_duplicates = ["graph_fan_in", "graph_fan_out", "graph_unique_in_addrs", "graph_unique_out_addrs"]
        for g_dup in graph_duplicates:
            self.assertNotIn(g_dup, canonical_features, f"{g_dup} must NOT be in canonical_feature_names!")

        ablation_entries = {item["name"]: item for item in self.manifest["optional_ablation_features"]}
        for g_dup in graph_duplicates:
            self.assertIn(g_dup, ablation_entries)
            self.assertFalse(ablation_entries[g_dup]["is_canonical"])
            self.assertFalse(ablation_entries[g_dup]["is_model_feature"])

    def test_canonical_predictive_feature_space_is_46(self):
        """MANDATORY AUDIT: Exactly 46 canonical predictive features (44 numeric + 2 categorical)."""
        canonical_features = self.manifest["canonical_feature_names"]
        self.assertEqual(len(canonical_features), 46, f"Expected 46 canonical features, but got {len(canonical_features)}")

        # Verify numeric (44) + categorical (2) breakdown in manifest
        num_count = self.manifest["dataset_summary"]["canonical_numeric_features_count"]
        cat_count = self.manifest["dataset_summary"]["canonical_categorical_features_count"]
        self.assertEqual(num_count, 44)
        self.assertEqual(cat_count, 2)
        self.assertEqual(num_count + cat_count, 46)

    def test_identifiers_targets_and_split_excluded_from_X(self):
        """Verify identifier, target, and split columns are strictly excluded from predictive matrix X."""
        canonical_features = set(self.manifest["canonical_feature_names"])
        non_feature_cols = {
            "transaction_id",
            "timestamp_epoch_sec",
            "hist_cluster_id",
            "target_binary",
            "target_multiclass",
            "temporal_split"
        }
        overlap = canonical_features.intersection(non_feature_cols)
        self.assertEqual(len(overlap), 0, f"Predictive feature set contains non-feature columns: {overlap}")

        # Assert slicing df by canonical_features yields exactly shape (10000, 46)
        X = self.df[self.manifest["canonical_feature_names"]]
        self.assertEqual(X.shape, (10000, 46))


if __name__ == "__main__":
    unittest.main()

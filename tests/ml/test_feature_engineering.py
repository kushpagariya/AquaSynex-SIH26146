"""
Unit & Integration Tests for AquaSynex Feature Engineering Pipeline (Phase 2.3)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
"""

import os
import shutil
import tempfile
import unittest
import pandas as pd
import numpy as np

from ml.feature_engineering.transaction_features import TransactionFeatureExtractor
from ml.feature_engineering.address_features import AddressFeatureExtractor
from ml.feature_engineering.temporal_features import TemporalFeatureExtractor
from ml.feature_engineering.network_features import NetworkFeatureExtractor
from ml.feature_engineering.feature_pipeline import FeatureEngineeringPipeline

class TestFeatureEngineering(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tx1 = "1" * 64
        self.tx2 = "2" * 64
        self.tx3 = "3" * 64

        self.mock_transactions = pd.DataFrame([
            {
                "transaction_id": self.tx1,
                "dataset_id": "test",
                "timestamp": "2026-01-01T12:00:00Z",
                "timestamp_epoch_sec": 1767268800,
                "input_count": 1,
                "output_count": 2,
                "total_input_value_satoshi": 100_000_000,
                "total_output_value_satoshi": 99_990_000,
                "fee_satoshi": 10_000,
                "transaction_size_bytes": 226
            },
            {
                "transaction_id": self.tx2,
                "dataset_id": "test",
                "timestamp": "2026-01-01T12:00:30Z",
                "timestamp_epoch_sec": 1767268830,  # 30 seconds later
                "input_count": 2,
                "output_count": 1,
                "total_input_value_satoshi": 50_000_000,
                "total_output_value_satoshi": 49_995_000,
                "fee_satoshi": 5_000,
                "transaction_size_bytes": 374
            },
            {
                "transaction_id": self.tx3,
                "dataset_id": "test",
                "timestamp": "2026-01-01T12:05:00Z",
                "timestamp_epoch_sec": 1767269100,  # 300 seconds later
                "input_count": 1,
                "output_count": 2,
                "total_input_value_satoshi": 80_000_000,
                "total_output_value_satoshi": 79_992_000,
                "fee_satoshi": 8_000,
                "transaction_size_bytes": 226
            }
        ])

        self.mock_inputs = pd.DataFrame([
            {"transaction_id": self.tx1, "input_index": 0, "input_address": "addr_alice", "input_value_satoshi": 100_000_000},
            {"transaction_id": self.tx2, "input_index": 0, "input_address": "addr_alice", "input_value_satoshi": 30_000_000},
            {"transaction_id": self.tx2, "input_index": 1, "input_address": "addr_carol", "input_value_satoshi": 20_000_000},
            {"transaction_id": self.tx3, "input_index": 0, "input_address": "addr_bob", "input_value_satoshi": 80_000_000}
        ])

        self.mock_outputs = pd.DataFrame([
            {"transaction_id": self.tx1, "output_index": 0, "output_address": "addr_bob", "output_value_satoshi": 40_000_000, "is_change": False},
            {"transaction_id": self.tx1, "output_index": 1, "output_address": "addr_alice", "output_value_satoshi": 59_990_000, "is_change": True},
            {"transaction_id": self.tx2, "output_index": 0, "output_address": "addr_dave", "output_value_satoshi": 49_995_000, "is_change": False},
            {"transaction_id": self.tx3, "output_index": 0, "output_address": "addr_alice", "output_value_satoshi": 50_000_000, "is_change": False},
            {"transaction_id": self.tx3, "output_index": 1, "output_address": "addr_bob", "output_value_satoshi": 29_992_000, "is_change": True}
        ])

        self.mock_network = pd.DataFrame([
            {"transaction_id": self.tx1, "timestamp_epoch_sec": 1767268800, "src_ip": "1.1.1.1", "src_port": 54321, "dst_ip": "10.0.0.1", "dst_port": 8333, "asn": 15169, "country": "US"},
            {"transaction_id": self.tx2, "timestamp_epoch_sec": 1767268830, "src_ip": "2.2.2.2", "src_port": 54322, "dst_ip": "10.0.0.1", "dst_port": 8333, "asn": 16509, "country": "DE"},
            {"transaction_id": self.tx3, "timestamp_epoch_sec": 1767269100, "src_ip": "3.3.3.3", "src_port": 54323, "dst_ip": "10.0.0.1", "dst_port": 18333, "asn": 13335, "country": "SG"}
        ])

        self.canonical_data = {
            "transactions": self.mock_transactions,
            "transaction_inputs": self.mock_inputs,
            "transaction_outputs": self.mock_outputs,
            "network_events": self.mock_network
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_transaction_feature_extraction(self):
        extractor = TransactionFeatureExtractor()
        df = extractor.extract(self.canonical_data)

        self.assertEqual(len(df), 3)
        row1 = df[df["transaction_id"] == self.tx1].iloc[0]
        self.assertEqual(row1["tx_input_count"], 1)
        self.assertEqual(row1["tx_output_count"], 2)
        self.assertAlmostEqual(row1["tx_input_output_ratio"], 0.5)
        self.assertEqual(row1["tx_fee_sats"], 10_000)
        self.assertAlmostEqual(row1["tx_fee_rate_sat_per_byte"], 10_000 / 226, places=4)
        self.assertAlmostEqual(row1["tx_value_balance_ratio"], 99_990_000 / 100_000_000, places=4)
        self.assertEqual(row1["tx_max_input_value_sats"], 100_000_000)
        self.assertEqual(row1["tx_max_output_value_sats"], 59_990_000)

    def test_address_features_strict_temporal_lookback(self):
        """
        Verify that for Alice:
        In tx1 (first occurrence): hist_tx_count == 0 (no future knowledge of tx2).
        In tx2 (second occurrence): hist_tx_count == 1 (sees tx1).
        """
        extractor = AddressFeatureExtractor()
        df = extractor.extract(self.canonical_data)

        row1 = df[df["transaction_id"] == self.tx1].iloc[0]
        self.assertEqual(row1["addr_hist_tx_count"], 0)
        self.assertEqual(row1["addr_hist_total_sent_sats"], 0)
        self.assertEqual(row1["addr_reuse_count"], 0)

        row2 = df[df["transaction_id"] == self.tx2].iloc[0]
        self.assertEqual(row2["addr_hist_tx_count"], 1)
        self.assertEqual(row2["addr_hist_total_sent_sats"], 99_990_000)
        self.assertEqual(row2["addr_reuse_count"], 1)

    def test_temporal_features_rolling_windows(self):
        extractor = TemporalFeatureExtractor()
        df = extractor.extract(self.canonical_data)

        # tx1 at T=0
        row1 = df[df["transaction_id"] == self.tx1].iloc[0]
        self.assertEqual(row1["time_since_prev_global_tx_sec"], 0.0)
        self.assertEqual(row1["time_txs_last_1m"], 0)

        # tx2 at T=30s (30s after tx1)
        row2 = df[df["transaction_id"] == self.tx2].iloc[0]
        self.assertEqual(row2["time_since_prev_global_tx_sec"], 30.0)
        self.assertEqual(row2["time_txs_last_1m"], 1)  # tx1 was 30s ago
        self.assertEqual(row2["time_since_prev_addr_tx_sec"], 30.0)  # Alice spent 30s ago

        # tx3 at T=300s (270s after tx2)
        row3 = df[df["transaction_id"] == self.tx3].iloc[0]
        self.assertEqual(row3["time_since_prev_global_tx_sec"], 270.0)
        self.assertEqual(row3["time_txs_last_1m"], 0)  # no tx in last 60s
        self.assertEqual(row3["time_txs_last_5m"], 2)  # tx1 and tx2 within last 300s

    def test_network_features_extraction(self):
        extractor = NetworkFeatureExtractor()
        df = extractor.extract(self.canonical_data)

        row1 = df[df["transaction_id"] == self.tx1].iloc[0]
        self.assertEqual(row1["net_src_port"], 54321)
        self.assertEqual(row1["net_dst_port"], 8333)
        self.assertEqual(row1["net_is_standard_bitcoin_port"], 1)
        self.assertEqual(row1["net_asn"], 15169)

        row3 = df[df["transaction_id"] == self.tx3].iloc[0]
        self.assertEqual(row3["net_dst_port"], 18333)
        self.assertEqual(row3["net_is_standard_bitcoin_port"], 0)

    def test_end_to_end_feature_pipeline(self):
        pipeline = FeatureEngineeringPipeline(version="test_v1")
        matrix, report = pipeline.build_feature_matrix(self.canonical_data)

        self.assertEqual(len(matrix), 3)
        self.assertTrue(report["is_clean"])
        self.assertEqual(len(report["nan_counts"]), 0)
        self.assertEqual(len(report["inf_counts"]), 0)
        self.assertEqual(len(report["leakage_columns_found"]), 0)

        # Verify relational features
        self.assertIn("rel_fan_in", matrix.columns)
        self.assertIn("rel_fan_out", matrix.columns)
        self.assertIn("rel_has_change_output", matrix.columns)
        self.assertIn("rel_change_value_ratio", matrix.columns)

        # Export test
        out_file = os.path.join(self.temp_dir, "test_features.parquet")
        pipeline.export_feature_matrix(matrix, self.temp_dir, filename="test_features.parquet")
        self.assertTrue(os.path.exists(out_file))

if __name__ == "__main__":
    unittest.main()

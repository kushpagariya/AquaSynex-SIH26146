"""
Unit & Integration Tests for AquaSynex Data Pipeline (Phase 2.2)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic
"""

import os
import shutil
import tempfile
import unittest
import pandas as pd
import numpy as np

from ml.data_pipeline.ingestion import DataIngestionEngine, GENERATOR_METADATA_COLUMNS
from ml.data_pipeline.validation import DataValidationEngine, ValidationResult
from ml.data_pipeline.cleaning import DataCleaningEngine
from ml.data_pipeline.normalization import DataNormalizationEngine

class TestDataPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_txid = "a" * 64

        self.mock_transactions = pd.DataFrame([{
            "txid": self.sample_txid,
            "timestamp": "2026-01-01T12:00:00Z",
            "input_count": 1,
            "output_count": 2,
            "total_input_value_satoshi": 100_000_000,
            "total_output_value_satoshi": 99_990_000,
            "fee_satoshi": 10_000,
            "transaction_size_bytes": 226,
            "scenario_id": "normal_001"  # Leaked metadata to test quarantine
        }])

        self.mock_inputs = pd.DataFrame([{
            "txid": self.sample_txid,
            "input_index": 0,
            "address": "bc1qtestaddress1234567890",
            "amount_satoshi": 100_000_000
        }])

        self.mock_outputs = pd.DataFrame([
            {
                "txid": self.sample_txid,
                "output_index": 0,
                "address": "bc1qrecipaddress123456789",
                "amount_satoshi": 50_000_000,
                "is_change": False
            },
            {
                "txid": self.sample_txid,
                "output_index": 1,
                "address": "bc1qchangeaddress12345678",
                "amount_satoshi": 49_990_000,
                "is_change": True
            }
        ])

        self.mock_network = pd.DataFrame([{
            "event_id": f"EVT_{self.sample_txid[:16]}",
            "txid": self.sample_txid,
            "timestamp": "2026-01-01T12:00:00Z",
            "src_ip": "192.168.1.1",
            "src_port": 50000,
            "dst_ip": "10.0.0.1",
            "dst_port": 8333,
            "country": "US",
            "asn": 15169,
            "has_network_anomaly": True  # Leaked generator flag to test quarantine
        }])

        self.mock_labels = pd.DataFrame([{
            "txid": self.sample_txid,
            "entity_id": "ENT_001",
            "scenario_id": "normal_001",
            "behavior_type": "normal",
            "ground_truth_label": 0,
            "has_network_anomaly": False
        }])

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ingestion_quarantines_metadata(self):
        engine = DataIngestionEngine()
        raw = {
            "transactions": self.mock_transactions,
            "transaction_inputs": self.mock_inputs,
            "transaction_outputs": self.mock_outputs,
            "network_events": self.mock_network,
            "labels": self.mock_labels
        }
        observational, quarantined = engine._quarantine_and_split(raw)

        # Assert generator columns removed from observational data
        self.assertNotIn("scenario_id", observational["transactions"].columns)
        self.assertNotIn("has_network_anomaly", observational["network_events"].columns)

        # Assert metadata safely captured in quarantined dict
        self.assertIn("labels", quarantined)
        self.assertIn("transactions_generator_meta", quarantined)
        self.assertIn("network_events_generator_meta", quarantined)

    def test_validation_engine_success(self):
        validator = DataValidationEngine()
        observational = {
            "transactions": self.mock_transactions.drop(columns=["scenario_id"]),
            "transaction_inputs": self.mock_inputs,
            "transaction_outputs": self.mock_outputs,
            "network_events": self.mock_network.drop(columns=["has_network_anomaly"])
        }
        result = validator.validate(observational)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_validation_detects_conservation_violation(self):
        validator = DataValidationEngine()
        corrupt_tx = self.mock_transactions.drop(columns=["scenario_id"]).copy()
        corrupt_tx["total_input_value_satoshi"] = 50_000_000  # Violates in == out + fee
        observational = {
            "transactions": corrupt_tx,
            "transaction_inputs": self.mock_inputs,
            "transaction_outputs": self.mock_outputs
        }
        result = validator.validate(observational)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("conservation" in e.lower() for e in result.errors))

    def test_validation_detects_invalid_hex(self):
        validator = DataValidationEngine()
        corrupt_tx = self.mock_transactions.drop(columns=["scenario_id"]).copy()
        corrupt_tx["txid"] = "invalid_txid_123"
        observational = {"transactions": corrupt_tx}
        result = validator.validate(observational)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("invalid 64-char hex" in e.lower() for e in result.errors))

    def test_cleaning_engine_deduplication(self):
        cleaner = DataCleaningEngine()
        # Duplicate transaction row
        dup_tx = pd.concat([self.mock_transactions, self.mock_transactions], ignore_index=True)
        cleaned = cleaner.clean({"transactions": dup_tx})
        self.assertEqual(len(cleaned["transactions"]), 1)
        self.assertEqual(cleaner.cleaning_stats["dropped_duplicates"]["transactions"], 1)

    def test_normalization_engine_fields(self):
        normalizer = DataNormalizationEngine(dataset_id="test_run")
        observational = {
            "transactions": self.mock_transactions.drop(columns=["scenario_id"]),
            "transaction_inputs": self.mock_inputs,
            "transaction_outputs": self.mock_outputs,
            "network_events": self.mock_network.drop(columns=["has_network_anomaly"])
        }
        canonical = normalizer.normalize(observational)

        tx = canonical["transactions"].iloc[0]
        self.assertEqual(tx["transaction_id"], self.sample_txid)
        self.assertEqual(tx["dataset_id"], "test_run")
        self.assertAlmostEqual(tx["total_input_btc"], 1.0)
        self.assertAlmostEqual(tx["total_output_btc"], 0.9999)
        self.assertAlmostEqual(tx["fee_btc"], 0.0001)
        self.assertGreater(tx["timestamp_epoch_sec"], 0)
        self.assertAlmostEqual(tx["value_balance_ratio"], 0.9999, places=4)

        # Check input surrogate key
        in_row = canonical["transaction_inputs"].iloc[0]
        self.assertEqual(in_row["input_id"], f"{self.sample_txid}:0")
        self.assertAlmostEqual(in_row["input_value_btc"], 1.0)

        # Check output surrogate keys
        out_rows = canonical["transaction_outputs"]
        self.assertEqual(len(out_rows), 2)
        self.assertEqual(out_rows.iloc[0]["output_id"], f"{self.sample_txid}:0")
        self.assertEqual(out_rows.iloc[1]["output_id"], f"{self.sample_txid}:1")

    def test_parquet_export_and_duckdb_registration(self):
        normalizer = DataNormalizationEngine(dataset_id="test_export")
        observational = {
            "transactions": self.mock_transactions.drop(columns=["scenario_id"]),
            "transaction_inputs": self.mock_inputs,
            "transaction_outputs": self.mock_outputs,
            "network_events": self.mock_network.drop(columns=["has_network_anomaly"])
        }
        canonical = normalizer.normalize(observational)

        # Test export
        out_dir = os.path.join(self.temp_dir, "parquet_out")
        normalizer.export_to_parquet(canonical, out_dir)
        self.assertTrue(os.path.exists(os.path.join(out_dir, "canonical_transactions.parquet")))

        # Test duckdb registration
        db_path = os.path.join(self.temp_dir, "test.duckdb")
        normalizer.register_in_duckdb(canonical, db_path)
        self.assertTrue(os.path.exists(db_path))

if __name__ == "__main__":
    unittest.main()

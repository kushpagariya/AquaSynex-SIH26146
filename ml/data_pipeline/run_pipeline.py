"""
AquaSynex — End-to-End Data Pipeline Runner (Phase 2.2)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Executes the four-stage data pipeline:
1. Ingestion & Generator Metadata Quarantine
2. Pre-cleaning Validation
3. Data Cleaning & Deduplication
4. Canonical Normalization & Parquet/DuckDB Export
"""

import os
import sys
import argparse
import time
from typing import Dict, Any

from ml.data_pipeline.ingestion import DataIngestionEngine
from ml.data_pipeline.validation import DataValidationEngine
from ml.data_pipeline.cleaning import DataCleaningEngine
from ml.data_pipeline.normalization import DataNormalizationEngine

def run_pipeline(
    input_dir: str,
    output_dir: str,
    db_path: str = "database/aquasynex.duckdb",
    dataset_id: str = "synthetic_dev"
) -> Dict[str, Any]:
    start_time = time.time()
    print("=" * 60, flush=True)
    print(f"[*] AquaSynex Data Pipeline (Phase 2.2) — Dataset: {dataset_id}", flush=True)
    print(f"[*] Input Directory: {input_dir}", flush=True)
    print(f"[*] Output Directory: {output_dir}", flush=True)
    print("=" * 60, flush=True)

    # 1. Ingestion
    print("\n[Stage 1/4] Ingesting and Quarantining Generator Metadata...", flush=True)
    ingestion = DataIngestionEngine(dataset_id=dataset_id)
    observational_data, quarantined_metadata = ingestion.load_from_parquet_dir(input_dir)

    print(f"  [+] Ingested Observational Tables:")
    for k, df in observational_data.items():
        print(f"      - {k:<22}: {len(df):>7,} rows")
    print(f"  [+] Quarantined Ground-Truth & Metadata Tables:")
    for k, df in quarantined_metadata.items():
        print(f"      - {k:<22}: {len(df):>7,} rows")

    # 2. Validation
    print("\n[Stage 2/4] Executing Pre-cleaning Validation...", flush=True)
    validator = DataValidationEngine()
    val_result = validator.validate(observational_data)

    if val_result.is_valid:
        print("  [+] Pre-cleaning Validation PASSED (0 critical integrity errors).")
    else:
        print(f"  [!] Pre-cleaning Validation encountered {len(val_result.errors)} errors:")
        for err in val_result.errors[:5]:
            print(f"      - {err}")
        if len(val_result.errors) > 5:
            print(f"      ... and {len(val_result.errors) - 5} more.")

    # 3. Cleaning
    print("\n[Stage 3/4] Cleaning & Deduplicating Observational Data...", flush=True)
    cleaner = DataCleaningEngine()
    cleaned_data = cleaner.clean(observational_data)
    print(f"  [+] Deduplication & Standardization Stats:")
    for entity, drops in cleaner.cleaning_stats.get("dropped_duplicates", {}).items():
        print(f"      - Dropped duplicates ({entity}): {drops}")

    # 4. Normalization
    print("\n[Stage 4/4] Normalizing into Canonical Schema & Scaling Features...", flush=True)
    normalizer = DataNormalizationEngine(dataset_id=dataset_id)
    canonical_data = normalizer.normalize(cleaned_data)

    # Post-normalization validation
    post_val = validator.validate(canonical_data)
    if post_val.is_valid:
        print("  [+] Canonical Schema Validation PASSED (100% compliant).")
    else:
        print(f"  [!] Post-normalization warnings: {len(post_val.warnings)}")

    # 5. Export Parquet & DuckDB
    print(f"\n[*] Exporting Canonical Parquet Files to: {output_dir}...", flush=True)
    normalizer.export_to_parquet(canonical_data, output_dir)
    for k, df in canonical_data.items():
        print(f"  [+] Saved canonical_{k}.parquet: {len(df):,} rows")

    if db_path:
        print(f"\n[*] Registering Canonical Tables in DuckDB: {db_path}...", flush=True)
        normalizer.register_in_duckdb(canonical_data, db_path, table_prefix="canonical_")
        print("  [+] Registered: canonical_transactions, canonical_transaction_inputs, canonical_transaction_outputs, canonical_network_events")

    elapsed = time.time() - start_time
    print("\n" + "=" * 60, flush=True)
    print(f"[+] Pipeline finished successfully in {elapsed:.2f} seconds!", flush=True)
    print("=" * 60 + "\n", flush=True)

    return {
        "status": "SUCCESS" if post_val.is_valid else "WARNING",
        "elapsed_seconds": elapsed,
        "canonical_transactions": len(canonical_data.get("transactions", [])),
        "canonical_inputs": len(canonical_data.get("transaction_inputs", [])),
        "canonical_outputs": len(canonical_data.get("transaction_outputs", [])),
        "canonical_events": len(canonical_data.get("network_events", [])),
        "quarantined_tables": list(quarantined_metadata.keys())
    }

def main():
    parser = argparse.ArgumentParser(description="AquaSynex Phase 2.2 Data Pipeline Runner")
    parser.add_argument("--input", type=str, default="data/sample/", help="Input raw/sample dataset folder")
    parser.add_argument("--output", type=str, default="data/processed/canonical/", help="Output canonical Parquet folder")
    parser.add_argument("--db-path", type=str, default="database/aquasynex.duckdb", help="Target DuckDB database path")
    parser.add_argument("--dataset-id", type=str, default="synthetic_dev", help="Dataset identifier tag")

    args = parser.parse_args()
    run_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        db_path=args.db_path,
        dataset_id=args.dataset_id
    )

if __name__ == "__main__":
    main()

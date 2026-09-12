#!/usr/bin/env python3
"""
AquaSynex — Development DuckDB Loader for SIH26146
AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Loads generated Parquet dataset tables into the analytical DuckDB database:
database/aquasynex.duckdb
"""

import os
import sys
import argparse
import duckdb

def load_dataset(data_dir: str, db_path: str):
    print(f"[*] Connecting to DuckDB: {db_path}...", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    
    con = duckdb.connect(db_path)
    
    tables_to_load = [
        ("transactions", "transactions.parquet"),
        ("transaction_inputs", "transaction_inputs.parquet"),
        ("transaction_outputs", "transaction_outputs.parquet"),
        ("network_events", "network_events.parquet"),
        ("entities", "entities.parquet"),
        ("labels", "labels.parquet"),
        ("sih_transactions", "sih_transactions.parquet")
    ]
    
    print(f"[*] Ingesting Parquet datasets from {data_dir}...", flush=True)
    results = {}
    for table_name, file_name in tables_to_load:
        file_path = os.path.join(data_dir, file_name)
        if not os.path.exists(file_path):
            print(f"  [!] Warning: {file_name} not found in {data_dir}. Skipping {table_name}.", flush=True)
            continue
            
        clean_path = file_path.replace("\\", "/")
        # Analytical simple table creation from Parquet (DuckDB native zero-copy read)
        con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM '{clean_path}'")
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        results[table_name] = count
        print(f"  [+] Loaded table '{table_name}': {count:,} rows", flush=True)

    # Verification query: count benign vs suspicious
    if "labels" in results:
        res = con.execute("""
            SELECT 
                behavior_type,
                ground_truth_label,
                COUNT(*) as count
            FROM labels
            GROUP BY behavior_type, ground_truth_label
            ORDER BY count DESC
        """).fetchall()
        print("\n[*] Scenario Distribution in DuckDB:", flush=True)
        for row in res:
            lbl_str = "Benign (0)" if row[1] == 0 else "Suspicious (1)"
            print(f"    - {row[0]:<25}: {row[2]:>6,} ({lbl_str})", flush=True)

    con.close()
    print(f"\n[+] Ingestion successfully completed! Database written to: {db_path}", flush=True)
    return results

def main():
    parser = argparse.ArgumentParser(description="Load Synthetic Bitcoin Dataset into DuckDB")
    parser.add_argument("--data-dir", type=str, default="data/sample/", help="Directory containing Parquet files")
    parser.add_argument("--db-path", type=str, default="database/aquasynex.duckdb", help="Target DuckDB file path")
    
    args = parser.parse_args()
    load_dataset(data_dir=args.data_dir, db_path=args.db_path)

if __name__ == "__main__":
    main()

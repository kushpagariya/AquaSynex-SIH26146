#!/usr/bin/env python3
"""AquaSynex TraceGrid — Scalability & Performance Benchmark Suite.

Benchmarks synthetic dataset generation, DuckDB ingestion, table population,
and API query performance (pagination, filtering, network aggregation, graph capping).
Verifies that no query or API dumps unpaginated large datasets to clients.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import duckdb

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.db.migrations import run_migrations
from backend.services.dataset_service import DatasetService
from backend.services.network_service import NetworkService
from backend.services.transaction_service import TransactionService
from backend.services.graph_service import GraphService


class BenchmarkRunner:
    def __init__(self, csv_path: str, dataset_name: str = "Benchmark-Dataset"):
        self.csv_path = Path(csv_path).resolve()
        self.dataset_name = dataset_name
        self.dataset_id = f"bench_{int(time.time())}"
        self.results: Dict[str, Any] = {
            "dataset_file": str(self.csv_path),
            "file_size_bytes": os.path.getsize(self.csv_path),
            "file_size_mb": round(os.path.getsize(self.csv_path) / (1024 * 1024), 2),
            "ingestion": {},
            "table_counts": {},
            "query_latencies_ms": {},
            "scalability_invariants": {},
            "status": "pending",
        }

    def run_all(self) -> Dict[str, Any]:
        print(f"[*] Starting benchmark on: {self.csv_path} ({self.results['file_size_mb']} MB)", flush=True)

        # 1. Initialize isolated DuckDB in-memory database with production migrations
        conn = duckdb.connect(":memory:")
        run_migrations(conn)

        # 2. Benchmark Ingestion via DatasetService
        print("[*] Ingesting CSV dataset into DuckDB via DatasetService...", flush=True)
        ds_svc = DatasetService(conn)

        # Register dataset record
        conn.execute(
            """
            INSERT INTO datasets (dataset_id, name, file_name, file_path, format, size_bytes, uploaded_at, status)
            VALUES (?, ?, ?, ?, 'csv', ?, current_timestamp, 'processing')
            """,
            [self.dataset_id, self.dataset_name, self.csv_path.name, str(self.csv_path), self.results["file_size_bytes"]],
        )

        t0 = time.time()
        ds_svc._ingest_file(self.dataset_id, self.csv_path, "csv")
        ingest_duration = time.time() - t0

        self.results["ingestion"] = {
            "duration_sec": round(ingest_duration, 3),
            "throughput_mb_per_sec": round(self.results["file_size_mb"] / max(ingest_duration, 0.001), 2),
        }
        print(f"[+] Ingested in {ingest_duration:.3f}s ({self.results['ingestion']['throughput_mb_per_sec']} MB/s)", flush=True)

        # 3. Verify Database Row Counts
        print("[*] Verifying database row counts...", flush=True)
        counts = {}
        for tbl in ["transactions", "transaction_inputs", "transaction_outputs", "network_events", "addresses"]:
            r = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE dataset_id = ?", [self.dataset_id]).fetchone()
            counts[tbl] = r[0] if r else 0
            print(f"  - {tbl}: {counts[tbl]:,} rows")

        self.results["table_counts"] = counts
        row_count = counts.get("transactions", 0)
        self.results["ingestion"]["throughput_rows_per_sec"] = round(row_count / max(ingest_duration, 0.001), 1)

        # 4. Measure Query Latencies
        print("[*] Benchmarking representative queries...", flush=True)
        tx_svc = TransactionService(conn)
        net_svc = NetworkService(conn)
        graph_svc = GraphService(conn)

        # A. Transaction Pagination: Page 1 (pageSize 50)
        t_start = time.time()
        p1_items, p1_meta = tx_svc.list_transactions(self.dataset_id, page=1, page_size=50)
        t_p1 = (time.time() - t_start) * 1000.0
        self.results["query_latencies_ms"]["list_transactions_page_1"] = round(t_p1, 2)

        # B. Transaction Pagination: Deep Page 100 (if rows allow)
        deep_page = min(100, max(1, row_count // 50))
        t_start = time.time()
        deep_items, deep_meta = tx_svc.list_transactions(self.dataset_id, page=deep_page, page_size=50)
        t_deep = (time.time() - t_start) * 1000.0
        self.results["query_latencies_ms"][f"list_transactions_page_{deep_page}"] = round(t_deep, 2)

        # C. Point lookup by exact TXID
        sample_txid = p1_items[0]["transaction_id"] if p1_items else "none"
        t_start = time.time()
        tx_detail = tx_svc.get_transaction(sample_txid)
        t_txid = (time.time() - t_start) * 1000.0
        self.results["query_latencies_ms"]["get_transaction_detail"] = round(t_txid, 2)

        # D. Server-side IP Filter lookup
        sample_ip = conn.execute("SELECT src_ip FROM network_events WHERE dataset_id = ? LIMIT 1", [self.dataset_id]).fetchone()[0]
        t_start = time.time()
        ip_items, _ = tx_svc.list_transactions(self.dataset_id, page=1, page_size=50, ip=sample_ip)
        t_ip = (time.time() - t_start) * 1000.0
        self.results["query_latencies_ms"]["filter_transactions_by_ip"] = round(t_ip, 2)

        # E. Network Map Aggregation
        t_start = time.time()
        net_map = net_svc.get_network_map(self.dataset_id)
        t_net = (time.time() - t_start) * 1000.0
        self.results["query_latencies_ms"]["get_network_map"] = round(t_net, 2)

        # F. Address / Graph Neighborhood Subgraph
        sample_addr = p1_items[0].get("inputs", [{}])[0].get("address") if p1_items else None
        if not sample_addr:
            sample_addr_row = conn.execute("SELECT address_id FROM addresses WHERE dataset_id = ? LIMIT 1", [self.dataset_id]).fetchone()
            sample_addr = sample_addr_row[0] if sample_addr_row else "none"

        t_start = time.time()
        graph_data = graph_svc.get_address_subgraph(sample_addr, hops=2)
        t_graph = (time.time() - t_start) * 1000.0
        self.results["query_latencies_ms"]["get_address_subgraph_2hop"] = round(t_graph, 2)

        # 5. Scalability & Data Invariant Verification (Crucial Audit)
        print("[*] Auditing scalability & data invariants...", flush=True)
        invalid_asns_row = conn.execute(
            "SELECT COUNT(*) FROM network_events WHERE dataset_id = ? AND (asn IS NOT NULL AND asn <= 0)",
            [self.dataset_id],
        ).fetchone()
        invalid_asns_count = invalid_asns_row[0] if invalid_asns_row else 0
        point_asns = [p["asn"] for p in net_map.get("points", []) if p.get("asn")]
        all_point_asns_valid = all(
            isinstance(p_asn, str) and p_asn.startswith("AS") and p_asn[2:].isdigit() and int(p_asn[2:]) > 0
            for p_asn in point_asns
        )

        invariants = {
            "pagination_bounded": len(p1_items) <= 50,
            "deep_pagination_bounded": len(deep_items) <= 50,
            "ip_search_bounded": len(ip_items) <= 50,
            "network_edges_capped_at_500": len(net_map.get("edges", [])) <= 500,
            "graph_nodes_capped": len(graph_data.get("nodes", [])) <= 5000,
            "network_endpoints_aggregated": len(net_map.get("points", [])) <= (2 * counts.get("transactions", 0)),
            "all_ingested_asns_positive_or_null": (invalid_asns_count == 0),
            "all_network_point_asns_valid_positive": all_point_asns_valid,
            "client_never_receives_unpaginated_dataset": (
                len(p1_items) <= 50 and len(net_map.get("edges", [])) <= 500
            ),
        }
        self.results["scalability_invariants"] = invariants

        for name, passed in invariants.items():
            status_str = "PASS" if passed else "FAIL"
            print(f"  - [{status_str}] {name}")

        self.results["network_metrics"] = net_map.get("metrics", {})
        self.results["status"] = "success" if all(invariants.values()) else "failed"

        # Save benchmark report alongside dataset
        report_path = self.csv_path.parent / "benchmark_report.json"
        with open(report_path, "w", encoding="utf-8") as f_r:
            json.dump(self.results, f_r, indent=2)

        print(f"[+] Benchmark report saved to: {report_path}", flush=True)
        conn.close()
        return self.results


def main():
    parser = argparse.ArgumentParser(description="AquaSynex TraceGrid Performance Benchmark")
    parser.add_argument("--csv", type=str, required=True, help="Path to synthetic CSV dataset")
    parser.add_argument("--name", type=str, default="Benchmark-Dataset", help="Dataset name")

    args = parser.parse_args()
    runner = BenchmarkRunner(args.csv, args.name)
    runner.run_all()


if __name__ == "__main__":
    main()

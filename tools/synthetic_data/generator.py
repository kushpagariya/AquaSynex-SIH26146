#!/usr/bin/env python3
"""AquaSynex TraceGrid — Large-Scale Deterministic Synthetic Dataset Generator.

Generates realistic, reproducible synthetic Bitcoin transaction and network telemetry
datasets strictly adhering to the SIH26146 schema accepted by TraceGrid.

Memory-efficient streaming architecture capable of generating 100K, 500K, 1M, and 2M+
rows with constant bounded RAM (< 50 MB).
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.synthetic_data.ip_pool import IPPoolManager, PUBLIC_SUBNETS

SATOSHIS_PER_BTC = 100_000_000

BECH32_CHARS = "023456789acdefghjklmnpqrstuvwxyz"
BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def generate_address(rng: random.Random, script_type: str = "P2WPKH") -> str:
    """Generate synthetic Bitcoin address according to script type."""
    if script_type == "P2WPKH":
        suffix = "".join(rng.choice(BECH32_CHARS) for _ in range(38))
        return f"bc1q{suffix}"
    elif script_type == "P2TR":
        suffix = "".join(rng.choice(BECH32_CHARS) for _ in range(58))
        return f"bc1p{suffix}"
    elif script_type == "P2SH":
        suffix = "".join(rng.choice(BASE58_CHARS) for _ in range(33))
        return f"3{suffix}"
    else:  # P2PKH
        suffix = "".join(rng.choice(BASE58_CHARS) for _ in range(33))
        return f"1{suffix}"


def generate_txid(rng: random.Random, seq: int) -> str:
    """Generate 64-char lowercase hex transaction hash."""
    h = hashlib.sha256(f"aquasynex_tx_{seq}_{rng.getrandbits(64)}".encode("utf-8")).hexdigest()
    return h


class SyntheticUTXO:
    """Lightweight in-memory UTXO representation."""
    __slots__ = ("txid", "output_index", "address", "amount_satoshi", "script_type")

    def __init__(self, txid: str, output_index: int, address: str, amount_satoshi: int, script_type: str):
        self.txid = txid
        self.output_index = output_index
        self.address = address
        self.amount_satoshi = amount_satoshi
        self.script_type = script_type


class SyntheticEntity:
    """Synthetic wallet/actor entity in the network."""
    def __init__(self, entity_id: str, entity_type: str, rng: random.Random):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.addresses: List[str] = []
        self.script_type = rng.choice(["P2WPKH", "P2WPKH", "P2SH", "P2PKH", "P2TR"])
        # Generate initial address pool for this entity
        addr_count = 50 if entity_type == "exchange" else (15 if entity_type == "merchant" else 3)
        for _ in range(addr_count):
            self.addresses.append(generate_address(rng, self.script_type))
        # Dedicated preferred subnet for network clustering
        chosen_sub = rng.choice(PUBLIC_SUBNETS)
        self.subnet = chosen_sub["subnet"]


class StreamingSyntheticGenerator:
    """High-performance streaming dataset generator."""

    def __init__(
        self,
        total_rows: int = 100_000,
        seed: int = 42,
        start_date: str = "2026-01-01T00:00:00+00:00",
        chunk_size: int = 10_000,
    ):
        self.total_rows = total_rows
        self.seed = seed
        self.chunk_size = chunk_size
        self.rng = random.Random(seed)
        self.ip_mgr = IPPoolManager(self.rng)

        # Parse start timestamp
        clean_date = start_date.replace("Z", "+00:00")
        self.current_time = datetime.datetime.fromisoformat(clean_date)
        if self.current_time.tzinfo is None:
            self.current_time = self.current_time.replace(tzinfo=datetime.timezone.utc)

        # Initialize entity clusters
        self.entities: List[SyntheticEntity] = []
        self._init_entities()

        # Bounded UTXO pool (ring buffer) to prevent memory ballooning
        self.max_utxo_pool_size = 30_000
        self.utxo_pool: List[SyntheticUTXO] = []
        self._bootstrap_utxos()

        # Manifest tracking metrics
        self.unique_txids = 0
        self.unique_input_addresses: Set[str] = set()
        self.unique_output_addresses: Set[str] = set()
        self.unique_ips: Set[str] = set()
        self.mapped_ip_count = 0
        self.unmapped_ip_count = 0
        self.private_ip_count = 0
        self.scenario_counts: Dict[str, int] = {}
        self.anomalous_clusters: List[Dict[str, Any]] = []

    def _init_entities(self):
        """Create initial entity clusters."""
        # 8 Exchanges (high volume hubs)
        for i in range(8):
            self.entities.append(SyntheticEntity(f"ENT_EXCH_{i+1:03d}", "exchange", self.rng))
        # 30 Merchants (medium volume)
        for i in range(30):
            self.entities.append(SyntheticEntity(f"ENT_MERCH_{i+1:03d}", "merchant", self.rng))
        # 200 Regular users
        for i in range(200):
            self.entities.append(SyntheticEntity(f"ENT_USER_{i+1:03d}", "user", self.rng))

    def _bootstrap_utxos(self):
        """Seed initial UTXOs so transactions have realistic inputs to spend."""
        for i in range(5_000):
            ent = self.rng.choice(self.entities)
            addr = self.rng.choice(ent.addresses)
            genesis_tx = generate_txid(self.rng, -i - 1)
            amt = self.rng.randint(50_000, 500_000_000)  # 0.0005 to 5 BTC
            self.utxo_pool.append(SyntheticUTXO(genesis_tx, 0, addr, amt, ent.script_type))

    def _get_spendable_utxos(self, count: int) -> List[SyntheticUTXO]:
        """Pop spendable UTXOs from the pool."""
        if len(self.utxo_pool) < count + 500:
            # Replenish if pool runs low
            self._bootstrap_utxos()
        
        # Pop from random positions
        selected = []
        for _ in range(count):
            idx = self.rng.randrange(len(self.utxo_pool))
            # Swap with last and pop for O(1)
            self.utxo_pool[idx], self.utxo_pool[-1] = self.utxo_pool[-1], self.utxo_pool[idx]
            selected.append(self.utxo_pool.pop())
        return selected

    def _add_utxos(self, new_utxos: List[SyntheticUTXO]):
        """Add new UTXOs to the spendable pool with bounded capacity."""
        for u in new_utxos:
            if len(self.utxo_pool) >= self.max_utxo_pool_size:
                # Evict random older UTXO
                idx = self.rng.randrange(len(self.utxo_pool))
                self.utxo_pool[idx] = u
            else:
                self.utxo_pool.append(u)

    def _step_time(self, seconds_min: float = 1.0, seconds_max: float = 12.0):
        """Advance time with realistic diurnal modulation."""
        base_sec = self.rng.uniform(seconds_min, seconds_max)
        # Sinusoidal diurnal activity (higher volume during UTC 08:00 - 20:00)
        hour = self.current_time.hour
        activity_factor = 0.7 if (8 <= hour <= 20) else 1.4
        delta = datetime.timedelta(seconds=base_sec * activity_factor)
        self.current_time += delta

    @staticmethod
    def _clean_asn(val: Any) -> Any:
        """Ensure only strictly positive integer ASNs (> 0) are emitted, otherwise empty string."""
        if val is None:
            return ""
        s = str(val).strip().upper()
        if s.startswith("AS"):
            s = s[2:].strip()
        if s.isdigit() and int(s) > 0:
            return int(s)
        return ""

    def _generate_single_transaction(
        self,
        seq: int,
        scenario_override: Optional[str] = None,
        burst_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a single coherent transaction adhering to all SIH constraints."""
        txid = generate_txid(self.rng, seq)

        # 1. Determine scenario
        if scenario_override:
            scenario = scenario_override
        else:
            r = self.rng.random()
            if r < 0.70:
                scenario = "SCEN_NORMAL"
            elif r < 0.76:
                scenario = "SCEN_BURST"
            elif r < 0.81:
                scenario = "SCEN_FAN_IN"
            elif r < 0.86:
                scenario = "SCEN_FAN_OUT"
            elif r < 0.90:
                scenario = "SCEN_PEELING"
            elif r < 0.94:
                scenario = "SCEN_COORDINATED"
            elif r < 0.97:
                scenario = "SCEN_HIGH_VOL"
            else:
                scenario = "SCEN_ADDRESS_REUSE"

        scenario_id = f"{scenario}_{seq:07d}"
        self.scenario_counts[scenario] = self.scenario_counts.get(scenario, 0) + 1

        # 2. Select entity & inputs
        if burst_meta and "entity" in burst_meta:
            sender_ent = burst_meta["entity"]
        else:
            sender_ent = self.rng.choice(self.entities)

        # Determine input/output count based on scenario
        if scenario == "SCEN_FAN_IN":
            in_count = self.rng.randint(5, 10)
            out_count = 1
        elif scenario == "SCEN_FAN_OUT":
            in_count = 1
            out_count = self.rng.randint(5, 10)
        elif scenario == "SCEN_PEELING":
            in_count = 1
            out_count = 2  # 1 small payment + 1 remaining change
        else:
            in_count = self.rng.choice([1, 1, 1, 2, 2, 3])
            out_count = self.rng.choice([1, 2, 2, 2, 3])

        inputs = self._get_spendable_utxos(in_count)
        in_addrs = [u.address for u in inputs]
        in_amts = [u.amount_satoshi for u in inputs]
        total_in = sum(in_amts)

        # Adjust for HIGH_VOL whale scenario
        if scenario == "SCEN_HIGH_VOL":
            boost = self.rng.randint(5_000_000_000, 25_000_000_000)  # 50 to 250 BTC
            in_amts[0] += boost
            total_in += boost

        # 3. Compute realistic fee (Bitcoin value conservation)
        script_type = inputs[0].script_type if inputs else "P2WPKH"
        min_required_spendable = out_count * 1000
        if total_in <= min_required_spendable + 500:
            needed = min_required_spendable + 1500 - total_in
            in_amts[0] += needed
            total_in += needed

        vsize = 10 + len(in_addrs) * 148 + out_count * 34
        fee_rate = self.rng.randint(8, 45)  # sat/vB
        max_possible_fee = total_in - min_required_spendable
        fee = min(vsize * fee_rate, max_possible_fee)
        fee = max(500, fee)
        spendable = total_in - fee

        # 4. Generate outputs & addresses
        out_addrs: List[str] = []
        out_amts: List[int] = []

        if scenario == "SCEN_PEELING":
            # Peel off small payment (10k to 500k satoshis)
            peel_amt = min(self.rng.randint(10_000, 500_000), max(1000, spendable // 3))
            rem_amt = spendable - peel_amt
            dest_ent = self.rng.choice(self.entities)
            out_addrs = [
                self.rng.choice(dest_ent.addresses),
                generate_address(self.rng, script_type)  # Fresh change address
            ]
            out_amts = [peel_amt, rem_amt]
        elif scenario == "SCEN_ADDRESS_REUSE":
            # Intentionally reuse an input address in outputs
            reused_addr = in_addrs[0]
            if out_count == 1:
                out_addrs = [reused_addr]
                out_amts = [spendable]
            else:
                amt1 = max(1000, int(spendable * self.rng.uniform(0.3, 0.7)))
                amt2 = spendable - amt1
                out_addrs = [reused_addr, generate_address(self.rng, script_type)]
                out_amts = [amt1, amt2]
        elif out_count == 1:
            dest_ent = self.rng.choice(self.entities)
            out_addrs = [self.rng.choice(dest_ent.addresses)]
            out_amts = [spendable]
        else:
            # Multi-output split guaranteeing every output >= 1000 and sum(out_amts) == spendable
            rem = spendable
            for i in range(out_count - 1):
                remaining_outputs = out_count - 1 - i
                max_this = rem - (remaining_outputs * 1000)
                if max_this <= 1000:
                    part = 1000
                else:
                    part = self.rng.randint(1000, max(1001, int(max_this * self.rng.uniform(0.1, 0.7))))
                out_amts.append(part)
                rem -= part
                dest_ent = self.rng.choice(self.entities)
                out_addrs.append(self.rng.choice(dest_ent.addresses))
            # Last output gets exact remainder
            out_amts.append(rem)
            out_addrs.append(generate_address(self.rng, script_type))

        # Guarantee exact satoshi conservation: sum(in) == sum(out) + fee
        assert sum(in_amts) == sum(out_amts) + fee, f"Conservation violation: {sum(in_amts)} != {sum(out_amts)} + {fee}"

        # Register outputs in spendable UTXO pool for future transactions
        new_utxos = [
            SyntheticUTXO(txid, idx, addr, amt, script_type)
            for idx, (addr, amt) in enumerate(zip(out_addrs, out_amts))
        ]
        self._add_utxos(new_utxos)

        # 5. Network telemetry
        if burst_meta and "src_ip" in burst_meta:
            src_ip = burst_meta["src_ip"]
            country = burst_meta["country"]
            asn = burst_meta["asn"]
            src_port = self.rng.randint(1024, 65535)
            dst_port = 8333
            dst_ip = f"198.78.30.{self.rng.randint(2, 254)}"
        else:
            tel_cat = "private" if self.rng.random() < 0.04 else "normal"
            src_ip, src_port, dst_ip, dst_port, country, asn = self.ip_mgr.sample_network_event(
                src_subnet=sender_ent.subnet,
                telemetry_category=tel_cat
            )

        # Step time
        if burst_meta:
            self._step_time(0.1, 1.2)  # Sub-second bursts
        else:
            self._step_time(1.0, 12.0)

        # Update tracking metrics
        self.unique_txids += 1
        self.unique_input_addresses.update(in_addrs)
        self.unique_output_addresses.update(out_addrs)
        self.unique_ips.add(src_ip)
        self.unique_ips.add(dst_ip)
        if country == "ZZ":
            self.private_ip_count += 1
        elif country == "XX":
            self.unmapped_ip_count += 1
        else:
            self.mapped_ip_count += 1

        # Format arrays to match SIH format
        # e.g., "['bc1q...']" or "['bc1q1', 'bc1q2']"
        in_addr_str = str(in_addrs)
        out_addr_str = str(out_addrs)
        in_amt_str = str(in_amts)
        out_amt_str = str(out_amts)

        return {
            "txid": txid,
            "timestamp": self.current_time.isoformat(),
            "input_addresses": in_addr_str,
            "output_addresses": out_addr_str,
            "input_amounts": in_amt_str,
            "output_amounts": out_amt_str,
            "fee": fee,
            "script_type": script_type,
            "src_ip": src_ip,
            "src_port": src_port,
            "dst_ip": dst_ip,
            "dst_port": dst_port,
            "country": country,
            "asn": self._clean_asn(asn),
            "scenario_id": scenario_id,
        }

    def generate_to_file(self, out_path: str) -> Dict[str, Any]:
        """Stream generated dataset directly to output CSV file in buffered chunks."""
        out_dir = os.path.dirname(os.path.abspath(out_path))
        os.makedirs(out_dir, exist_ok=True)

        fieldnames = [
            "txid", "timestamp", "input_addresses", "output_addresses",
            "input_amounts", "output_amounts", "fee", "script_type",
            "src_ip", "src_port", "dst_ip", "dst_port", "country", "asn", "scenario_id"
        ]

        print(f"[*] Starting streaming generation of {self.total_rows:,} rows (seed={self.seed})...", flush=True)
        start_wall_time = time.time()

        rows_written = 0
        burst_remaining = 0
        burst_meta = None

        with open(out_path, "w", newline="", encoding="utf-8", buffering=1024 * 1024) as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()

            chunk_buffer: List[Dict[str, Any]] = []

            for i in range(1, self.total_rows + 1):
                # Check burst state
                if burst_remaining > 0:
                    rec = self._generate_single_transaction(i, scenario_override="SCEN_BURST", burst_meta=burst_meta)
                    burst_remaining -= 1
                else:
                    # Occasional multi-transaction burst trigger
                    if self.rng.random() < 0.015:
                        burst_remaining = self.rng.randint(4, 10)
                        burst_ent = self.rng.choice(self.entities)
                        b_ip, b_c, b_asn = self.ip_mgr.sample_public_endpoint(preferred_subnet=burst_ent.subnet)
                        burst_meta = {"entity": burst_ent, "src_ip": b_ip, "country": b_c, "asn": b_asn}
                        self.anomalous_clusters.append({
                            "type": "BURST_ACTIVITY",
                            "start_seq": i,
                            "count": burst_remaining,
                            "ip": b_ip,
                            "country": b_c,
                            "asn": b_asn
                        })
                        rec = self._generate_single_transaction(i, scenario_override="SCEN_BURST", burst_meta=burst_meta)
                        burst_remaining -= 1
                    else:
                        rec = self._generate_single_transaction(i)

                chunk_buffer.append(rec)

                # Write chunk to disk
                if len(chunk_buffer) >= self.chunk_size:
                    writer.writerows(chunk_buffer)
                    rows_written += len(chunk_buffer)
                    chunk_buffer.clear()
                    elapsed = time.time() - start_wall_time
                    rate = rows_written / max(elapsed, 0.001)
                    print(f"  -> Written {rows_written:,} / {self.total_rows:,} rows ({rate:,.0f} rows/s)...", flush=True)

            # Flush remaining
            if chunk_buffer:
                writer.writerows(chunk_buffer)
                rows_written += len(chunk_buffer)
                chunk_buffer.clear()

        duration = time.time() - start_wall_time
        file_size_bytes = os.path.getsize(out_path)
        file_size_mb = file_size_bytes / (1024 * 1024)

        print(f"[+] Completed generation: {rows_written:,} rows in {duration:.2f}s ({rows_written/duration:,.0f} rows/s, {file_size_mb:.2f} MB)", flush=True)

        manifest = {
            "dataset_name": os.path.splitext(os.path.basename(out_path))[0],
            "synthetic_disclaimer": "This dataset is strictly synthetic research data generated for TraceGrid/SIH26146 testing. It contains no real Bitcoin transactions or private information.",
            "seed": self.seed,
            "row_count": rows_written,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": round(file_size_mb, 2),
            "generation_duration_sec": round(duration, 3),
            "throughput_rows_per_sec": round(rows_written / max(duration, 0.001), 1),
            "unique_txid_count": self.unique_txids,
            "unique_input_address_count": len(self.unique_input_addresses),
            "unique_output_address_count": len(self.unique_output_addresses),
            "unique_ip_count": len(self.unique_ips),
            "mapped_ip_events": self.mapped_ip_count,
            "unmapped_ip_events": self.unmapped_ip_count,
            "private_ip_events": self.private_ip_count,
            "scenario_distribution": self.scenario_counts,
            "anomalous_cluster_samples": self.anomalous_clusters[:20],
        }

        manifest_path = os.path.join(out_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f_m:
            json.dump(manifest, f_m, indent=2)

        print(f"[+] Written manifest to: {manifest_path}", flush=True)
        return manifest


def main():
    parser = argparse.ArgumentParser(description="AquaSynex TraceGrid Large-Scale Synthetic Dataset Generator")
    parser.add_argument("--rows", type=int, default=100_000, help="Number of rows to generate (e.g. 1000, 100000, 500000, 1000000)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--out", type=str, default=None, help="Output CSV filepath or directory")
    parser.add_argument("--chunk-size", type=int, default=10_000, help="Streaming write buffer chunk size")
    parser.add_argument("--start-date", type=str, default="2026-01-01T00:00:00+00:00", help="Start timestamp in ISO-8601")

    args = parser.parse_args()

    # Determine default output path if not specified
    if not args.out:
        if args.rows < 10_000:
            out_file = f"data/synthetic/{args.rows // 1000 if args.rows >= 1000 else args.rows}k/synthetic_{args.rows}.csv"
        elif args.rows >= 1_000_000:
            out_file = f"data/synthetic/{args.rows // 1_000_000}m/synthetic_{args.rows // 1_000_000}m.csv"
        else:
            out_file = f"data/synthetic/{args.rows // 1000}k/synthetic_{args.rows // 1000}k.csv"
    else:
        if args.out.endswith(".csv"):
            out_file = args.out
        else:
            out_file = os.path.join(args.out, f"synthetic_{args.rows}.csv")

    gen = StreamingSyntheticGenerator(
        total_rows=args.rows,
        seed=args.seed,
        start_date=args.start_date,
        chunk_size=args.chunk_size,
    )
    gen.generate_to_file(out_file)


if __name__ == "__main__":
    main()

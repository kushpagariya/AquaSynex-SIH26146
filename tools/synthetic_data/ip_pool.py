"""IP Pool and Network Telemetry Module for Synthetic Generation.

Provides deterministic, MMDB-compatible public, private, and unmapped IPv4 pools
for TraceGrid network intelligence simulation.
"""

from typing import Dict, List, Optional, Tuple
import random

# Curated public IP subnets with realistic geographic and ASN distribution
# These subnets are known to resolve in MaxMind GeoLite2-City and IPinfo Lite
PUBLIC_SUBNETS: List[Dict[str, any]] = [
    # North America
    {"subnet": "78.18.57", "country": "US", "asn": 15169, "as_name": "Google LLC", "weight": 0.12},
    {"subnet": "8.8.8", "country": "US", "asn": 15169, "as_name": "Google LLC", "weight": 0.05},
    {"subnet": "198.78.30", "country": "US", "asn": 7018, "as_name": "AT&T Services", "weight": 0.08},
    {"subnet": "104.128.149", "country": "US", "asn": 16509, "as_name": "Amazon AWS", "weight": 0.06},
    {"subnet": "24.78.26", "country": "CA", "asn": 852, "as_name": "TELUS Communications", "weight": 0.04},
    {"subnet": "24.226.137", "country": "CA", "asn": 11260, "as_name": "Eastlink", "weight": 0.03},

    # Europe
    {"subnet": "104.26.184", "country": "NL", "asn": 13335, "as_name": "Cloudflare, Inc.", "weight": 0.10},
    {"subnet": "45.99.98", "country": "NL", "asn": 14061, "as_name": "DigitalOcean, LLC", "weight": 0.06},
    {"subnet": "168.112.65", "country": "DE", "asn": 24940, "as_name": "Hetzner Online GmbH", "weight": 0.08},
    {"subnet": "85.193.58", "country": "DE", "asn": 3320, "as_name": "Deutsche Telekom AG", "weight": 0.04},
    {"subnet": "185.150.207", "country": "FR", "asn": 16276, "as_name": "OVH SAS", "weight": 0.06},
    {"subnet": "51.109.74", "country": "GB", "asn": 8075, "as_name": "Microsoft Corporation", "weight": 0.06},
    {"subnet": "78.129.252", "country": "GB", "asn": 20860, "as_name": "Iomart Hosting Ltd", "weight": 0.03},
    {"subnet": "178.193.126", "country": "CH", "asn": 3303, "as_name": "Swisscom AG", "weight": 0.03},

    # Asia & India
    {"subnet": "78.118.79", "country": "IN", "asn": 15169, "as_name": "Google LLC (India)", "weight": 0.08},
    {"subnet": "103.21.244", "country": "IN", "asn": 13335, "as_name": "Cloudflare India", "weight": 0.04},
    {"subnet": "115.112.22", "country": "IN", "asn": 4755, "as_name": "Tata Communications", "weight": 0.04},
    {"subnet": "121.240.12", "country": "IN", "asn": 4755, "as_name": "Tata Communications", "weight": 0.03},
    {"subnet": "103.224.182", "country": "SG", "asn": 13335, "as_name": "Cloudflare SG", "weight": 0.05},
    {"subnet": "202.12.27", "country": "JP", "asn": 2500, "as_name": "WIDE Project", "weight": 0.04},

    # Latin America & Other
    {"subnet": "168.135.218", "country": "PA", "asn": 15169, "as_name": "Google LLC Panama", "weight": 0.02},
    {"subnet": "177.18.200", "country": "BR", "asn": 28573, "as_name": "Claro Brasil", "weight": 0.03},
    {"subnet": "203.44.216", "country": "AU", "asn": 1221, "as_name": "Telstra Corporation", "weight": 0.03},
]

PRIVATE_SUBNETS = [
    "10.0.1", "10.0.2", "192.168.1", "192.168.0", "172.16.10"
]

UNMAPPED_SUBNETS = [
    "240.0.1", "240.10.5", "198.51.100"
]

BITCOIN_DST_PORTS: List[Tuple[int, float]] = [
    (8333, 0.75),   # Standard Bitcoin mainnet
    (8332, 0.12),   # Bitcoin RPC/node
    (18333, 0.08),  # Bitcoin testnet
    (9333, 0.05),   # Altcoin/p2p
]


class IPPoolManager:
    """Manages deterministic generation of public, private, and unmapped network endpoints."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self.public_subnets = PUBLIC_SUBNETS
        self.weights = [s["weight"] for s in self.public_subnets]
        total_w = sum(self.weights)
        self.normalized_weights = [w / total_w for w in self.weights]

    def sample_public_endpoint(self, preferred_subnet: Optional[str] = None) -> Tuple[str, str, int]:
        """Return (ip, country, asn) for a public endpoint."""
        if preferred_subnet:
            # Match preferred subnet if available
            matched = [s for s in self.public_subnets if s["subnet"] == preferred_subnet]
            if matched:
                sub_meta = matched[0]
            else:
                sub_meta = self.rng.choices(self.public_subnets, weights=self.normalized_weights, k=1)[0]
        else:
            sub_meta = self.rng.choices(self.public_subnets, weights=self.normalized_weights, k=1)[0]

        host_id = self.rng.randint(2, 254)
        ip = f"{sub_meta['subnet']}.{host_id}"
        return ip, sub_meta["country"], sub_meta["asn"]

    def sample_network_event(
        self,
        src_subnet: Optional[str] = None,
        telemetry_category: str = "normal"
    ) -> Tuple[str, int, str, int, str, Optional[int]]:
        """Generate (src_ip, src_port, dst_ip, dst_port, country, asn).

        Only positive integer ASNs (> 0) or None (for unrouted/private IPs) are returned.
        telemetry_category:
        - 'normal': 95% public, 3% private, 2% unmapped
        - 'burst': rapid traffic from identical src_ip/subnet
        - 'private': forced RFC 1918 private IP
        """
        src_port = self.rng.randint(1024, 65535)
        dst_ports, dst_weights = zip(*BITCOIN_DST_PORTS)
        dst_port = self.rng.choices(dst_ports, weights=dst_weights, k=1)[0]

        # Determine source IP type
        r_type = self.rng.random()
        if telemetry_category == "private" or r_type < 0.035:
            # Private RFC 1918 IP (no public ASN)
            sub = self.rng.choice(PRIVATE_SUBNETS)
            src_ip = f"{sub}.{self.rng.randint(2, 254)}"
            country = "ZZ"
            asn = None
        elif r_type < 0.055:
            # Unmapped / documentation IP (no public ASN)
            sub = self.rng.choice(UNMAPPED_SUBNETS)
            src_ip = f"{sub}.{self.rng.randint(2, 254)}"
            country = "XX"
            asn = None
        else:
            # Standard public mapped IP (guaranteed positive ASN > 0)
            src_ip, country, asn = self.sample_public_endpoint(preferred_subnet=src_subnet)

        # Generate distinct public destination IP
        dst_meta = self.rng.choices(self.public_subnets, weights=self.normalized_weights, k=1)[0]
        dst_ip = f"{dst_meta['subnet']}.{self.rng.randint(2, 254)}"
        while dst_ip == src_ip:
            dst_ip = f"{dst_meta['subnet']}.{self.rng.randint(2, 254)}"

        return src_ip, src_port, dst_ip, dst_port, country, asn

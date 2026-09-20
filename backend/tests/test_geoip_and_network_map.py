"""Focused tests for offline GeoIP/ASN enrichment, network aggregation, and map endpoints."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
import duckdb
from backend.services.geoip_service import get_geoip_service
from backend.services.network_service import NetworkService


def test_mmdb_resolves_known_ip():
    """Verify local MMDB lookups return coordinates, country, and ASN for known public IPs."""
    svc = get_geoip_service()
    res = svc.lookup_ip("8.8.8.8")
    assert res.ip == "8.8.8.8"
    assert res.country == "United States"
    assert res.country_code == "US"
    assert res.asn == "AS15169"
    assert res.as_name == "Google LLC"
    assert res.is_mapped is True
    assert res.latitude is not None and -90 <= res.latitude <= 90
    assert res.longitude is not None and -180 <= res.longitude <= 180


def test_invalid_and_private_ips_safe():
    """Verify private, loopback, and malformed IPs do not crash and remain unmapped."""
    svc = get_geoip_service()

    # Private IP
    res_priv = svc.lookup_ip("192.168.1.1")
    assert res_priv.is_private is True
    assert res_priv.is_mapped is False
    assert res_priv.latitude is None
    assert res_priv.longitude is None

    # Loopback IP
    res_loop = svc.lookup_ip("127.0.0.1")
    assert res_loop.is_private is True
    assert res_loop.is_mapped is False

    # Malformed IP
    res_invalid = svc.lookup_ip("not.an.ip.address")
    assert res_invalid.is_mapped is False
    assert res_invalid.latitude is None
    assert res_invalid.longitude is None

    # None / empty
    assert svc.lookup_ip(None).is_mapped is False
    assert svc.lookup_ip("").is_mapped is False


def test_network_aggregation_and_priority(db: duckdb.DuckDBPyConnection):
    """Verify network aggregation combines src/dst, preserves dataset country/ASN, and enriches missing values."""
    dataset_id = "ds_net_test_1"
    now = datetime.now(timezone.utc)

    # Seed dataset record
    db.execute(
        """
        INSERT INTO datasets (dataset_id, name, file_name, file_path, format, uploaded_at, status)
        VALUES (?, 'Net Test', 'test.csv', '/tmp/test.csv', 'csv', ?, 'ready')
        """,
        [dataset_id, now],
    )

    # Insert 3 network events:
    # Event 1: src=8.8.8.8 (dataset country='NL', asn=99999), dst=51.109.74.176
    # Event 2: src=8.8.8.8 (dataset country='NL', asn=99999), dst=10.0.0.1 (private)
    # Event 3: src=104.26.184.134 (country=NULL, asn=NULL - should enrich), dst=8.8.8.8
    events = [
        ("EVT_1", "TX_1", dataset_id, now, "8.8.8.8", 8333, "51.109.74.176", 8333, "NL", 99999),
        ("EVT_2", "TX_2", dataset_id, now, "8.8.8.8", 8333, "10.0.0.1", 8333, "NL", 99999),
        ("EVT_3", "TX_3", dataset_id, now, "104.26.184.134", 8333, "8.8.8.8", 8333, None, None),
    ]
    for ev in events:
        db.execute(
            """
            INSERT INTO network_events (event_id, transaction_id, dataset_id, timestamp, src_ip, src_port, dst_ip, dst_port, country, asn)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            list(ev),
        )

    svc = NetworkService(db)
    result = svc.get_network_map(dataset_id)

    assert result["dataset_id"] == dataset_id
    metrics = result["metrics"]
    assert metrics["total_events"] == 3
    # Distinct IPs: 8.8.8.8, 51.109.74.176, 10.0.0.1, 104.26.184.134 -> 4 unique IPs
    assert metrics["total_ips"] == 4

    points_by_ip = {p["ip"]: p for p in result["points"]}

    # 8.8.8.8 appeared in 3 distinct events (2 as src, 1 as dst)
    p_google = points_by_ip["8.8.8.8"]
    assert p_google["event_count"] == 3
    assert p_google["source_event_count"] == 2
    assert p_google["destination_event_count"] == 1
    assert p_google["transaction_count"] == 3
    # Dataset priority test: country was explicitly provided as 'NL', asn as 99999
    assert p_google["country"] == "NL"
    assert p_google["asn"] == "AS99999"
    # Coordinates come from GeoLite2
    assert p_google["is_mapped"] is True
    assert p_google["latitude"] is not None

    # 104.26.184.134 had no country or asn in dataset -> should enrich from MMDB
    p_cf = points_by_ip["104.26.184.134"]
    assert p_cf["country"] == "United States"
    assert p_cf["is_mapped"] is True

    # 10.0.0.1 is private -> unmapped
    p_priv = points_by_ip["10.0.0.1"]
    assert p_priv["is_mapped"] is False
    assert p_priv["latitude"] is None


def test_network_map_dataset_isolation(db: duckdb.DuckDBPyConnection):
    """Verify dataset isolation prevents network events from leaking across datasets."""
    now = datetime.now(timezone.utc)
    for ds in ["ds_iso_A", "ds_iso_B"]:
        db.execute(
            """
            INSERT INTO datasets (dataset_id, name, file_name, file_path, format, uploaded_at, status)
            VALUES (?, 'Iso Test', 'test.csv', '/tmp/test.csv', 'csv', ?, 'ready')
            """,
            [ds, now],
        )

    db.execute(
        """
        INSERT INTO network_events (event_id, transaction_id, dataset_id, timestamp, src_ip, dst_ip)
        VALUES ('E_A1', 'TX_A1', 'ds_iso_A', ?, '8.8.8.8', '1.1.1.1')
        """,
        [now],
    )
    db.execute(
        """
        INSERT INTO network_events (event_id, transaction_id, dataset_id, timestamp, src_ip, dst_ip)
        VALUES ('E_B1', 'TX_B1', 'ds_iso_B', ?, '9.9.9.9', '1.1.1.1')
        """,
        [now],
    )

    svc = NetworkService(db)
    res_a = svc.get_network_map("ds_iso_A")
    res_b = svc.get_network_map("ds_iso_B")

    ips_a = {p["ip"] for p in res_a["points"]}
    ips_b = {p["ip"] for p in res_b["points"]}

    assert "8.8.8.8" in ips_a
    assert "8.8.8.8" not in ips_b
    assert "9.9.9.9" in ips_b
    assert "9.9.9.9" not in ips_a


def test_api_network_map_endpoints(client: TestClient, db: duckdb.DuckDBPyConnection):
    """Verify both /api/datasets/{datasetId}/network/map and /api/network/map return canonical envelopes."""
    dataset_id = "ds_api_net_1"
    now = datetime.now(timezone.utc)

    db.execute(
        """
        INSERT INTO datasets (dataset_id, name, file_name, file_path, format, uploaded_at, status)
        VALUES (?, 'API Net Test', 'test.csv', '/tmp/test.csv', 'csv', ?, 'ready')
        """,
        [dataset_id, now],
    )
    db.execute(
        """
        INSERT INTO network_events (event_id, transaction_id, dataset_id, timestamp, src_ip, dst_ip, country, asn)
        VALUES ('E1', 'TX1', ?, ?, '8.8.8.8', '51.109.74.176', 'US', 15169)
        """,
        [dataset_id, now],
    )

    # Route 1: /api/datasets/{datasetId}/network/map
    resp1 = client.get(f"/api/datasets/{dataset_id}/network/map")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["success"] is True
    assert data1["data"]["datasetId"] == dataset_id
    assert data1["data"]["metrics"]["totalIps"] == 2
    assert len(data1["data"]["points"]) == 2

    # Route 2: /api/network/map?datasetId={datasetId}
    resp2 = client.get(f"/api/network/map?datasetId={dataset_id}")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    assert data2["data"]["datasetId"] == dataset_id


def test_transactions_api_ip_drilldown(client: TestClient, db: duckdb.DuckDBPyConnection):
    """Verify /api/datasets/{datasetId}/transactions?ip=<IP> filters server-side with pagination."""
    dataset_id = "ds_tx_ip_test"
    now = datetime.now(timezone.utc)

    db.execute(
        """
        INSERT INTO datasets (dataset_id, name, file_name, file_path, format, uploaded_at, status)
        VALUES (?, 'TX IP Test', 'test.csv', '/tmp/test.csv', 'csv', ?, 'ready')
        """,
        [dataset_id, now],
    )

    # Insert 3 transactions
    for i in range(1, 4):
        db.execute(
            """
            INSERT INTO transactions (transaction_id, dataset_id, timestamp, input_count, output_count,
                                      total_input_value_satoshi, total_output_value_satoshi, fee_satoshi, ingested_at)
            VALUES (?, ?, ?, 1, 1, 100000000, 99990000, 10000, ?)
            """,
            [f"TX_{i}", dataset_id, now, now],
        )

    # Associate TX_1 and TX_3 with IP 8.8.8.8; TX_2 with 1.1.1.1
    db.execute(
        """
        INSERT INTO network_events (event_id, transaction_id, dataset_id, src_ip, dst_ip)
        VALUES 
            ('E_1', 'TX_1', ?, '8.8.8.8', '51.109.74.176'),
            ('E_2', 'TX_2', ?, '1.1.1.1', '51.109.74.176'),
            ('E_3', 'TX_3', ?, '24.78.26.42', '8.8.8.8')
        """,
        [dataset_id, dataset_id, dataset_id],
    )

    # Query without filter -> returns all 3 transactions
    all_resp = client.get(f"/api/datasets/{dataset_id}/transactions")
    assert all_resp.status_code == 200
    assert len(all_resp.json()["data"]) == 3

    # Query with ?ip=8.8.8.8 -> must return only TX_1 and TX_3 (paginated, 2 items)
    ip_resp = client.get(f"/api/datasets/{dataset_id}/transactions?ip=8.8.8.8")
    assert ip_resp.status_code == 200
    res_data = ip_resp.json()
    assert res_data["success"] is True
    tx_ids = [t["transactionId"] for t in res_data["data"]]
    assert set(tx_ids) == {"TX_1", "TX_3"}
    assert res_data["meta"]["pagination"]["totalItems"] == 2

    # Query with ?ip=1.1.1.1 -> only TX_2
    ip2_resp = client.get(f"/api/datasets/{dataset_id}/transactions?ip=1.1.1.1")
    assert ip2_resp.status_code == 200
    tx2_ids = [t["transactionId"] for t in ip2_resp.json()["data"]]
    assert tx2_ids == ["TX_2"]

    # Query with non-existent IP -> 0 items
    none_resp = client.get(f"/api/datasets/{dataset_id}/transactions?ip=99.99.99.99")
    assert none_resp.status_code == 200
    assert len(none_resp.json()["data"]) == 0
    assert none_resp.json()["meta"]["pagination"]["totalItems"] == 0

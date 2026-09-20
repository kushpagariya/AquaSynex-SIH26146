"""Focused tests for offline GeoIP/ASN enrichment, network aggregation, and map endpoints."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
import duckdb
from backend.services.geoip_service import get_geoip_service
from backend.services.network_service import NetworkService
from backend.services.dataset_service import DatasetService


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


def test_asn_strict_positive_validation_in_ingestion(db: duckdb.DuckDBPyConnection, tmp_path):
    """Verify ingestion pipeline accepts strictly positive integer ASNs (> 0) and converts 0, negative, null, or invalid ASNs to NULL."""
    dataset_id = "ds_asn_test"
    csv_file = tmp_path / "test_asn.csv"
    csv_content = (
        "txid,timestamp,input_addresses,output_addresses,input_amounts,output_amounts,fee,script_type,src_ip,src_port,dst_ip,dst_port,country,asn\n"
        "tx_0001_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:00Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,8.8.8.8,12345,10.0.0.1,8333,US,15169\n"
        "tx_0002_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:01Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,8.8.4.4,12346,10.0.0.1,8333,US,AS15169\n"
        "tx_0003_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:02Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,51.109.74.1,12347,10.0.0.1,8333,GB,as8075\n"
        "tx_0004_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:03Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,10.0.0.1,12348,10.0.0.2,8333,ZZ,0\n"
        "tx_0005_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:04Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,10.0.0.2,12349,10.0.0.3,8333,ZZ,AS0\n"
        "tx_0006_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:05Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,10.0.0.3,12350,10.0.0.4,8333,ZZ,-10\n"
        "tx_0007_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:06Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,10.0.0.4,12351,10.0.0.5,8333,ZZ,\"-50\"\n"
        "tx_0008_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:07Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,10.0.0.5,12352,10.0.0.6,8333,XX,invalid\n"
        "tx_0009_000000000000000000000000000000000000000000000000000000000000,2026-03-01T12:00:08Z,['addr1'],['addr2'],[100000],[90000],10000,p2pkh,10.0.0.6,12353,10.0.0.7,8333,XX,\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    db.execute(
        "INSERT INTO datasets (dataset_id, name, file_name, file_path, format, uploaded_at, status) VALUES (?, 'ASN Test', 'test.csv', ?, 'csv', current_timestamp, 'processing')",
        [dataset_id, str(csv_file)],
    )

    ds_svc = DatasetService(db)
    ds_svc._ingest_file(dataset_id, csv_file, "csv")

    rows = db.execute(
        "SELECT transaction_id, src_ip, asn FROM network_events WHERE dataset_id = ? ORDER BY transaction_id",
        [dataset_id],
    ).fetchall()
    asn_by_tx = {r[0][:7]: r[2] for r in rows}

    # Positive integer ASNs accepted:
    assert asn_by_tx["tx_0001"] == 15169
    assert asn_by_tx["tx_0002"] == 15169
    assert asn_by_tx["tx_0003"] == 8075

    # 0, AS0, negative (-10, -50), invalid strings, and empty -> NULL
    assert asn_by_tx["tx_0004"] is None
    assert asn_by_tx["tx_0005"] is None
    assert asn_by_tx["tx_0006"] is None
    assert asn_by_tx["tx_0007"] is None
    assert asn_by_tx["tx_0008"] is None
    assert asn_by_tx["tx_0009"] is None

    # Verify no non-positive ASN exists in the table
    non_positive = db.execute(
        "SELECT COUNT(*) FROM network_events WHERE dataset_id = ? AND (asn IS NOT NULL AND asn <= 0)",
        [dataset_id],
    ).fetchone()[0]
    assert non_positive == 0


def test_network_map_rejects_non_positive_asn(db: duckdb.DuckDBPyConnection):
    """Verify get_network_map ignores zero/negative ASNs and does not populate 'AS0' or count invalid ASNs."""
    dataset_id = "ds_asn_map_test"
    now = datetime.now(timezone.utc)
    db.execute(
        "INSERT INTO datasets (dataset_id, name, file_name, file_path, format, uploaded_at, status) VALUES (?, 'Map ASN Test', 'test.csv', '/tmp/test.csv', 'csv', ?, 'ready')",
        [dataset_id, now],
    )

    # Insert events with 0, negative, and positive ASNs
    events = [
        ("EVT_P1", "TX_P1", dataset_id, now, "10.0.0.1", 8333, "10.0.0.2", 8333, "ZZ", 0),
        ("EVT_P2", "TX_P2", dataset_id, now, "10.0.0.3", 8333, "10.0.0.4", 8333, "ZZ", -5),
        ("EVT_P3", "TX_P3", dataset_id, now, "8.8.8.8", 8333, "10.0.0.5", 8333, "US", 15169),
    ]
    for ev in events:
        db.execute(
            "INSERT INTO network_events (event_id, transaction_id, dataset_id, timestamp, src_ip, src_port, dst_ip, dst_port, country, asn) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            list(ev),
        )

    svc = NetworkService(db)
    res = svc.get_network_map(dataset_id)

    # metrics.unique_asns should strictly count positive ASNs (1 for AS15169)
    assert res["metrics"]["unique_asns"] == 1

    point_by_ip = {p["ip"]: p for p in res["points"]}
    assert point_by_ip["10.0.0.1"]["asn"] is None
    assert point_by_ip["10.0.0.3"]["asn"] is None
    assert point_by_ip["8.8.8.8"]["asn"] == "AS15169"

    for point in res["points"]:
        if point["asn"]:
            assert point["asn"].startswith("AS")
            asn_num = int(point["asn"][2:])
            assert asn_num > 0

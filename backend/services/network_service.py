"""Network Intelligence service aggregating DuckDB network events with offline MMDB enrichment."""

from typing import Any, Dict, List, Optional
import duckdb
from backend.services.geoip_service import GeoIPService, get_geoip_service
from backend.utils.converters import format_utc_datetime
from backend.utils.errors import DatasetNotFoundError


class NetworkService:
    """Aggregates network telemetry and enriches endpoints with local GeoIP/ASN metadata."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        geoip_service: Optional[GeoIPService] = None,
    ) -> None:
        self.conn = conn
        self.geoip_service = geoip_service or get_geoip_service()

    def get_network_map(
        self,
        dataset_id: str,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate network events by IP for a dataset and enrich with offline GeoIP/ASN data.
        
        Prioritizes dataset-provided country and ASN, filling missing metadata and coordinates
        from local MMDB databases.
        """
        # 1. Verify dataset exists
        check_sql = "SELECT 1 FROM datasets WHERE dataset_id = ?"
        exists = self.conn.execute(check_sql, [dataset_id]).fetchone()
        if not exists:
            raise DatasetNotFoundError(dataset_id)

        # 2. Get total network events count for this dataset
        total_events_sql = "SELECT COUNT(*) FROM network_events WHERE dataset_id = ?"
        total_events_row = self.conn.execute(total_events_sql, [dataset_id]).fetchone()
        total_events = total_events_row[0] if total_events_row else 0

        # 3. Aggregate distinct network endpoints (both src and dst)
        agg_sql = """
        WITH ep AS (
            SELECT 
                src_ip AS ip,
                event_id,
                transaction_id,
                timestamp,
                country,
                asn,
                1 AS is_src,
                0 AS is_dst
            FROM network_events
            WHERE dataset_id = ? AND src_ip IS NOT NULL AND TRIM(src_ip) != ''
            UNION ALL
            SELECT 
                dst_ip AS ip,
                event_id,
                transaction_id,
                timestamp,
                NULL AS country,
                NULL AS asn,
                0 AS is_src,
                1 AS is_dst
            FROM network_events
            WHERE dataset_id = ? AND dst_ip IS NOT NULL AND TRIM(dst_ip) != ''
        )
        SELECT 
            ip,
            COUNT(DISTINCT event_id) AS event_count,
            COUNT(DISTINCT transaction_id) AS transaction_count,
            SUM(is_src) AS source_event_count,
            SUM(is_dst) AS destination_event_count,
            MIN(timestamp) AS first_seen,
            MAX(timestamp) AS last_seen,
            MAX(country) FILTER (WHERE country IS NOT NULL AND TRIM(country) != '') AS dataset_country,
            MAX(asn) FILTER (WHERE asn IS NOT NULL) AS dataset_asn
        FROM ep
        GROUP BY ip
        ORDER BY event_count DESC, ip ASC
        """
        rows = self.conn.execute(agg_sql, [dataset_id, dataset_id]).fetchall()

        points: List[Dict[str, Any]] = []
        unique_countries = set()
        unique_asns = set()
        mapped_ips = 0

        for r in rows:
            (
                ip,
                event_count,
                transaction_count,
                src_count,
                dst_count,
                first_seen_ts,
                last_seen_ts,
                dataset_country,
                dataset_asn,
            ) = r

            # Offline enrichment via local MMDBs
            enrichment = self.geoip_service.lookup_ip(ip)

            # Data Priority: prefer dataset-provided values
            # Country:
            final_country = dataset_country if dataset_country else enrichment.country
            final_country_code = (
                dataset_country
                if dataset_country and len(dataset_country) == 2
                else (enrichment.country_code or (final_country[:2].upper() if final_country else None))
            )

            # ASN:
            if dataset_asn is not None:
                final_asn = f"AS{dataset_asn}"
                final_as_name = enrichment.as_name or f"AS{dataset_asn}"
            else:
                final_asn = enrichment.asn
                final_as_name = enrichment.as_name

            if final_country:
                unique_countries.add(final_country)
            if final_asn:
                unique_asns.add(final_asn)

            if enrichment.is_mapped:
                mapped_ips += 1

            first_seen_str = format_utc_datetime(first_seen_ts) if first_seen_ts else None
            last_seen_str = format_utc_datetime(last_seen_ts) if last_seen_ts else None

            points.append({
                "ip": ip,
                "country": final_country,
                "country_code": final_country_code,
                "region": enrichment.region,
                "city": enrichment.city,
                "latitude": enrichment.latitude,
                "longitude": enrichment.longitude,
                "asn": final_asn,
                "as_name": final_as_name,
                "as_domain": enrichment.as_domain,
                "event_count": int(event_count or 0),
                "transaction_count": int(transaction_count or 0),
                "source_event_count": int(src_count or 0),
                "destination_event_count": int(dst_count or 0),
                "first_seen": first_seen_str,
                "last_seen": last_seen_str,
                "is_mapped": enrichment.is_mapped,
            })

        total_ips = len(points)
        unmapped_ips = total_ips - mapped_ips

        # 4. Aggregate directional network flow relationships between endpoints
        edge_sql = """
        SELECT
            src_ip,
            dst_ip,
            COUNT(*) AS event_count,
            COUNT(DISTINCT transaction_id) AS transaction_count
        FROM network_events
        WHERE dataset_id = ?
          AND src_ip IS NOT NULL AND TRIM(src_ip) != ''
          AND dst_ip IS NOT NULL AND TRIM(dst_ip) != ''
          AND src_ip != dst_ip
        GROUP BY src_ip, dst_ip
        ORDER BY event_count DESC
        LIMIT 500
        """
        edge_rows = self.conn.execute(edge_sql, [dataset_id]).fetchall()
        edges = [
            {
                "src_ip": er[0],
                "dst_ip": er[1],
                "event_count": int(er[2] or 0),
                "transaction_count": int(er[3] or 0),
            }
            for er in edge_rows
        ]

        metrics = {
            "total_ips": total_ips,
            "mapped_ips": mapped_ips,
            "unmapped_ips": unmapped_ips,
            "unique_countries": len(unique_countries),
            "unique_asns": len(unique_asns),
            "total_events": total_events,
        }

        return {
            "dataset_id": dataset_id,
            "analysis_id": analysis_id,
            "metrics": metrics,
            "points": points,
            "edges": edges,
        }


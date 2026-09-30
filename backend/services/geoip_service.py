"""Offline GeoIP and ASN enrichment service using local MMDB databases.

Loads datasets/GeoLite2-City.mmdb and datasets/ipinfo_lite.mmdb for offline IP
enrichment. Never calls remote APIs or requires internet connectivity.
"""

from dataclasses import dataclass
import ipaddress
import os
from pathlib import Path
from typing import Any, Dict, Optional
import maxminddb
from backend.utils.logging import logger


@dataclass
class GeoIPEnrichment:
    ip: str
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    asn: Optional[str] = None
    as_name: Optional[str] = None
    as_domain: Optional[str] = None
    is_mapped: bool = False
    is_private: bool = False


class GeoIPService:
    """Offline reader for MaxMind GeoLite2-City and IPinfo Lite MMDB databases."""

    def __init__(
        self,
        geolite_path: Optional[str] = None,
        ipinfo_path: Optional[str] = None,
    ) -> None:
        self.geolite_path = self._resolve_path(
            geolite_path or os.environ.get("GEOLITE2_PATH"),
            "GeoLite2-City.mmdb",
        )
        self.ipinfo_path = self._resolve_path(
            ipinfo_path or os.environ.get("IPINFO_PATH"),
            "ipinfo_lite.mmdb",
        )

        self._geo_reader: Optional[maxminddb.Reader] = None
        self._asn_reader: Optional[maxminddb.Reader] = None
        self._cache: Dict[str, GeoIPEnrichment] = {}
        self._max_cache_size = 50000

        self._init_readers()

    def _resolve_path(self, override_path: Optional[str], filename: str) -> Optional[Path]:
        """Find the local MMDB database file path across dev, docker, and package environments."""
        candidates = []
        if override_path:
            candidates.append(Path(override_path))

        # Relative to project root
        repo_root = Path(__file__).resolve().parent.parent.parent
        candidates.append(repo_root / "datasets" / filename)

        # Docker / linux container standard path
        candidates.append(Path("/app/datasets") / filename)
        candidates.append(Path("datasets") / filename)

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        logger.warning(f"MMDB database '{filename}' was not found in candidate paths: {[str(c) for c in candidates]}")
        return None

    def _init_readers(self) -> None:
        """Initialize and cache persistent MMDB readers."""
        if self.geolite_path and self.geolite_path.exists():
            try:
                self._geo_reader = maxminddb.open_database(str(self.geolite_path))
                logger.info(f"Loaded GeoLite2 database from {self.geolite_path}")
            except Exception as exc:
                logger.error(f"Failed to open GeoLite2 MMDB at {self.geolite_path}: {exc}")
                self._geo_reader = None

        if self.ipinfo_path and self.ipinfo_path.exists():
            try:
                self._asn_reader = maxminddb.open_database(str(self.ipinfo_path))
                logger.info(f"Loaded IPinfo Lite database from {self.ipinfo_path}")
            except Exception as exc:
                logger.error(f"Failed to open IPinfo Lite MMDB at {self.ipinfo_path}: {exc}")
                self._asn_reader = None

    def lookup_ip(self, ip_str: Optional[str]) -> GeoIPEnrichment:
        """Safely enrich an IP string using local MMDB databases.
        
        Never raises an exception on malformed or unresolvable IP addresses.
        """
        if not ip_str or not isinstance(ip_str, str):
            return GeoIPEnrichment(ip=str(ip_str or ""), is_mapped=False)

        clean_ip = ip_str.strip()
        if not clean_ip:
            return GeoIPEnrichment(ip="", is_mapped=False)

        if clean_ip in self._cache:
            return self._cache[clean_ip]

        # Validate IP format and check for private / reserved ranges
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
        except ValueError:
            enrichment = GeoIPEnrichment(ip=clean_ip, is_mapped=False)
            self._save_cache(clean_ip, enrichment)
            return enrichment

        is_private = (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
            or ip_obj.is_link_local
        )

        if is_private:
            enrichment = GeoIPEnrichment(
                ip=clean_ip,
                country="Private / Reserved",
                country_code="ZZ",
                is_private=True,
                is_mapped=False,
            )
            self._save_cache(clean_ip, enrichment)
            return enrichment

        country: Optional[str] = None
        country_code: Optional[str] = None
        region: Optional[str] = None
        city: Optional[str] = None
        latitude: Optional[float] = None
        longitude: Optional[float] = None
        asn: Optional[str] = None
        as_name: Optional[str] = None
        as_domain: Optional[str] = None

        # 1. Geographic enrichment via GeoLite2-City
        if self._geo_reader:
            try:
                geo_rec = self._geo_reader.get(clean_ip)
                if isinstance(geo_rec, dict):
                    loc = geo_rec.get("location") or {}
                    lat = loc.get("latitude")
                    lon = loc.get("longitude")
                    if lat is not None and lon is not None:
                        try:
                            f_lat = float(lat)
                            f_lon = float(lon)
                            if -90.0 <= f_lat <= 90.0 and -180.0 <= f_lon <= 180.0:
                                latitude = f_lat
                                longitude = f_lon
                        except (ValueError, TypeError):
                            pass

                    c_info = geo_rec.get("country") or {}
                    country = c_info.get("names", {}).get("en")
                    country_code = c_info.get("iso_code")

                    c_city = geo_rec.get("city") or {}
                    city = c_city.get("names", {}).get("en")

                    subs = geo_rec.get("subdivisions") or []
                    if subs and isinstance(subs, list) and len(subs) > 0:
                        region = subs[0].get("names", {}).get("en")
            except Exception as exc:
                logger.debug(f"GeoLite2 lookup error for IP {clean_ip}: {exc}")

        # 2. ASN and network enrichment via ipinfo_lite
        if self._asn_reader:
            try:
                asn_rec = self._asn_reader.get(clean_ip)
                if isinstance(asn_rec, dict):
                    raw_asn = asn_rec.get("asn")
                    if raw_asn is not None:
                        clean_asn_str = str(raw_asn).strip()
                        if clean_asn_str.upper().startswith("AS"):
                            clean_asn_str = clean_asn_str[2:].strip()
                        if clean_asn_str.isdigit() and int(clean_asn_str) > 0:
                            asn = f"AS{int(clean_asn_str)}"
                        else:
                            asn = None
                    else:
                        asn = None
                    as_name = asn_rec.get("as_name")
                    as_domain = asn_rec.get("as_domain")

                    # Fallback country from ipinfo if GeoLite didn't supply it
                    if not country and asn_rec.get("country"):
                        country = asn_rec.get("country")
                    if not country_code and asn_rec.get("country_code"):
                        country_code = asn_rec.get("country_code")
            except Exception as exc:
                logger.debug(f"IPinfo lookup error for IP {clean_ip}: {exc}")

        is_mapped = latitude is not None and longitude is not None

        enrichment = GeoIPEnrichment(
            ip=clean_ip,
            country=country,
            country_code=country_code,
            region=region,
            city=city,
            latitude=latitude,
            longitude=longitude,
            asn=asn,
            as_name=as_name,
            as_domain=as_domain,
            is_mapped=is_mapped,
            is_private=False,
        )

        self._save_cache(clean_ip, enrichment)
        return enrichment

    def _save_cache(self, ip: str, val: GeoIPEnrichment) -> None:
        """Bounded in-memory cache."""
        if len(self._cache) >= self._max_cache_size:
            # Drop earliest 10% of entries to keep size controlled
            keys_to_remove = list(self._cache.keys())[:5000]
            for k in keys_to_remove:
                del self._cache[k]
        self._cache[ip] = val

    def close(self) -> None:
        """Close open reader file handles."""
        if self._geo_reader:
            try:
                self._geo_reader.close()
            except Exception:
                pass
            self._geo_reader = None

        if self._asn_reader:
            try:
                self._asn_reader.close()
            except Exception:
                pass
            self._asn_reader = None


# Module-level singleton
_geoip_service_instance: Optional[GeoIPService] = None


def get_geoip_service() -> GeoIPService:
    """Return or initialize the singleton GeoIPService instance."""
    global _geoip_service_instance
    if _geoip_service_instance is None:
        _geoip_service_instance = GeoIPService()
    return _geoip_service_instance

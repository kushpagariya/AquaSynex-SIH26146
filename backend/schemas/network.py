"""Pydantic schemas for network intelligence and geographic map visualization."""

from typing import List, Optional
from backend.schemas.common import CamelModel


class NetworkMapPoint(CamelModel):
    """An aggregated network endpoint represented on the geographic map."""

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
    event_count: int = 0
    transaction_count: int = 0
    source_event_count: int = 0
    destination_event_count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    is_mapped: bool = False


class NetworkMapMetrics(CamelModel):
    """Overall derived summary metrics for the dataset network events."""

    total_ips: int = 0
    mapped_ips: int = 0
    unmapped_ips: int = 0
    unique_countries: int = 0
    unique_asns: int = 0
    total_events: int = 0


class NetworkMapResponse(CamelModel):
    """Canonical response payload for the network map endpoint."""

    dataset_id: str
    analysis_id: Optional[str] = None
    metrics: NetworkMapMetrics
    points: List[NetworkMapPoint] = []

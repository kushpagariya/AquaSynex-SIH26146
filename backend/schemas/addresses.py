"""Address schemas matching docs/backend/request-response-schemas.md."""

from datetime import datetime
from typing import Optional
from backend.schemas.common import CamelModel
from backend.schemas.ml_results import MLResultDetail


class AddressSummary(CamelModel):
    address_id: str
    transaction_count: Optional[int] = None
    total_received_btc: Optional[str] = None  # 8-decimal string
    total_sent_btc: Optional[str] = None  # 8-decimal string
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None


class AddressDetail(AddressSummary):
    address_type: Optional[str] = None
    active_days: Optional[int] = None
    ml_result: Optional[MLResultDetail] = None

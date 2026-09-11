"""BTC/satoshi precision converters and datetime formatting utilities.

Authoritative reference: docs/decisions/ADR-004-satoshi-value-representation.md
Rules:
- All Bitcoin values are stored and processed internally as integer satoshis.
- API responses must use satoshi_to_btc_str() for BTC value fields.
- Never return raw satoshi integers as BTC float values.
- Never use floating-point arithmetic on BTC monetary values.
"""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional, Union


SATOSHIS_PER_BTC = 100_000_000


def satoshi_to_btc_str(satoshi: Optional[Union[int, float]]) -> Optional[str]:
    """Convert satoshi integer to 8-decimal BTC string for API responses.

    Examples:
        500000000 -> "5.00000000"
        1000 -> "0.00001000"
        None -> None
    """
    if satoshi is None:
        return None
    
    # Use Decimal for forensic precision
    dec_sat = Decimal(str(int(satoshi)))
    dec_btc = dec_sat / Decimal(SATOSHIS_PER_BTC)
    return f"{dec_btc:.8f}"


def btc_str_to_satoshi(btc_val: Optional[Union[str, int, float, Decimal]]) -> int:
    """Convert BTC string or value to satoshi integer without precision loss.

    Examples:
        "5.00000000" -> 500000000
        "0.00000001" -> 1
    """
    if btc_val is None:
        return 0

    if isinstance(btc_val, (int, float, str, Decimal)):
        try:
            dec_btc = Decimal(str(btc_val).strip())
            return int((dec_btc * Decimal(SATOSHIS_PER_BTC)).to_integral_value())
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Invalid BTC amount representation: {btc_val}") from exc

    raise TypeError(f"Unsupported type for BTC conversion: {type(btc_val)}")


def to_utc_datetime(dt: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """Convert a datetime or string to a UTC timezone-aware datetime."""
    if dt is None:
        return None

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(dt, str):
        cleaned = dt.strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    return None


def format_utc_datetime(dt: Optional[Union[datetime, str]]) -> Optional[str]:
    """Format datetime as UTC ISO 8601 string."""
    utc_dt = to_utc_datetime(dt)
    if utc_dt is None:
        return None
    return utc_dt.isoformat()

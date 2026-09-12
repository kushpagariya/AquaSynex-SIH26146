"""Unit tests for converters and ADR-004 satoshi/BTC precision handling."""

from datetime import datetime, timezone
import pytest
from backend.utils.converters import btc_str_to_satoshi, format_utc_datetime, satoshi_to_btc_str, to_utc_datetime


def test_satoshi_to_btc_str_standard():
    assert satoshi_to_btc_str(100_000_000) == "1.00000000"
    assert satoshi_to_btc_str(500_000_000) == "5.00000000"
    assert satoshi_to_btc_str(1) == "0.00000001"
    assert satoshi_to_btc_str(0) == "0.00000000"
    assert satoshi_to_btc_str(None) is None


def test_satoshi_to_btc_str_large_numbers():
    # 21 million BTC in satoshis: 2,100,000,000,000,000
    assert satoshi_to_btc_str(2_100_000_000_000_000) == "21000000.00000000"


def test_btc_str_to_satoshi():
    assert btc_str_to_satoshi("1.00000000") == 100_000_000
    assert btc_str_to_satoshi("5.00000000") == 500_000_000
    assert btc_str_to_satoshi("0.00000001") == 1
    assert btc_str_to_satoshi("0.00000000") == 0
    assert btc_str_to_satoshi(None) == 0


def test_btc_str_to_satoshi_floating_precision_safety():
    # Demonstrating no 0.1 + 0.2 floating precision loss
    sat1 = btc_str_to_satoshi("0.10000000")
    sat2 = btc_str_to_satoshi("0.20000000")
    assert sat1 + sat2 == 30_000_000
    assert satoshi_to_btc_str(sat1 + sat2) == "0.30000000"


def test_btc_str_to_satoshi_invalid():
    with pytest.raises(ValueError):
        btc_str_to_satoshi("invalid_btc")


def test_to_utc_datetime():
    dt_naive = datetime(2026, 9, 11, 12, 0, 0)
    dt_utc = to_utc_datetime(dt_naive)
    assert dt_utc.tzinfo == timezone.utc

    str_iso = "2026-09-11T16:30:00Z"
    dt_from_str = to_utc_datetime(str_iso)
    assert dt_from_str.tzinfo == timezone.utc
    assert dt_from_str.hour == 16
    assert dt_from_str.minute == 30


def test_format_utc_datetime():
    dt = datetime(2026, 9, 11, 16, 30, 0, tzinfo=timezone.utc)
    formatted = format_utc_datetime(dt)
    assert formatted == "2026-09-11T16:30:00+00:00"

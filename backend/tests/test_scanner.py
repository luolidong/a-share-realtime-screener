from datetime import datetime
from zoneinfo import ZoneInfo

from app.scanner import is_market_open

SHANGHAI = ZoneInfo("Asia/Shanghai")


def dt(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=SHANGHAI)


def test_market_open_during_weekday_sessions():
    assert is_market_open(dt(2026, 9, 14, 9, 30))
    assert is_market_open(dt(2026, 9, 14, 10, 15))
    assert is_market_open(dt(2026, 9, 14, 13, 0))
    assert is_market_open(dt(2026, 9, 14, 14, 59))


def test_market_closed_at_lunch_and_weekend():
    assert not is_market_open(dt(2026, 9, 14, 12, 0))
    assert not is_market_open(dt(2026, 9, 12, 10, 0))

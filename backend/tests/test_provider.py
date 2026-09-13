from datetime import date

import pandas as pd

from app.providers.akshare_provider import _normalize_codes, latest_reporting_period


def test_latest_complete_reporting_period_boundaries():
    assert latest_reporting_period(date(2026, 1, 1)) == "20250930"
    assert latest_reporting_period(date(2026, 4, 30)) == "20250930"
    assert latest_reporting_period(date(2026, 5, 1)) == "20260331"
    assert latest_reporting_period(date(2026, 8, 31)) == "20260331"
    assert latest_reporting_period(date(2026, 9, 1)) == "20260630"
    assert latest_reporting_period(date(2026, 10, 31)) == "20260630"
    assert latest_reporting_period(date(2026, 11, 1)) == "20260930"
    assert latest_reporting_period(date(2026, 12, 31)) == "20260930"


def test_codes_are_padded_trimmed_and_deduplicated():
    frame = pd.DataFrame(
        [
            {"code": "1", "value": 10},
            {"code": " 600000 ", "value": 20},
            {"code": "1", "value": 30},
        ]
    )

    result = _normalize_codes(frame)

    assert result["code"].tolist() == ["600000", "000001"]
    assert result.loc[result["code"] == "000001", "value"].item() == 30

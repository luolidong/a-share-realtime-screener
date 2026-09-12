import pytest
from fastapi import HTTPException

from app.main import build_rules


def test_runtime_rule_overrides():
    rules = build_rules(12, 25, 200_000_000, 40, 35)
    assert rules.turnover_min == 12
    assert rules.turnover_max == 25
    assert rules.net_inflow_min_cny == 200_000_000
    assert rules.net_profit_yoy_min == 40
    assert rules.revenue_yoy_min == 35


def test_invalid_turnover_range():
    with pytest.raises(HTTPException) as exc:
        build_rules(30, 10, None, None, None)
    assert exc.value.status_code == 422

import pandas as pd

from app.models import ScreeningRules
from app.providers.base import StockDataProvider
from app.screener import screen_stocks


class FakeProvider(StockDataProvider):
    def get_realtime_quotes(self):
        return pd.DataFrame([
            {"code": "000001", "name": "通过股", "price": 10, "pct_change": 3, "turnover_rate": 15},
            {"code": "000002", "name": "低换手", "price": 11, "pct_change": 2, "turnover_rate": 8},
            {"code": "000003", "name": "高换手", "price": 12, "pct_change": 1, "turnover_rate": 35},
            {"code": "000004", "name": "低资金", "price": 13, "pct_change": 4, "turnover_rate": 20},
        ])

    def get_realtime_money_flow(self):
        return pd.DataFrame([
            {"code": "000001", "net_inflow_cny": 150_000_000},
            {"code": "000002", "net_inflow_cny": 200_000_000},
            {"code": "000003", "net_inflow_cny": 200_000_000},
            {"code": "000004", "net_inflow_cny": 90_000_000},
        ])

    def get_financial_growth(self):
        return pd.DataFrame([
            {"code": "000001", "net_profit_yoy": 50, "revenue_yoy": 45},
            {"code": "000002", "net_profit_yoy": 50, "revenue_yoy": 45},
            {"code": "000003", "net_profit_yoy": 50, "revenue_yoy": 45},
            {"code": "000004", "net_profit_yoy": 50, "revenue_yoy": 45},
        ])


def test_all_conditions_are_required():
    result = screen_stocks(FakeProvider(), ScreeningRules())
    assert result["code"].tolist() == ["000001"]

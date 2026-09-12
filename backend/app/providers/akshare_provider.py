from __future__ import annotations

from datetime import date
import akshare as ak
import pandas as pd

from .base import StockDataProvider


def latest_reporting_period(today: date | None = None) -> str:
    today = today or date.today()
    y = today.year
    # Use the latest reporting period that should normally have broad disclosure coverage.
    if today.month >= 9:
        return f"{y}0630"
    if today.month >= 5:
        return f"{y}0331"
    return f"{y - 1}1231"


class AkShareProvider(StockDataProvider):
    def get_realtime_quotes(self) -> pd.DataFrame:
        df = ak.stock_zh_a_spot_em()
        out = df[["代码", "名称", "最新价", "涨跌幅", "换手率"]].copy()
        out.columns = ["code", "name", "price", "pct_change", "turnover_rate"]
        out["code"] = out["code"].astype(str).str.zfill(6)
        return out

    def get_realtime_money_flow(self) -> pd.DataFrame:
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        out = df[["代码", "今日主力净流入-净额"]].copy()
        out.columns = ["code", "net_inflow_cny"]
        out["code"] = out["code"].astype(str).str.zfill(6)
        return out

    def get_financial_growth(self) -> pd.DataFrame:
        period = latest_reporting_period()
        df = ak.stock_yjbb_em(date=period)
        out = df[["股票代码", "净利润-同比增长", "营业总收入-同比增长"]].copy()
        out.columns = ["code", "net_profit_yoy", "revenue_yoy"]
        out["code"] = out["code"].astype(str).str.zfill(6)
        return out

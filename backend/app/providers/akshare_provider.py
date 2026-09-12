from __future__ import annotations

from datetime import date, datetime, timedelta
from threading import Lock

import akshare as ak
import pandas as pd

from .base import StockDataProvider


def latest_reporting_period(today: date | None = None) -> str:
    today = today or date.today()
    y = today.year
    if today.month >= 9:
        return f"{y}0630"
    if today.month >= 5:
        return f"{y}0331"
    return f"{y - 1}1231"


class AkShareProvider(StockDataProvider):
    _financial_cache: pd.DataFrame | None = None
    _financial_cache_period: str | None = None
    _financial_cache_at: datetime | None = None
    _financial_cache_lock = Lock()
    financial_cache_ttl = timedelta(hours=6)

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
        now = datetime.now()
        cls = type(self)
        with cls._financial_cache_lock:
            cache_valid = (
                cls._financial_cache is not None
                and cls._financial_cache_period == period
                and cls._financial_cache_at is not None
                and now - cls._financial_cache_at < cls.financial_cache_ttl
            )
            if cache_valid:
                return cls._financial_cache.copy()

            df = ak.stock_yjbb_em(date=period)
            out = df[["股票代码", "净利润-同比增长", "营业总收入-同比增长"]].copy()
            out.columns = ["code", "net_profit_yoy", "revenue_yoy"]
            out["code"] = out["code"].astype(str).str.zfill(6)
            cls._financial_cache = out.copy()
            cls._financial_cache_period = period
            cls._financial_cache_at = now
            return out

    @classmethod
    def financial_cache_status(cls) -> dict:
        return {
            "period": cls._financial_cache_period,
            "cached_at": cls._financial_cache_at.isoformat() if cls._financial_cache_at else None,
            "ttl_seconds": int(cls.financial_cache_ttl.total_seconds()),
            "ready": cls._financial_cache is not None,
        }

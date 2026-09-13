from __future__ import annotations

from datetime import date, datetime, timedelta
from threading import Lock
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd

from .base import StockDataProvider

SHANGHAI = ZoneInfo("Asia/Shanghai")


def latest_reporting_period(today: date | None = None) -> str:
    """Return the newest quarterly period whose disclosure deadline has passed."""
    today = today or datetime.now(SHANGHAI).date()
    year = today.year
    if today.month >= 11:
        return f"{year}0930"
    if today.month >= 9:
        return f"{year}0630"
    if today.month >= 5:
        return f"{year}0331"
    return f"{year - 1}0930"


def _normalize_codes(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["code"] = frame["code"].astype(str).str.strip().str.zfill(6)
    return frame.drop_duplicates(subset=["code"], keep="last").reset_index(drop=True)


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
        return _normalize_codes(out)

    def get_realtime_money_flow(self) -> pd.DataFrame:
        df = ak.stock_individual_fund_flow_rank(indicator="今日")
        out = df[["代码", "今日主力净流入-净额"]].copy()
        out.columns = ["code", "net_inflow_cny"]
        return _normalize_codes(out)

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
            out = _normalize_codes(out)
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

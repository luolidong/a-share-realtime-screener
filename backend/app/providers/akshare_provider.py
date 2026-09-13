from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta
from threading import Lock
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd
import requests

from .base import StockDataProvider

SHANGHAI = ZoneInfo("Asia/Shanghai")

# The generic push2.eastmoney.com endpoint can close connections without a
# response on some networks. Prefer the numbered node that has been verified
# to work from the deployed Docker container.
EASTMONEY_CLIST_URLS = (
    "https://82.push2.eastmoney.com/api/qt/clist/get",
    "https://push2.eastmoney.com/api/qt/clist/get",
)
EASTMONEY_TIMEOUT_SECONDS = 15
EASTMONEY_RETRIES_PER_NODE = 3
# A-share universe is currently a little over 5,000 securities. Using a large
# page size avoids dozens of rapid requests, which can trigger Eastmoney to
# close the connection mid-pagination.
EASTMONEY_PAGE_SIZE = 5000


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


def _request_eastmoney_page(
    session: requests.Session,
    params: dict[str, str | int],
) -> dict:
    """Fetch one Eastmoney clist page with node failover and retries."""
    last_error: Exception | None = None

    for url in EASTMONEY_CLIST_URLS:
        for attempt in range(EASTMONEY_RETRIES_PER_NODE):
            try:
                # Deliberately do not add custom headers here: the same plain
                # requests.get call has been verified against the numbered node.
                response = session.get(
                    url,
                    params=params,
                    timeout=EASTMONEY_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("data") is None:
                    raise RuntimeError(f"Eastmoney returned no data: rc={payload.get('rc')}")
                return payload
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                last_error = exc
                if attempt + 1 < EASTMONEY_RETRIES_PER_NODE:
                    time.sleep(0.8 * (attempt + 1))

    raise RuntimeError(f"Eastmoney realtime API unavailable: {last_error}") from last_error


def _fetch_eastmoney_clist(params: dict[str, str | int]) -> pd.DataFrame:
    """Fetch the Eastmoney realtime stock list with minimal request count."""
    request_params = dict(params)
    request_params["pn"] = "1"
    request_params["pz"] = str(EASTMONEY_PAGE_SIZE)

    rows: list[dict] = []
    with requests.Session() as session:
        payload = _request_eastmoney_page(session, request_params)
        data = payload["data"]
        rows.extend(data.get("diff") or [])

        total = int(data.get("total") or len(rows))
        total_pages = max(1, math.ceil(total / EASTMONEY_PAGE_SIZE))
        for page in range(2, total_pages + 1):
            # Avoid a burst of back-to-back requests to the public endpoint.
            time.sleep(0.35)
            request_params["pn"] = str(page)
            page_payload = _request_eastmoney_page(session, request_params)
            rows.extend(page_payload["data"].get("diff") or [])

    return pd.DataFrame(rows)


class AkShareProvider(StockDataProvider):
    _financial_cache: pd.DataFrame | None = None
    _financial_cache_period: str | None = None
    _financial_cache_at: datetime | None = None
    _financial_cache_lock = Lock()
    financial_cache_ttl = timedelta(hours=6)

    def get_realtime_quotes(self) -> pd.DataFrame:
        df = _fetch_eastmoney_clist(
            {
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "fid": "f12",
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
                "fields": "f12,f14,f2,f3,f8",
            }
        )
        out = df[["f12", "f14", "f2", "f3", "f8"]].copy()
        out.columns = ["code", "name", "price", "pct_change", "turnover_rate"]
        return _normalize_codes(out)

    def get_realtime_money_flow(self) -> pd.DataFrame:
        # f62 is today's main-fund net inflow amount, in CNY.
        df = _fetch_eastmoney_clist(
            {
                "fid": "f62",
                "po": "1",
                "np": "1",
                "fltt": "2",
                "invt": "2",
                "ut": "b2884a393a59ad64002292a3e90d46a5",
                "fs": (
                    "m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,"
                    "m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2"
                ),
                "fields": "f12,f62",
            }
        )
        out = df[["f12", "f62"]].copy()
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

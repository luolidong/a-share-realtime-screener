from __future__ import annotations

import math
import random
import time
from datetime import date, datetime, timedelta
from threading import Lock
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd
from curl_cffi import requests as curl_requests

from .base import StockDataProvider

SHANGHAI = ZoneInfo("Asia/Shanghai")

# Eastmoney may reject/close plain requests on some networks. Prefer the
# webguest routes used by newer community clients, use browser-like TLS via
# curl_cffi, and keep several nodes as failover.
EASTMONEY_CLIST_URLS = (
    "https://82.push2.eastmoney.com/webguest/api/qt/clist/get",
    "https://73.push2.eastmoney.com/webguest/api/qt/clist/get",
    "https://push2.eastmoney.com/webguest/api/qt/clist/get",
    "https://82.push2.eastmoney.com/api/qt/clist/get",
)
EASTMONEY_TIMEOUT_SECONDS = 15
EASTMONEY_RETRIES_PER_NODE = 2
EASTMONEY_PAGE_SIZE = 100
EASTMONEY_MIN_TURNOVER = 10.0
REALTIME_SNAPSHOT_TTL = timedelta(seconds=15)


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
    session: curl_requests.Session,
    params: dict[str, str | int],
    preferred_url: str | None = None,
) -> tuple[dict, str]:
    """Fetch one Eastmoney page and return both payload and working URL."""
    urls = list(EASTMONEY_CLIST_URLS)
    if preferred_url in urls:
        urls.remove(preferred_url)
        urls.insert(0, preferred_url)

    last_error: Exception | None = None
    for url in urls:
        for attempt in range(EASTMONEY_RETRIES_PER_NODE):
            try:
                response = session.get(
                    url,
                    params=params,
                    timeout=EASTMONEY_TIMEOUT_SECONDS,
                    impersonate="chrome",
                    headers={
                        "Accept": "application/json,text/plain,*/*",
                        "Referer": "https://quote.eastmoney.com/",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("data") is None:
                    raise RuntimeError(f"Eastmoney returned no data: rc={payload.get('rc')}")
                return payload, url
            except Exception as exc:  # curl_cffi and JSON errors have different types
                last_error = exc
                if attempt + 1 < EASTMONEY_RETRIES_PER_NODE:
                    time.sleep(0.6 * (attempt + 1))

    raise RuntimeError(f"Eastmoney realtime API unavailable: {last_error}") from last_error


def _fetch_realtime_snapshot() -> pd.DataFrame:
    """Fetch only stocks that can satisfy the turnover rule, sorted by turnover.

    The screener requires turnover >= 10%, so the request sorts the whole market
    by turnover descending and stops as soon as a page crosses below 10%. This
    avoids pulling all ~5,500 stocks and sharply reduces public-API requests.
    """
    params: dict[str, str | int] = {
        "pn": "1",
        "pz": str(EASTMONEY_PAGE_SIZE),
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f8",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": "f12,f14,f2,f3,f8,f62",
    }

    rows: list[dict] = []
    preferred_url: str | None = None
    with curl_requests.Session() as session:
        for page in range(1, 100):
            params["pn"] = str(page)
            payload, preferred_url = _request_eastmoney_page(
                session,
                params,
                preferred_url=preferred_url,
            )
            page_rows = payload["data"].get("diff") or []
            if not page_rows:
                break

            rows.extend(page_rows)
            turnover = pd.to_numeric(
                pd.Series([row.get("f8") for row in page_rows]),
                errors="coerce",
            ).dropna()

            # Results are sorted by f8 descending. Once the current page reaches
            # below 10%, no later page can satisfy the screener's turnover rule.
            if turnover.empty or turnover.min() < EASTMONEY_MIN_TURNOVER:
                break

            total = int(payload["data"].get("total") or 0)
            if total and page * EASTMONEY_PAGE_SIZE >= total:
                break

            time.sleep(random.uniform(0.35, 0.7))

    if not rows:
        raise RuntimeError("Eastmoney realtime API returned no rows")

    frame = pd.DataFrame(rows)
    for column in ("f2", "f3", "f8", "f62"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[frame["f8"] >= EASTMONEY_MIN_TURNOVER].copy()
    return frame.reset_index(drop=True)


class AkShareProvider(StockDataProvider):
    _financial_cache: pd.DataFrame | None = None
    _financial_cache_period: str | None = None
    _financial_cache_at: datetime | None = None
    _financial_cache_lock = Lock()
    financial_cache_ttl = timedelta(hours=6)

    _realtime_cache: pd.DataFrame | None = None
    _realtime_cache_at: datetime | None = None
    _realtime_cache_lock = Lock()

    def _get_realtime_snapshot(self) -> pd.DataFrame:
        cls = type(self)
        now = datetime.now()
        with cls._realtime_cache_lock:
            cache_valid = (
                cls._realtime_cache is not None
                and cls._realtime_cache_at is not None
                and now - cls._realtime_cache_at < REALTIME_SNAPSHOT_TTL
            )
            if cache_valid:
                return cls._realtime_cache.copy()

            snapshot = _fetch_realtime_snapshot()
            cls._realtime_cache = snapshot.copy()
            cls._realtime_cache_at = now
            return snapshot

    def get_realtime_quotes(self) -> pd.DataFrame:
        df = self._get_realtime_snapshot()
        out = df[["f12", "f14", "f2", "f3", "f8"]].copy()
        out.columns = ["code", "name", "price", "pct_change", "turnover_rate"]
        return _normalize_codes(out)

    def get_realtime_money_flow(self) -> pd.DataFrame:
        # f62 is today's main-fund net inflow amount, in CNY. Reuse the same
        # realtime snapshot instead of downloading the market a second time.
        df = self._get_realtime_snapshot()
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

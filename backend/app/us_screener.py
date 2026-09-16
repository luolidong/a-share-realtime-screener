from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import akshare as ak
import pandas as pd


def _number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _symbol(code: str) -> str:
    return str(code).split(".", 1)[-1]


def _rvol(code: str, current_volume: float) -> float | None:
    try:
        end = date.today()
        start = end - timedelta(days=45)
        hist = ak.stock_us_hist(
            symbol=str(code),
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="",
        )
        if hist.empty or "成交量" not in hist.columns:
            return None
        volumes = _number(hist["成交量"]).dropna()
        if len(volumes) < 5:
            return None
        # The last row can be today's partial session; exclude it when possible.
        baseline = volumes.iloc[-21:-1] if len(volumes) >= 21 else volumes.iloc[:-1]
        avg = baseline.mean()
        if not avg or pd.isna(avg):
            return None
        return round(float(current_volume) / float(avg), 2)
    except Exception:
        return None


def screen_us_stocks(
    pct_min: float = 2.0,
    pct_max: float = 10.0,
    rvol_min: float = 1.5,
    amount_min_usd: float = 50_000_000.0,
    market_cap_min_usd: float = 1_000_000_000.0,
    limit: int = 100,
) -> list[dict]:
    df = ak.stock_us_spot_em().copy()
    if df.empty:
        return []

    for col in ["最新价", "涨跌幅", "成交量", "成交额", "总市值"]:
        df[col] = _number(df[col])

    df = df[
        df["涨跌幅"].between(pct_min, pct_max, inclusive="both")
        & (df["成交额"] >= amount_min_usd)
        & (df["总市值"] >= market_cap_min_usd)
        & df["最新价"].notna()
        & df["成交量"].notna()
    ].copy()

    # Calculate RVOL only for the most liquid pre-screened names to keep manual queries responsive.
    df = df.sort_values("成交额", ascending=False).head(max(limit * 2, 60))
    rvols: dict[str, float | None] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_rvol, row["代码"], row["成交量"]): str(row["代码"])
            for _, row in df.iterrows()
        }
        for future in as_completed(futures):
            rvols[futures[future]] = future.result()

    df["rvol"] = df["代码"].astype(str).map(rvols)
    df = df[df["rvol"].notna() & (df["rvol"] >= rvol_min)]
    df = df.sort_values(["rvol", "成交额"], ascending=False).head(limit)

    return [
        {
            "symbol": _symbol(row["代码"]),
            "name": str(row["名称"]),
            "price": None if pd.isna(row["最新价"]) else float(row["最新价"]),
            "pct_change": None if pd.isna(row["涨跌幅"]) else float(row["涨跌幅"]),
            "rvol": None if pd.isna(row["rvol"]) else float(row["rvol"]),
            "volume": None if pd.isna(row["成交量"]) else float(row["成交量"]),
            "amount_usd": None if pd.isna(row["成交额"]) else float(row["成交额"]),
            "market_cap_usd": None if pd.isna(row["总市值"]) else float(row["总市值"]),
        }
        for _, row in df.iterrows()
    ]

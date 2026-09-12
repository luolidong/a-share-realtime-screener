from __future__ import annotations

import pandas as pd

from .models import ScreeningRules
from .providers.base import StockDataProvider


REQUIRED_COLUMNS = {
    "code",
    "name",
    "price",
    "pct_change",
    "turnover_rate",
    "net_inflow_cny",
    "net_profit_yoy",
    "revenue_yoy",
}


def screen_stocks(provider: StockDataProvider, rules: ScreeningRules) -> pd.DataFrame:
    quotes = provider.get_realtime_quotes()
    flows = provider.get_realtime_money_flow()
    financials = provider.get_financial_growth()

    df = quotes.merge(flows, on="code", how="inner").merge(financials, on="code", how="inner")

    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"provider data missing columns: {sorted(missing)}")

    numeric_cols = [
        "price",
        "pct_change",
        "turnover_rate",
        "net_inflow_cny",
        "net_profit_yoy",
        "revenue_yoy",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    matched = df[
        df["turnover_rate"].between(rules.turnover_min, rules.turnover_max, inclusive="both")
        & (df["net_inflow_cny"] > rules.net_inflow_min_cny)
        & (df["net_profit_yoy"] >= rules.net_profit_yoy_min)
        & (df["revenue_yoy"] >= rules.revenue_yoy_min)
    ].copy()

    return matched.sort_values(["net_inflow_cny", "turnover_rate"], ascending=[False, False]).reset_index(drop=True)

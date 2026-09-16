from __future__ import annotations

from dataclasses import replace

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import load_rules
from .models import ScreeningRules, StockResult
from .providers.akshare_provider import AkShareProvider
from .screener import screen_stocks
from .us_screener import screen_us_stocks

provider = AkShareProvider()

app = FastAPI(title="A股 / 美股条件选股 API", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "financial_cache": provider.financial_cache_status()}


@app.get("/api/rules")
def rules() -> dict:
    return load_rules().__dict__


@app.get("/api/us/rules")
def us_rules() -> dict:
    return {
        "pct_min": 2.0,
        "pct_max": 10.0,
        "rvol_min": 1.5,
        "amount_min_usd": 50_000_000.0,
        "market_cap_min_usd": 1_000_000_000.0,
    }


def build_rules(turnover_min, turnover_max, net_inflow_min_cny, net_profit_yoy_min, revenue_yoy_min) -> ScreeningRules:
    base = load_rules()
    values = {
        "turnover_min": turnover_min,
        "turnover_max": turnover_max,
        "net_inflow_min_cny": net_inflow_min_cny,
        "net_profit_yoy_min": net_profit_yoy_min,
        "revenue_yoy_min": revenue_yoy_min,
    }
    active = replace(base, **{k: v for k, v in values.items() if v is not None})
    if active.turnover_min > active.turnover_max:
        raise HTTPException(status_code=422, detail="换手率最小值不能大于最大值")
    return active


@app.get("/api/stocks", response_model=list[StockResult])
def stocks(
    limit: int = Query(default=100, ge=1, le=500),
    turnover_min: float | None = Query(default=None, ge=0),
    turnover_max: float | None = Query(default=None, ge=0),
    net_inflow_min_cny: float | None = Query(default=None),
    net_profit_yoy_min: float | None = Query(default=None),
    revenue_yoy_min: float | None = Query(default=None),
) -> list[StockResult]:
    active_rules = build_rules(turnover_min, turnover_max, net_inflow_min_cny, net_profit_yoy_min, revenue_yoy_min)
    try:
        result = screen_stocks(provider, active_rules).head(limit)
        records = result.where(result.notna(), None).to_dict(orient="records")
        return [StockResult(**row) for row in records]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"数据源暂不可用: {exc}") from exc


@app.get("/api/us/stocks")
def us_stocks(
    limit: int = Query(default=100, ge=1, le=200),
    pct_min: float = Query(default=2.0),
    pct_max: float = Query(default=10.0),
    rvol_min: float = Query(default=1.5, ge=0),
    amount_min_usd: float = Query(default=50_000_000.0, ge=0),
    market_cap_min_usd: float = Query(default=1_000_000_000.0, ge=0),
) -> list[dict]:
    if pct_min > pct_max:
        raise HTTPException(status_code=422, detail="涨跌幅最小值不能大于最大值")
    try:
        return screen_us_stocks(pct_min, pct_max, rvol_min, amount_min_usd, market_cap_min_usd, limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"美股数据源暂不可用: {exc}") from exc

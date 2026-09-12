from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import load_rules
from .models import ScreeningRules, StockResult
from .providers.akshare_provider import AkShareProvider
from .scanner import BackgroundScanner
from .screener import screen_stocks
from .storage import get_active_matches, get_events, get_last_scan

provider = AkShareProvider()
scanner = BackgroundScanner(provider, interval_seconds=15)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await scanner.start()
    yield
    await scanner.stop()


app = FastAPI(title="A股实时条件选股 API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "financial_cache": provider.financial_cache_status(),
        "scanner": scanner.status(),
        "last_scan": get_last_scan(),
    }


@app.get("/api/scanner/status")
def scanner_status() -> dict:
    return {**scanner.status(), "last_scan": get_last_scan()}


@app.get("/api/scanner/active")
def scanner_active(limit: int = Query(default=500, ge=1, le=1000)) -> list[dict]:
    return get_active_matches(limit)


@app.get("/api/scanner/events")
def scanner_events(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
    return get_events(limit)


@app.post("/api/scanner/scan-now")
async def scanner_scan_now() -> dict:
    try:
        return await scanner.scan_once()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"扫描失败: {exc}") from exc


@app.get("/api/rules")
def rules() -> dict:
    return load_rules().__dict__


def build_rules(
    turnover_min: float | None,
    turnover_max: float | None,
    net_inflow_min_cny: float | None,
    net_profit_yoy_min: float | None,
    revenue_yoy_min: float | None,
) -> ScreeningRules:
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
    active_rules = build_rules(
        turnover_min,
        turnover_max,
        net_inflow_min_cny,
        net_profit_yoy_min,
        revenue_yoy_min,
    )
    try:
        result = screen_stocks(provider, active_rules).head(limit)
        records = result.where(result.notna(), None).to_dict(orient="records")
        return [StockResult(**row) for row in records]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"数据源暂不可用: {exc}") from exc

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import load_rules
from .models import StockResult
from .providers.akshare_provider import AkShareProvider
from .screener import screen_stocks

app = FastAPI(title="A股实时条件选股 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/rules")
def rules() -> dict:
    return load_rules().__dict__


@app.get("/api/stocks", response_model=list[StockResult])
def stocks(limit: int = Query(default=100, ge=1, le=500)) -> list[StockResult]:
    try:
        result = screen_stocks(AkShareProvider(), load_rules()).head(limit)
        return [StockResult(**row) for row in result.to_dict(orient="records")]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"数据源暂不可用: {exc}") from exc

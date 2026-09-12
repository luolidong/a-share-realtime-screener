from dataclasses import dataclass
from pydantic import BaseModel


@dataclass(frozen=True)
class ScreeningRules:
    turnover_min: float = 10.0
    turnover_max: float = 30.0
    net_inflow_min_cny: float = 100_000_000.0
    net_profit_yoy_min: float = 30.0
    revenue_yoy_min: float = 30.0


class StockResult(BaseModel):
    code: str
    name: str
    price: float | None = None
    pct_change: float | None = None
    turnover_rate: float | None = None
    net_inflow_cny: float | None = None
    net_profit_yoy: float | None = None
    revenue_yoy: float | None = None

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreeningRules:
    turnover_min: float = 10.0
    turnover_max: float = 30.0
    net_inflow_min_cny: float = 100_000_000.0
    net_profit_yoy_min: float = 30.0
    revenue_yoy_min: float = 30.0

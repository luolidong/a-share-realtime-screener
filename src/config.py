from pathlib import Path

import yaml

from .models import ScreeningRules


def load_rules(path: str | Path = "config.yaml") -> ScreeningRules:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    rules = data.get("rules", {})
    return ScreeningRules(
        turnover_min=float(rules.get("turnover_min", 10)),
        turnover_max=float(rules.get("turnover_max", 30)),
        net_inflow_min_cny=float(rules.get("net_inflow_min_cny", 100_000_000)),
        net_profit_yoy_min=float(rules.get("net_profit_yoy_min", 30)),
        revenue_yoy_min=float(rules.get("revenue_yoy_min", 30)),
    )

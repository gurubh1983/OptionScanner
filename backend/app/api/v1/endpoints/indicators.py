"""Indicator list and meta-indicator support."""

from fastapi import APIRouter, Depends

from app.indicators.library import INDICATOR_REGISTRY
from app.indicators.engine import IndicatorEngine
from app.api.v1.deps import get_indicator_engine

router = APIRouter()


@router.get("/list")
def list_indicators() -> dict[str, list[str]]:
    """Return full indicator library grouped by category."""
    categories = {
        "price": ["sma", "ema", "wma", "rsi", "macd", "atr", "obv"],
        "momentum": ["rsi", "macd", "cci", "roc", "mom"],
        "volume": ["obv", "cmf", "vwma", "vpt"],
        "volatility": ["atr", "iv_rank", "iv_percentile", "hv"],
        "options": ["pcr", "max_pain", "iv_skew", "oi_change", "delta", "gamma", "theta"],
    }
    return {"categories": categories, "all": list(INDICATOR_REGISTRY.keys())}


@router.get("/resolve")
def resolve_indicator(
    field: str,
    engine: IndicatorEngine = Depends(get_indicator_engine),
) -> dict[str, str]:
    """Resolve expression e.g. rsi(14), ema(close,20). Returns parsed name and args."""
    name, args = engine._parse_expression(field)
    return {"field": field, "name": name, "args": [str(a) for a in args]}

"""
Indicator Engine: resolve field expressions like rsi(14), ema(close,20).
Supports meta-indicators. build_series_from_candles() for real data from market data service.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from app.indicators.library import INDICATOR_REGISTRY, register_builtins

register_builtins()


def _to_array(x: Any) -> np.ndarray | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return np.array([x])
    if hasattr(x, "__len__"):
        return np.asarray(x)
    return np.array([x])


class IndicatorEngine:
    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}

    def _parse_expression(self, field: str) -> tuple[str, list[Any]]:
        field = field.strip()
        match = re.match(r"(\w+)\s*\((.*)\)\s*$", field)
        if match:
            name = match.group(1).lower()
            args_str = match.group(2)
            args: list[Any] = []
            for part in args_str.split(","):
                part = part.strip()
                if part.isdigit():
                    args.append(int(part))
                else:
                    args.append(part)
            return name, args
        return field.lower(), []

    def resolve(self, field: str, series: dict[str, Any]) -> Any:
        if field in series:
            return series[field]
        name, args = self._parse_expression(field)
        if name in INDICATOR_REGISTRY:
            fn = INDICATOR_REGISTRY[name]
            return fn(series, *args)
        if name in series:
            return series[name]
        return None

    def build_series_from_candles(self, candles: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Build OHLCV arrays and compute all registered indicators from candle list.
        Each candle: {ts, open, high, low, close, volume}.
        """
        if not candles:
            return self._empty_series()
        n = len(candles)
        open_ = np.array([float(c.get("open", 0)) for c in candles])
        high = np.array([float(c.get("high", 0)) for c in candles])
        low = np.array([float(c.get("low", 0)) for c in candles])
        close = np.array([float(c.get("close", 0)) for c in candles])
        volume = np.array([float(c.get("volume", 0)) for c in candles])
        series = {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
        for name in list(INDICATOR_REGISTRY.keys()):
            try:
                fn = INDICATOR_REGISTRY[name]
                res = fn(series)
                if res is not None:
                    series[name] = res
            except Exception:
                pass
        return series

    def _empty_series(self) -> dict[str, Any]:
        return {
            "open": np.array([]),
            "high": np.array([]),
            "low": np.array([]),
            "close": np.array([]),
            "volume": np.array([]),
        }

    def get_series(self, symbol: str, timeframe: str) -> dict[str, Any]:
        """Fallback: generate seed data when no market data provider is used."""
        cache_key = f"{symbol}:{timeframe}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        n = 100
        np.random.seed(hash(symbol + timeframe) % (2**32))
        close = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
        high = close + np.abs(np.random.randn(n)) * 0.3
        low = close - np.abs(np.random.randn(n)) * 0.3
        open_ = np.roll(close, 1)
        open_[0] = close[0]
        volume = (np.random.rand(n) * 1e6 + 1e5).astype(float)
        series = {"open": open_, "high": high, "low": low, "close": close, "volume": volume}
        for name in list(INDICATOR_REGISTRY.keys()):
            try:
                fn = INDICATOR_REGISTRY[name]
                res = fn(series)
                if res is not None:
                    series[name] = res
            except Exception:
                pass
        self._cache[cache_key] = series
        return series

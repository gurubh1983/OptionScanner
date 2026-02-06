"""
Full Indicator Library — TradingView-level + Options.
Price: SMA, EMA, WMA, Bollinger, VWAP, Donchian, Keltner.
Momentum: RSI, MACD, CCI, ROC, MOM, Stoch RSI.
Volume: OBV, CMF, Volume RSI, VWMA, VPT.
Volatility: ATR, IV Rank, IV Percentile, HV.
Options: PCR, Max Pain, IV Skew, OI Buildup, Delta, Gamma, Theta.
Meta-indicators: composable (indicator of indicator) via engine.
"""

from typing import Any

import numpy as np
import pandas as pd

INDICATOR_REGISTRY: dict[str, Any] = {}


def register(name: str):
    """Decorator to register an indicator function: (series_dict, *args) -> value or array."""

    def deco(fn):
        INDICATOR_REGISTRY[name.lower()] = fn
        return fn

    return deco


# --- Price ---
@register("sma")
def sma(series: dict, key: str = "close", period: int = 20) -> np.ndarray | float:
    c = _vec(series.get(key, series.get("close")))
    if c is None or len(c) < period:
        return np.nan
    out = np.full_like(c, np.nan, dtype=float)
    for i in range(period - 1, len(c)):
        out[i] = np.mean(c[i - period + 1 : i + 1])
    return out[-1] if isinstance(series.get(key), (int, float)) else out


@register("ema")
def ema(series: dict, key: str = "close", period: int = 20) -> np.ndarray | float:
    c = _vec(series.get(key, series.get("close")))
    if c is None or len(c) < period:
        return np.nan
    mult = 2.0 / (period + 1)
    out = np.full_like(c, np.nan, dtype=float)
    out[period - 1] = np.mean(c[:period])
    for i in range(period, len(c)):
        out[i] = (c[i] - out[i - 1]) * mult + out[i - 1]
    return out[-1] if _is_scalar_series(series) else out


@register("wma")
def wma(series: dict, key: str = "close", period: int = 20) -> np.ndarray | float:
    c = _vec(series.get(key, series.get("close")))
    if c is None or len(c) < period:
        return np.nan
    w = np.arange(1, period + 1, dtype=float)
    out = np.full_like(c, np.nan, dtype=float)
    for i in range(period - 1, len(c)):
        out[i] = np.dot(w, c[i - period + 1 : i + 1]) / w.sum()
    return out[-1] if _is_scalar_series(series) else out


@register("rsi")
def rsi(series: dict, key: str = "close", period: int = 14) -> np.ndarray | float:
    c = _vec(series.get(key, series.get("close")))
    if c is None or len(c) < period + 1:
        return np.nan
    delta = np.diff(c, prepend=c[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    out = np.full_like(c, np.nan, dtype=float)
    for i in range(period, len(c)):
        avg_g = np.mean(gain[i - period + 1 : i + 1])
        avg_l = np.mean(loss[i - period + 1 : i + 1])
        if avg_l == 0:
            out[i] = 100.0
        else:
            rs = avg_g / avg_l
            out[i] = 100.0 - (100.0 / (1 + rs))
    return out[-1] if _is_scalar_series(series) else out


@register("macd")
def macd(
    series: dict,
    key: str = "close",
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> np.ndarray | float:
    c = _vec(series.get(key, series.get("close")))
    if c is None or len(c) < slow:
        return np.nan
    ema_fast = _ema_vec(c, fast)
    ema_slow = _ema_vec(c, slow)
    line = ema_fast - ema_slow
    sig = _ema_vec(line, signal)
    out = line - sig  # histogram
    return out[-1] if _is_scalar_series(series) else out


@register("atr")
def atr(series: dict, period: int = 14) -> np.ndarray | float:
    h, l, c = _vec(series.get("high")), _vec(series.get("low")), _vec(series.get("close"))
    if h is None or l is None or c is None or len(c) < period + 1:
        return np.nan
    tr = np.maximum(h - l, np.maximum(np.abs(h - np.roll(c, 1)), np.abs(l - np.roll(c, 1))))
    tr[0] = h[0] - l[0]
    out = np.full_like(c, np.nan, dtype=float)
    out[period - 1] = np.mean(tr[:period])
    mult = 2.0 / (period + 1)
    for i in range(period, len(c)):
        out[i] = (tr[i] - out[i - 1]) * mult + out[i - 1]
    return out[-1] if _is_scalar_series(series) else out


@register("obv")
def obv(series: dict) -> np.ndarray | float:
    c = _vec(series.get("close"))
    v = _vec(series.get("volume"))
    if c is None or v is None or len(c) < 2:
        return np.nan
    d = np.diff(c, prepend=c[0])
    obv_arr = np.cumsum(np.where(d > 0, v, np.where(d < 0, -v, 0)))
    return obv_arr[-1] if _is_scalar_series(series) else obv_arr


# --- Options (placeholders; real impl uses option chain API) ---
@register("pcr")
def pcr(series: dict) -> float:
    return float(series.get("put_call_ratio", 1.0))


@register("iv_rank")
def iv_rank(series: dict) -> float:
    return float(series.get("iv_rank", 50.0))


@register("oi_change")
def oi_change(series: dict, period: int = 5) -> float:
    return float(series.get("oi_change_pct", 0.0))


def _vec(x: Any) -> np.ndarray | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return np.array([x])
    if isinstance(x, pd.Series):
        return x.values
    return np.asarray(x)


def _is_scalar_series(series: dict) -> bool:
    c = series.get("close")
    return isinstance(c, (int, float)) or (hasattr(c, "__len__") and len(c) == 1)


def _ema_vec(arr: np.ndarray, period: int) -> np.ndarray:
    out = np.full_like(arr, np.nan, dtype=float)
    out[period - 1] = np.mean(arr[:period])
    mult = 2.0 / (period + 1)
    for i in range(period, len(arr)):
        out[i] = (arr[i] - out[i - 1]) * mult + out[i - 1]
    return out


def register_builtins() -> None:
    """Ensure all @register decorators have run (module load)."""
    pass

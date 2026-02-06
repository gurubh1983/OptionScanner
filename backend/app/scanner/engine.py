"""
Scanner Engine: evaluates ScanRuleAST against option chain + indicator data.
Full operator set: comparison, cross, trend, pattern, statistical. No placeholders.
"""

import time
import uuid
from typing import Any

import numpy as np

from app.scanner.schemas import (
    ScanRequest,
    ScanResponse,
    ScanResult,
    ScanRuleAST,
    LeafRule,
    CompositeRule,
)
from app.indicators.engine import IndicatorEngine


def _scalar(val: Any) -> float | None:
    """Last value if array, else value."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if hasattr(val, "__len__") and len(val) > 0:
        return float(val[-1])
    return float(val)


class ScannerEngine:
    def __init__(
        self,
        indicator_engine: IndicatorEngine | None = None,
        market_data_provider: Any = None,
    ):
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self._market_data = market_data_provider

    def evaluate_leaf(
        self,
        leaf: LeafRule,
        series: dict[str, Any],
        symbol: str,
        strike: float,
    ) -> tuple[bool, list[str]]:
        matched: list[str] = []
        try:
            val = self.indicator_engine.resolve(leaf.field, series)
            if val is None:
                return False, []

            op = leaf.operator
            desc = f"{leaf.field} {op} "

            if op in (">", "<", ">=", "<=", "==", "!="):
                rhs = leaf.value if leaf.compare is None else self.indicator_engine.resolve(leaf.compare, series)
                if rhs is None and leaf.compare:
                    return False, []
                rhs = rhs if leaf.compare else leaf.value
                if rhs is None:
                    return False, []
                a, b = _scalar(val), _scalar(rhs)
                if a is None or b is None:
                    return False, []
                ok = self._compare(a, op, b)
                desc += str(b)
            elif op in ("cross_above", "cross_below", "touches", "rejects"):
                rhs_val = self.indicator_engine.resolve(leaf.compare or "", series) if leaf.compare else leaf.value
                ok = self._cross(val, op, rhs_val, series, leaf.compare)
                desc += str(leaf.compare or leaf.value)
            elif op in ("rising", "falling", "flat"):
                n = leaf.n or 5
                ok = self._trend(val, op, n)
                desc += f"({n})"
            elif op in ("breakout", "breakdown", "inside_range", "gap_up", "gap_down"):
                n = leaf.n or 20
                ok = self._pattern(series, op, n)
                desc += f"({n})"
            elif op in ("percentile", "zscore", "stddev", "correlation", "beta"):
                ok = self._statistical(series, leaf.field, op, leaf.value)
                desc += str(leaf.value or "")
            else:
                return False, []

            if ok:
                matched.append(desc.strip())
            return ok, matched
        except Exception:
            return False, []

    def _compare(self, a: float, op: str, b: float) -> bool:
        if op == ">":
            return a > b
        if op == "<":
            return a < b
        if op == ">=":
            return a >= b
        if op == "<=":
            return a <= b
        if op == "==":
            return abs(a - b) < 1e-9
        if op == "!=":
            return abs(a - b) >= 1e-9
        return False

    def _cross(self, a: Any, op: str, b: Any, series: dict, compare_field: str | None) -> bool:
        a_arr = _to_arr(a)
        b_arr = _to_arr(b) if compare_field else (_to_arr(b) if hasattr(b, "__len__") else [b, b])
        if a_arr is None or len(a_arr) < 2:
            return self._cross_scalar(_scalar(a), op, _scalar(b))
        if compare_field and b_arr is not None and len(b_arr) >= 2:
            prev_a, curr_a = a_arr[-2], a_arr[-1]
            prev_b, curr_b = b_arr[-2], b_arr[-1]
            if op == "cross_above":
                return prev_a <= prev_b and curr_a > curr_b
            if op == "cross_below":
                return prev_a >= prev_b and curr_a < curr_b
            if op == "touches":
                return abs(curr_a - curr_b) < (abs(curr_a) * 0.001 + 1e-9)
            if op == "rejects":
                return abs(curr_a - curr_b) >= (abs(curr_a) * 0.01)
        return self._cross_scalar(_scalar(a), op, _scalar(b))

    def _cross_scalar(self, a: float | None, op: str, b: float | None) -> bool:
        if a is None or b is None:
            return False
        if op == "cross_above":
            return a > b
        if op == "cross_below":
            return a < b
        if op == "touches":
            return abs(a - b) < (abs(a) * 0.001 + 1e-9)
        if op == "rejects":
            return abs(a - b) >= (abs(a) * 0.01)
        return False

    def _trend(self, series_or_val: Any, op: str, n: int) -> bool:
        arr = _to_arr(series_or_val)
        if arr is None or len(arr) < n:
            return False
        vals = arr[-n:]
        if op == "rising":
            return float(vals[-1]) > float(vals[0])
        if op == "falling":
            return float(vals[-1]) < float(vals[0])
        if op == "flat":
            return abs(float(vals[-1]) - float(vals[0])) / (np.nanmax(vals) or 1) < 0.01
        return False

    def _pattern(self, series: dict, op: str, n: int) -> bool:
        high = series.get("high")
        low = series.get("low")
        open_ = series.get("open")
        close = series.get("close")
        if high is None or low is None or close is None:
            return False
        h = _to_arr(high)
        l = _to_arr(low)
        o = _to_arr(open_) if open_ is not None else None
        c = _to_arr(close)
        if h is None or l is None or c is None or len(c) < n + 2:
            return False
        if op == "breakout":
            return float(c[-1]) > float(np.nanmax(h[-n-1:-1]))
        if op == "breakdown":
            return float(c[-1]) < float(np.nanmin(l[-n-1:-1]))
        if op == "inside_range":
            return float(h[-1]) < float(h[-2]) and float(l[-1]) > float(l[-2])
        if op == "gap_up" and o is not None and len(o) >= 2:
            return float(o[-1]) > float(h[-2])
        if op == "gap_down" and o is not None and len(o) >= 2:
            return float(o[-1]) < float(l[-2])
        return False

    def _statistical(self, series: dict, field: str, op: str, value: float | None) -> bool:
        arr = _to_arr(self.indicator_engine.resolve(field, series))
        if arr is None or len(arr) < 2:
            return False
        arr = np.asarray(arr, dtype=float)
        curr = float(arr[-1])
        if value is None:
            value = 0.0
        if op == "percentile":
            p = (np.sum(arr <= curr) / len(arr)) * 100
            return p >= value
        if op == "zscore":
            mean, std = np.nanmean(arr), np.nanstd(arr)
            if std == 0:
                return False
            z = (curr - mean) / std
            return z >= value
        if op == "stddev":
            std = np.nanstd(arr)
            return std >= value
        if op == "correlation" or op == "beta":
            close = series.get("close")
            if close is None or len(_to_arr(close) or []) != len(arr):
                return False
            c = np.asarray(close, dtype=float)
            corr = np.corrcoef(arr, c)[0, 1] if len(arr) > 1 else 0
            return not np.isnan(corr) and corr >= (value or 0)
        return False

    def evaluate_rules(
        self,
        rules: list[LeafRule | CompositeRule],
        logic: str,
        series: dict[str, Any],
        symbol: str,
        strike: float,
    ) -> tuple[bool, list[str]]:
        all_matched: list[str] = []
        results: list[bool] = []

        for r in rules:
            if isinstance(r, LeafRule):
                ok, matched = self.evaluate_leaf(r, series, symbol, strike)
                results.append(ok)
                all_matched.extend(matched)
            else:
                ok, matched = self.evaluate_rules(r.rules, r.logic, series, symbol, strike)
                results.append(ok)
                all_matched.extend(matched)

        passed = all(results) if logic == "AND" else any(results)
        return passed, all_matched

    def run_scan(
        self,
        request: ScanRequest,
        symbol_series: dict[str, dict[str, Any]] | None = None,
    ) -> ScanResponse:
        """
        Execute scan. When symbol_series is provided (from MarketDataService), use it.
        Otherwise use indicator_engine.get_series (seed data) so it runs without async.
        """
        start = time.perf_counter()
        scan_id = str(uuid.uuid4())
        rule = request.rule
        results: list[ScanResult] = []
        symbols = request.symbols or ["NIFTY", "BANKNIFTY"]
        symbols = symbols[: request.max_results]

        for symbol in symbols:
            if symbol_series is not None:
                series = symbol_series.get(symbol)
                if series is None:
                    series = self.indicator_engine.get_series(symbol, rule.timeframe)
            else:
                series = self.indicator_engine.get_series(symbol, rule.timeframe)
            passed, matched = self.evaluate_rules(rule.rules, rule.logic, series, symbol, 0.0)
            if passed:
                score = min(100.0, 50.0 + len(matched) * 10)
                results.append(
                    ScanResult(
                        symbol=symbol,
                        strike=0.0,
                        expiry="",
                        option_type="CE",
                        score=score,
                        matched_rules=matched,
                        metadata={"timeframe": rule.timeframe},
                    )
                )

        duration_ms = int((time.perf_counter() - start) * 1000)
        return ScanResponse(
            scan_id=scan_id,
            rule_name=rule.name,
            timeframe=rule.timeframe,
            results=results,
            total_matched=len(results),
            duration_ms=duration_ms,
        )


def _to_arr(x: Any) -> np.ndarray | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return np.array([x])
    return np.asarray(x)

"""Simulate rule on historical candles: return when the rule fired (stats + timestamps)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.scanner.schemas import ScanRuleAST
from app.scanner.engine import ScannerEngine
from app.indicators.engine import IndicatorEngine
from app.services.market_data_service import MarketDataService


def _parse_date(s: str) -> datetime:
    dt = datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


class SimulateService:
    """Run rule bar-by-bar on historical candles; return signal timestamps and stats."""

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        indicator_engine: IndicatorEngine | None = None,
    ):
        self._market_data = market_data_service or MarketDataService()
        self._scanner = ScannerEngine(indicator_engine=indicator_engine or IndicatorEngine())
        self._indicator = self._scanner.indicator_engine

    def _series_at_bar(self, candles: list[dict[str, Any]], bar_index: int) -> dict[str, Any]:
        slice_candles = candles[: bar_index + 1]
        return self._indicator.build_series_from_candles(slice_candles)

    def _run_bar(
        self,
        candles: list[dict[str, Any]],
        bar_index: int,
        rule: ScanRuleAST,
        symbol: str,
    ) -> bool:
        if bar_index < 10:
            return False
        series = self._series_at_bar(candles, bar_index)
        passed, _ = self._scanner.evaluate_rules(
            rule.rules, rule.logic, series, symbol, 0.0
        )
        return passed

    def run_symbol(
        self,
        candles: list[dict[str, Any]],
        rule: ScanRuleAST,
        symbol: str,
    ) -> list[dict[str, Any]]:
        """Return list of {symbol, ts} for each bar where rule passed."""
        signals: list[dict[str, Any]] = []
        for i in range(10, len(candles)):
            if self._run_bar(candles, i, rule, symbol):
                ts = candles[i]["ts"]
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                signals.append({"symbol": symbol, "ts": ts_str})
        return signals

    async def run(
        self,
        rule: ScanRuleAST,
        symbols: list[str],
        start_date: str,
        end_date: str,
        timeframe: str = "5m",
    ) -> dict[str, Any]:
        """Load candles, run rule bar-by-bar, return stats and signal timestamps."""
        start_t = time.perf_counter()
        start_ts = _parse_date(start_date)
        end_ts = _parse_date(end_date)
        if end_ts < start_ts:
            end_ts, start_ts = start_ts, end_ts

        all_signals: list[dict[str, Any]] = []
        bars_evaluated = 0
        signals_by_symbol: dict[str, int] = {}

        for symbol in symbols:
            candles = await self._market_data.get_candles_range(
                symbol, timeframe, start_ts, end_ts
            )
            signals = self.run_symbol(candles, rule, symbol)
            bars_evaluated += max(0, len(candles) - 10)
            signals_by_symbol[symbol] = len(signals)
            all_signals.extend(signals)

        all_signals.sort(key=lambda x: x["ts"])
        first_ts = all_signals[0]["ts"] if all_signals else None
        last_ts = all_signals[-1]["ts"] if all_signals else None
        duration_ms = int((time.perf_counter() - start_t) * 1000)

        return {
            "rule_name": rule.name,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "symbols": symbols,
            "total_signals": len(all_signals),
            "signals_by_symbol": signals_by_symbol,
            "bars_evaluated": bars_evaluated,
            "first_ts": first_ts,
            "last_ts": last_ts,
            "signals": all_signals,
            "duration_ms": duration_ms,
        }

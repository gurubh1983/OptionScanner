"""
Backtest engine: run scan rule bar-by-bar on historical candles (TimescaleDB).
Compute win rate, PnL, max drawdown, Sharpe, expectancy.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.scanner.schemas import ScanRuleAST, LeafRule, CompositeRule
from app.scanner.engine import ScannerEngine
from app.indicators.engine import IndicatorEngine
from app.backtest.schemas import (
    BacktestRequest,
    BacktestResponse,
    BacktestMetrics,
    TradeRecord,
)


class BacktestEngine:
    """Run rule on historical candles; record trades; compute metrics."""

    def __init__(self, indicator_engine: IndicatorEngine | None = None):
        self._scanner = ScannerEngine(indicator_engine=indicator_engine or IndicatorEngine())
        self._indicator = self._scanner.indicator_engine

    def _series_at_bar(self, candles: list[dict[str, Any]], bar_index: int) -> dict[str, Any]:
        """Build OHLCV series up to and including bar_index (no lookahead)."""
        slice_candles = candles[: bar_index + 1]
        return self._indicator.build_series_from_candles(slice_candles)

    def _run_bar(
        self,
        candles: list[dict[str, Any]],
        bar_index: int,
        rule: ScanRuleAST,
        symbol: str,
    ) -> bool:
        """Evaluate rule at bar_index. Returns True if signal (enter long)."""
        if bar_index < 10:
            return False
        series = self._series_at_bar(candles, bar_index)
        passed, _ = self._scanner.evaluate_rules(
            rule.rules, rule.logic, series, symbol, 0.0
        )
        return passed

    def _run_symbol(
        self,
        candles: list[dict[str, Any]],
        rule: ScanRuleAST,
        symbol: str,
        exit_after_bars: int,
        initial_capital: float,
        position_size_pct: float,
        allow_short: bool,
    ) -> tuple[list[TradeRecord], list[tuple[str, float]]]:
        """Run backtest on one symbol. Returns (trades, equity_points)."""
        trades: list[TradeRecord] = []
        equity = initial_capital
        equity_points: list[tuple[str, float]] = []
        position: dict[str, Any] | None = None  # {entry_bar, entry_price, entry_ts}
        n = len(candles)
        for i in range(10, n):
            close = candles[i]["close"]
            ts = candles[i]["ts"]
            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            if position is None:
                if self._run_bar(candles, i, rule, symbol):
                    position = {
                        "entry_bar": i,
                        "entry_price": close,
                        "entry_ts": ts_str,
                        "side": "long",
                    }
            else:
                bars_held = i - position["entry_bar"]
                exit_signal = bars_held >= exit_after_bars
                if exit_signal:
                    entry_price = position["entry_price"]
                    pnl = (close - entry_price) * (1 if position["side"] == "long" else -1)
                    size = initial_capital * (position_size_pct / 100.0)
                    pnl_amount = (pnl / entry_price) * size
                    pnl_pct = (close - entry_price) / entry_price * 100
                    equity += pnl_amount
                    trades.append(
                        TradeRecord(
                            symbol=symbol,
                            entry_ts=position["entry_ts"],
                            exit_ts=ts_str,
                            entry_price=entry_price,
                            exit_price=close,
                            side=position["side"],
                            pnl=pnl_amount,
                            pnl_pct=pnl_pct,
                            bars_held=bars_held,
                        )
                    )
                    position = None
            equity_points.append((ts_str, equity))
        if position is not None:
            i = n - 1
            close = candles[i]["close"]
            ts = candles[i]["ts"]
            ts_str = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            entry_price = position["entry_price"]
            pnl = (close - entry_price) * (1 if position["side"] == "long" else -1)
            size = initial_capital * (position_size_pct / 100.0)
            pnl_amount = (pnl / entry_price) * size
            pnl_pct = (close - entry_price) / entry_price * 100
            equity += pnl_amount
            trades.append(
                TradeRecord(
                    symbol=symbol,
                    entry_ts=position["entry_ts"],
                    exit_ts=ts_str,
                    entry_price=entry_price,
                    exit_price=close,
                    side=position["side"],
                    pnl=pnl_amount,
                    pnl_pct=pnl_pct,
                    bars_held=i - position["entry_bar"],
                )
            )
        return trades, equity_points

    def _compute_metrics(
        self,
        trades: list[TradeRecord],
        initial_capital: float,
        final_equity: float,
        equity_curve: list[dict[str, Any]],
    ) -> BacktestMetrics:
        """Compute win rate, PnL, max drawdown, Sharpe, expectancy."""
        total = len(trades)
        if total == 0:
            return BacktestMetrics(
                total_trades=0,
                total_pnl=final_equity - initial_capital,
                total_pnl_pct=((final_equity - initial_capital) / initial_capital * 100) if initial_capital else 0,
            )
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total * 100) if total else 0
        total_pnl = final_equity - initial_capital
        total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital else 0
        avg_win = (sum(t.pnl for t in wins) / winning_trades) if winning_trades else 0
        avg_loss = (sum(t.pnl for t in losses) / losing_trades) if losing_trades else 0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss else (gross_profit or 0)
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * abs(avg_loss)) if avg_loss else avg_win

        equity_vals = [p["equity"] for p in equity_curve] if equity_curve else [initial_capital, final_equity]
        peak = equity_vals[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        for eq in equity_vals:
            if eq > peak:
                peak = eq
            dd = peak - eq
            dd_pct = (dd / peak * 100) if peak else 0
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]["equity"]
            curr = equity_curve[i]["equity"]
            if prev > 0:
                returns.append((curr - prev) / prev)
        sharpe = 0.0
        if len(returns) > 1:
            arr = np.array(returns)
            rf = 0.0
            excess = arr - rf
            if np.std(excess) > 0:
                sharpe = float(np.mean(excess) / np.std(excess) * np.sqrt(252 * 24 * 12))

        return BacktestMetrics(
            total_trades=total,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl_pct, 2),
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            sharpe_ratio=round(sharpe, 2),
            expectancy=round(expectancy, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
        )

    def run(
        self,
        request: BacktestRequest,
        candles_by_symbol: dict[str, list[dict[str, Any]]],
    ) -> BacktestResponse:
        """Run backtest given per-symbol candles. Caller loads candles from MarketDataService."""
        start = time.perf_counter()
        backtest_id = str(uuid.uuid4())
        all_trades: list[TradeRecord] = []
        capital_per_symbol = request.initial_capital / len(request.symbols)
        equity_curve_agg: list[dict[str, Any]] = []
        time_equity: dict[str, float] = {}

        for symbol in request.symbols:
            candles = candles_by_symbol.get(symbol)
            if not candles:
                continue
            trades, _ = self._run_symbol(
                candles=candles,
                rule=request.rule,
                symbol=symbol,
                exit_after_bars=request.exit_after_bars,
                initial_capital=capital_per_symbol,
                position_size_pct=request.position_size_pct,
                allow_short=request.allow_short,
            )
            all_trades.extend(trades)

        all_trades.sort(key=lambda t: t.exit_ts)
        running = request.initial_capital
        equity_curve_agg.append({"ts": request.start_date, "equity": round(running, 2)})
        for t in all_trades:
            running += t.pnl
            equity_curve_agg.append({"ts": t.exit_ts, "equity": round(running, 2)})
        final_equity = running

        metrics = self._compute_metrics(
            all_trades,
            request.initial_capital,
            final_equity,
            equity_curve_agg,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        return BacktestResponse(
            backtest_id=backtest_id,
            rule_name=request.rule.name,
            start_date=request.start_date,
            end_date=request.end_date,
            timeframe=request.timeframe,
            symbols=request.symbols,
            initial_capital=request.initial_capital,
            final_equity=round(final_equity, 2),
            metrics=metrics,
            trades=sorted(all_trades, key=lambda t: t.entry_ts),
            equity_curve=equity_curve_agg,
            duration_ms=duration_ms,
        )

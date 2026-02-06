"""Backtest API and result schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.scanner.schemas import ScanRuleAST


class BacktestRequest(BaseModel):
    """Request to run a backtest."""

    rule: ScanRuleAST
    symbols: list[str] = Field(default_factory=lambda: ["NIFTY", "BANKNIFTY"], min_length=1, max_length=20)
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    timeframe: str = Field("5m", description="5m, 15m, 1h, 1d")
    initial_capital: float = Field(100_000.0, ge=100)
    position_size_pct: float = Field(10.0, ge=1, le=100, description="% of capital per trade")
    exit_after_bars: int = Field(5, ge=1, le=500, description="Hold N bars then exit")
    allow_short: bool = Field(False, description="Allow short positions")


class TradeRecord(BaseModel):
    """Single trade for report."""

    symbol: str
    entry_ts: str
    exit_ts: str
    entry_price: float
    exit_price: float
    side: str = "long"
    pnl: float
    pnl_pct: float
    bars_held: int


class BacktestMetrics(BaseModel):
    """Aggregate backtest metrics."""

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    expectancy: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0


class BacktestResponse(BaseModel):
    """Full backtest result."""

    backtest_id: str
    rule_name: str
    start_date: str
    end_date: str
    timeframe: str
    symbols: list[str]
    initial_capital: float
    final_equity: float
    metrics: BacktestMetrics
    trades: list[TradeRecord] = Field(default_factory=list)
    equity_curve: list[dict[str, Any]] = Field(default_factory=list, description="[{ts, equity}] for charts")
    duration_ms: int = 0

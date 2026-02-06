"""Backtest service: load candles from TimescaleDB and run backtest engine."""

from __future__ import annotations

from datetime import datetime, timezone

from app.backtest.engine import BacktestEngine
from app.backtest.schemas import BacktestRequest, BacktestResponse
from app.services.market_data_service import MarketDataService


def _parse_date(s: str) -> datetime:
    """Parse YYYY-MM-DD to UTC datetime at start of day."""
    dt = datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


class BacktestService:
    def __init__(self, market_data_service: MarketDataService | None = None):
        self._market_data = market_data_service or MarketDataService()
        self._engine = BacktestEngine()

    async def run(self, request: BacktestRequest) -> BacktestResponse:
        """Load candles for date range from TimescaleDB and run backtest."""
        start_ts = _parse_date(request.start_date)
        end_ts = _parse_date(request.end_date)
        if end_ts < start_ts:
            end_ts, start_ts = start_ts, end_ts
        candles_by_symbol: dict[str, list] = {}
        for symbol in request.symbols:
            candles = await self._market_data.get_candles_range(
                symbol, request.timeframe, start_ts, end_ts
            )
            candles_by_symbol[symbol] = candles
        return self._engine.run(request, candles_by_symbol)

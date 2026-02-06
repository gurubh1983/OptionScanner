"""Market data service: candles from TimescaleDB or broker. Single entry for scanner/indicators."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.adapters.market_data import TimescaleDBMarketDataAdapter
from app.adapters.broker import BrokerAdapterRegistry


class MarketDataService:
    """Unified market data: tries broker when configured, else TimescaleDB, else seed data."""

    def __init__(self):
        self._timescale = TimescaleDBMarketDataAdapter()
        self._broker = BrokerAdapterRegistry.get_adapter()

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        end_ts: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get OHLCV. Prefer broker if it returns data, else TimescaleDB, else seed."""
        end_ts = end_ts or datetime.now(timezone.utc)
        broker_candles = await self._broker.get_candles(symbol, timeframe, limit)
        if broker_candles:
            return self._normalize_candles(broker_candles)
        return await self._timescale.get_candles(symbol, timeframe, limit, end_ts)

    async def get_candles_range(
        self,
        symbol: str,
        timeframe: str,
        start_ts: datetime,
        end_ts: datetime,
    ) -> list[dict[str, Any]]:
        """Get OHLCV in date range for backtest/replay. Uses TimescaleDB (or seed)."""
        return await self._timescale.get_candles_range(symbol, timeframe, start_ts, end_ts)

    def _normalize_candles(self, rows: list) -> list[dict[str, Any]]:
        """Normalize broker format to {ts, open, high, low, close, volume}."""
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append({
                    "ts": r.get("ts") or r.get("timestamp") or r.get("date"),
                    "open": float(r.get("open", 0)),
                    "high": float(r.get("high", 0)),
                    "low": float(r.get("low", 0)),
                    "close": float(r.get("close", 0)),
                    "volume": float(r.get("volume", 0)),
                })
            else:
                out.append({
                    "ts": r[0] if len(r) > 0 else None,
                    "open": float(r[1]) if len(r) > 1 else 0,
                    "high": float(r[2]) if len(r) > 2 else 0,
                    "low": float(r[3]) if len(r) > 3 else 0,
                    "close": float(r[4]) if len(r) > 4 else 0,
                    "volume": float(r[5]) if len(r) > 5 else 0,
                })
        return out

    async def get_option_chain(self, symbol: str) -> dict[str, Any]:
        """Option chain from broker or placeholder."""
        return await self._broker.get_option_chain(symbol)

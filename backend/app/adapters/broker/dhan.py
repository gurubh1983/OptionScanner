"""Dhan broker adapter. Pluggable via BROKER_ADAPTER=dhan."""

from __future__ import annotations

from typing import Any

from app.adapters.broker.base import BaseBrokerAdapter, BrokerAdapterRegistry
from app.adapters.broker.feed_dhan import DhanFeed
from app.core.config import settings


@BrokerAdapterRegistry.register("dhan")
class DhanBrokerAdapter(BaseBrokerAdapter):
    def get_name(self) -> str:
        return "dhan"

    def _has_credentials(self) -> bool:
        return bool(getattr(settings, "dhan_api_key", None))

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        if not self._has_credentials():
            return []
        try:
            import httpx
            api_key = getattr(settings, "dhan_api_key", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.dhan.co/v2/charts/historical",
                    params={"symbol": symbol, "interval": timeframe, "count": limit},
                    headers={"access-token": api_key},
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("candles", []) or []
        except Exception:
            pass
        return []

    async def get_option_chain(self, symbol: str) -> dict[str, Any]:
        if not self._has_credentials():
            return {"symbol": symbol, "strikes": [], "pcr": 1.0}
        try:
            import httpx
            api_key = getattr(settings, "dhan_api_key", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.dhan.co/v2/optionchain",
                    params={"symbol": symbol},
                    headers={"access-token": api_key},
                )
                if r.status_code == 200:
                    return r.json().get("data", {}) or {"symbol": symbol, "strikes": [], "pcr": 1.0}
        except Exception:
            pass
        return {"symbol": symbol, "strikes": [], "pcr": 1.0}

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    def get_feed_class(self) -> type[DhanFeed] | None:
        return DhanFeed

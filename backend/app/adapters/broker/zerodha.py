"""Zerodha broker adapter. Pluggable via BROKER_ADAPTER=zerodha."""

from __future__ import annotations

from typing import Any

from app.adapters.broker.base import BaseBrokerAdapter, BrokerAdapterRegistry
from app.adapters.broker.feed_zerodha import ZerodhaFeed
from app.core.config import settings


@BrokerAdapterRegistry.register("zerodha")
class ZerodhaBrokerAdapter(BaseBrokerAdapter):
    def get_name(self) -> str:
        return "zerodha"

    def _has_credentials(self) -> bool:
        return bool(getattr(settings, "zerodha_api_key", None))

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
            api_key = getattr(settings, "zerodha_api_key", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.kite.trade/instruments/historical",
                    params={"instrument_token": symbol, "interval": timeframe, "limit": limit},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("data", {}).get("candles", []) or []
        except Exception:
            pass
        return []

    async def get_option_chain(self, symbol: str) -> dict[str, Any]:
        if not self._has_credentials():
            return {"symbol": symbol, "strikes": [], "pcr": 1.0}
        try:
            import httpx
            api_key = getattr(settings, "zerodha_api_key", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://api.kite.trade/optionchain",
                    params={"symbol": symbol},
                    headers={"Authorization": f"Bearer {api_key}"},
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

    def get_feed_class(self) -> type[ZerodhaFeed] | None:
        return ZerodhaFeed

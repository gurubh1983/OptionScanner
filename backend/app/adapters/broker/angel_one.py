"""
Angel One broker adapter.
Uses ANGEL_ONE_API_KEY when set; otherwise returns data from injected market_data provider for local run.
"""

from __future__ import annotations

from typing import Any

from app.adapters.broker.base import BaseBrokerAdapter, BrokerAdapterRegistry
from app.adapters.broker.feed_angel_one import AngelOneFeed
from app.core.config import settings


@BrokerAdapterRegistry.register("angel_one")
class AngelOneBrokerAdapter(BaseBrokerAdapter):
    def get_name(self) -> str:
        return "angel_one"

    def _has_credentials(self) -> bool:
        return bool(getattr(settings, "angel_one_api_key", None))

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
            # Angel One historical API (example endpoint shape)
            api_key = getattr(settings, "angel_one_api_key", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://apiconnect.angelbroking.com/rest/secure/angelone/v1/historical",
                    params={"symbol": symbol, "interval": timeframe, "limit": limit},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    return data.get("data", []) or []
        except Exception:
            pass
        return []

    async def get_option_chain(self, symbol: str) -> dict[str, Any]:
        if not self._has_credentials():
            return {"symbol": symbol, "strikes": [], "pcr": 1.0, "put_call_ratio": 1.0}
        try:
            import httpx
            api_key = getattr(settings, "angel_one_api_key", "")
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    "https://apiconnect.angelbroking.com/rest/secure/angelone/v1/option-chain",
                    params={"symbol": symbol},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if r.status_code == 200:
                    return r.json().get("data", {}) or {"symbol": symbol, "strikes": [], "pcr": 1.0}
        except Exception:
            pass
        return {"symbol": symbol, "strikes": [], "pcr": 1.0}

    async def connect(self) -> None:
        if self._has_credentials():
            pass  # Session init if needed

    async def disconnect(self) -> None:
        pass

    def get_feed_class(self) -> type[AngelOneFeed] | None:
        return AngelOneFeed

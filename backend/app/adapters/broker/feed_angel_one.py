"""
Angel One (SmartAPI) hardened WebSocket feed.
WebSocket reconnect, token refresh, heartbeat, lag detection, fallback, auto resubscribe.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from app.core.config import settings
from app.adapters.broker.feed_base import HardenedFeedBase


class AngelOneFeed(HardenedFeedBase):
    """Angel One live feed with pipeline hardening."""

    # Angel One SmartAPI WebSocket (typical pattern)
    WS_URL = "wss://smartapisocket.angelone.in/smart-api-ws"
    HEARTBEAT_MODE = "ping"  # or broker-specific

    def __init__(self) -> None:
        super().__init__("angel_one")
        self._access_token: str = getattr(settings, "angel_one_api_key", "") or ""
        self._token_expiry_ts: float = 0.0

    def _has_credentials(self) -> bool:
        return bool(self._access_token)

    async def _ws_connect(self) -> ClientConnection:
        if not self._has_credentials():
            raise RuntimeError("Angel One credentials not set")
        ws = await websockets.connect(
            self.WS_URL,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
            extra_headers={"Authorization": f"Bearer {self._access_token}"},
        )
        return ws

    async def _ws_send(self, ws: Any, data: str | bytes | dict) -> None:
        if isinstance(data, dict):
            data = json.dumps(data)
        if isinstance(data, str):
            data = data.encode("utf-8")
        await ws.send(data)

    async def _ws_recv(self, ws: Any) -> str | bytes | None:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=self.heartbeat_interval * 2)
            return msg
        except asyncio.TimeoutError:
            return ""  # keep connection alive, no message
        except websockets.exceptions.ConnectionClosed:
            return None
        except Exception:
            return None

    async def _ws_close(self, ws: Any) -> None:
        await ws.close()

    def _build_subscribe_message(self, symbols: list[str]) -> dict | None:
        # Angel One subscribe format (example)
        return {
            "mode": "LTP",
            "tokenList": [{"exchangeType": 1, "tradingSymbol": s} for s in symbols],
        }

    def _is_heartbeat_message(self, raw: str | bytes) -> bool:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        if not raw or not raw.strip():
            return True
        try:
            d = json.loads(raw)
            return d.get("type") == "pong" or d.get("heartbeat") is True
        except Exception:
            return False

    def _get_token_expiry_ts(self) -> float:
        return self._token_expiry_ts

    async def _refresh_token(self) -> bool:
        try:
            import httpx
            # Angel One token refresh endpoint (example)
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    "https://apiconnect.angelbroking.com/rest/auth/angel-api/v1/login",
                    json={"clientcode": "", "password": ""},  # Use refresh token in production
                )
                if r.status_code == 200:
                    data = r.json()
                    self._access_token = data.get("data", {}).get("jwtToken", "") or self._access_token
                    # Set expiry from JWT or default 1h
                    self._token_expiry_ts = time.time() + 3600
                    return True
        except Exception:
            pass
        return False

    async def _send_heartbeat(self) -> None:
        if self._ws:
            await self._ws_send(self._ws, {"type": "ping"})

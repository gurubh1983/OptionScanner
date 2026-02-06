"""
Zerodha (Kite) hardened WebSocket feed.
Reconnect, token refresh, heartbeat, lag detection, fallback, auto resubscribe.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import websockets

from app.core.config import settings
from app.adapters.broker.feed_base import HardenedFeedBase


class ZerodhaFeed(HardenedFeedBase):
    """Zerodha Kite live feed with pipeline hardening."""

    WS_URL = "wss://ws.kite.trade"

    def __init__(self) -> None:
        super().__init__("zerodha")
        self._api_key: str = getattr(settings, "zerodha_api_key", "") or ""
        self._access_token: str = ""
        self._token_expiry_ts: float = 0.0

    def _has_credentials(self) -> bool:
        return bool(self._api_key)

    async def _ws_connect(self) -> Any:
        if not self._has_credentials():
            raise RuntimeError("Zerodha credentials not set")
        # Kite WS expects api_key and access_token in first message; connect then send login
        ws = await websockets.connect(
            self.WS_URL,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        )
        # Send login packet (Kite format)
        await self._ws_send(ws, {
            "a": "login",
            "api_key": self._api_key,
            "access_token": self._access_token or self._api_key,
            "request_id": "login",
        })
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
            return ""
        except websockets.exceptions.ConnectionClosed:
            return None
        except Exception:
            return None

    async def _ws_close(self, ws: Any) -> None:
        await ws.close()

    def _build_subscribe_message(self, symbols: list[str]) -> dict | None:
        # Kite subscribe: tokens or instrument_tokens
        return {"a": "subscribe", "v": symbols}

    def _is_heartbeat_message(self, raw: str | bytes) -> bool:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        if not raw or not raw.strip():
            return True
        try:
            d = json.loads(raw)
            return d.get("type") == "pong" or d.get("a") == "pong"
        except Exception:
            return False

    def _get_token_expiry_ts(self) -> float:
        return self._token_expiry_ts

    async def _refresh_token(self) -> bool:
        try:
            import httpx
            # Kite session refresh (use refresh_token in production)
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    "https://api.kite.trade/session/refresh",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    self._access_token = data.get("access_token", "") or self._access_token
                    self._token_expiry_ts = time.time() + 3600
                    return True
        except Exception:
            pass
        return False

    async def _send_heartbeat(self) -> None:
        if self._ws:
            await self._ws_send(self._ws, {"a": "ping"})

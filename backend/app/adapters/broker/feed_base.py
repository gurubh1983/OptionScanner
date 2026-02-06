"""
Hardened market data pipeline base: WebSocket reconnect, token refresh,
heartbeat, lag detection, fallback feed, auto resubscribe.
All broker adapters can extend this for live feeds.
"""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable

from app.core.config import settings
from app.adapters.broker.monitoring import (
    log_connect,
    log_disconnect,
    log_reconnect,
    log_heartbeat,
    log_lag,
    log_token_refresh,
    log_fallback,
    log_resubscribe,
)


class HardenedFeedBase(ABC):
    """
    Base for live WebSocket feeds with:
    - Reconnect with exponential backoff
    - Token refresh before expiry
    - Heartbeat (ping/pong or broker heartbeat)
    - Lag detection (alert when last message too old)
    - Fallback flag (consumer can switch to REST)
    - Auto resubscribe on reconnect
    """

    def __init__(self, adapter_name: str) -> None:
        self.adapter_name = adapter_name
        self._ws: Any = None
        self._running = False
        self._last_message_ts: float = 0.0
        self._subscribed_symbols: list[str] = []
        self._reconnect_attempt = 0
        self._fallback_active = False
        self._token_expiry_ts: float = 0.0
        self._heartbeat_task: asyncio.Task[Any] | None = None
        self._lag_task: asyncio.Task[Any] | None = None
        self._recv_task: asyncio.Task[Any] | None = None
        self._lock = asyncio.Lock()

        self.heartbeat_interval = getattr(settings, "feed_heartbeat_interval_sec", 30.0)
        self.lag_threshold = getattr(settings, "feed_lag_threshold_sec", 60.0)
        self.reconnect_max = getattr(settings, "feed_reconnect_max_retries", 10)
        self.reconnect_base = getattr(settings, "feed_reconnect_base_delay_sec", 1.0)
        self.reconnect_max_delay = getattr(settings, "feed_reconnect_max_delay_sec", 120.0)
        self.token_refresh_before = getattr(settings, "feed_token_refresh_before_expiry_sec", 300)
        self.fallback_enabled = getattr(settings, "feed_fallback_enabled", True)

    def _reconnect_delay(self) -> float:
        """Exponential backoff with cap."""
        delay = min(
            self.reconnect_base * (2 ** self._reconnect_attempt),
            self.reconnect_max_delay,
        )
        return delay

    @abstractmethod
    async def _ws_connect(self) -> Any:
        """Return connected WebSocket (or similar) instance."""
        ...

    @abstractmethod
    async def _ws_send(self, ws: Any, data: str | bytes | dict) -> None:
        """Send data on WebSocket."""
        ...

    @abstractmethod
    async def _ws_recv(self, ws: Any) -> str | bytes | None:
        """Receive one message; return None on close."""
        ...

    @abstractmethod
    async def _ws_close(self, ws: Any) -> None:
        """Close WebSocket."""
        ...

    @abstractmethod
    def _build_subscribe_message(self, symbols: list[str]) -> str | bytes | dict:
        """Build broker-specific subscribe message."""
        ...

    @abstractmethod
    def _is_heartbeat_message(self, raw: str | bytes) -> bool:
        """True if message is ping/pong or broker heartbeat (no need to update last_message_ts for lag)."""
        ...

    @abstractmethod
    async def _refresh_token(self) -> bool:
        """Refresh auth token. Return True on success. Log via log_token_refresh."""
        ...

    def _get_token_expiry_ts(self) -> float:
        """Override to return token expiry timestamp (Unix). Default: no expiry."""
        return 0.0

    def is_fallback_active(self) -> bool:
        return self._fallback_active

    def get_subscribed_symbols(self) -> list[str]:
        return list(self._subscribed_symbols)

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to symbols; stored for auto resubscribe on reconnect."""
        async with self._lock:
            self._subscribed_symbols = list(symbols)
            if self._ws and self._running:
                msg = self._build_subscribe_message(self._subscribed_symbols)
                if msg is not None:
                    await self._ws_send(self._ws, msg)
                    log_resubscribe(self.adapter_name, self._subscribed_symbols, True)

    async def _on_message(self, raw: str | bytes) -> None:
        """Override to handle tick/candle. Default: only update last_message_ts."""
        if not self._is_heartbeat_message(raw):
            self._last_message_ts = time.time()

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat and measure latency."""
        while self._running and self._ws:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if not self._running or not self._ws:
                    break
                t0 = time.perf_counter()
                await self._send_heartbeat()
                latency_ms = (time.perf_counter() - t0) * 1000
                log_heartbeat(self.adapter_name, latency_ms)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_heartbeat(self.adapter_name, error=str(e))

    async def _send_heartbeat(self) -> None:
        """Override for broker-specific ping. Default: no-op."""
        pass

    async def _lag_check_loop(self) -> None:
        """Detect feed lag and set fallback if over threshold."""
        while self._running:
            try:
                await asyncio.sleep(min(10.0, self.lag_threshold / 2))
                if not self._running:
                    break
                if self._last_message_ts == 0:
                    continue
                lag = time.time() - self._last_message_ts
                if lag >= self.lag_threshold:
                    log_lag(self.adapter_name, lag, self.lag_threshold)
                    if self.fallback_enabled:
                        self._fallback_active = True
                        log_fallback(self.adapter_name, f"lag {lag:.0f}s", active=True)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _token_refresh_loop(self) -> None:
        """Refresh token before expiry."""
        while self._running:
            try:
                await asyncio.sleep(60)
                if not self._running:
                    break
                expiry = self._get_token_expiry_ts()
                if expiry <= 0:
                    continue
                if time.time() >= expiry - self.token_refresh_before:
                    t0 = time.perf_counter()
                    ok = await self._refresh_token()
                    latency_ms = (time.perf_counter() - t0) * 1000
                    log_token_refresh(self.adapter_name, ok, latency_ms, None if ok else "refresh failed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_token_refresh(self.adapter_name, False, error=str(e))

    async def _recv_loop(self, ws: Any) -> None:
        """Receive messages and dispatch."""
        try:
            while self._running:
                raw = await self._ws_recv(ws)
                if raw is None:
                    break
                await self._on_message(raw)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_disconnect(self.adapter_name, str(e))

    async def _run_once(self) -> bool:
        """Connect, run recv until disconnect. Return True if intentional stop."""
        t0 = time.perf_counter()
        try:
            ws = await self._ws_connect()
        except Exception as e:
            log_connect(self.adapter_name, error=str(e))
            return False
        latency_ms = (time.perf_counter() - t0) * 1000
        log_connect(self.adapter_name, latency_ms=latency_ms)
        self._ws = ws
        self._fallback_active = False
        log_fallback(self.adapter_name, "reconnected", active=False)
        self._reconnect_attempt = 0
        if self._subscribed_symbols:
            msg = self._build_subscribe_message(self._subscribed_symbols)
            if msg is not None:
                try:
                    await self._ws_send(ws, msg)
                    log_resubscribe(self.adapter_name, self._subscribed_symbols, True)
                except Exception as e:
                    log_resubscribe(self.adapter_name, self._subscribed_symbols, False)

        self._recv_task = asyncio.create_task(self._recv_loop(ws))
        try:
            await self._recv_task
        finally:
            self._recv_task = None
        try:
            await self._ws_close(ws)
        except Exception:
            pass
        self._ws = None
        log_disconnect(self.adapter_name, "recv closed")
        return False

    async def run(self) -> None:
        """Run feed with reconnect, heartbeat, lag check, token refresh."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._lag_task = asyncio.create_task(self._lag_check_loop())
        token_task = asyncio.create_task(self._token_refresh_loop())
        while self._running:
            ok = await self._run_once()
            if ok:
                break
            if not self._running:
                break
            self._reconnect_attempt += 1
            if self._reconnect_attempt > self.reconnect_max:
                if self.fallback_enabled:
                    self._fallback_active = True
                    log_fallback(
                        self.adapter_name,
                        f"reconnect exhausted ({self.reconnect_max} attempts)",
                        active=True,
                    )
                log_reconnect(
                    self.adapter_name,
                    self._reconnect_attempt,
                    self.reconnect_max,
                    self.reconnect_max_delay,
                    error="max retries exceeded",
                )
                break
            delay = self._reconnect_delay()
            log_reconnect(
                self.adapter_name,
                self._reconnect_attempt,
                self.reconnect_max,
                delay,
            )
            await asyncio.sleep(delay)
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self._lag_task:
            self._lag_task.cancel()
            try:
                await self._lag_task
            except asyncio.CancelledError:
                pass
        token_task.cancel()
        try:
            await token_task
        except asyncio.CancelledError:
            pass
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        self._ws = None

    async def stop(self) -> None:
        """Stop the feed."""
        self._running = False
        if self._ws:
            try:
                await self._ws_close(self._ws)
            except Exception:
                pass
            self._ws = None

"""
Market data feed manager: start/stop hardened WebSocket feeds per adapter.
Uses fallback (REST) when feed is down or lagging. Monitoring logs emitted by feeds.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.adapters.broker.feed_base import HardenedFeedBase
from app.adapters.broker.feed_angel_one import AngelOneFeed
from app.adapters.broker.feed_dhan import DhanFeed
from app.adapters.broker.feed_zerodha import ZerodhaFeed
from app.adapters.broker.monitoring import log_feed_event


_FEED_CLASSES: dict[str, type[HardenedFeedBase]] = {
    "angel_one": AngelOneFeed,
    "dhan": DhanFeed,
    "zerodha": ZerodhaFeed,
}


class FeedManager:
    """Start/stop and query feeds. Single run task per adapter."""

    def __init__(self) -> None:
        self._feeds: dict[str, HardenedFeedBase] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    def get_feed(self, adapter_name: str) -> HardenedFeedBase | None:
        """Return running feed for adapter if any."""
        return self._feeds.get(adapter_name)

    def is_fallback_active(self, adapter_name: str) -> bool:
        """True if feed is down or lagging and REST fallback should be used."""
        feed = self._feeds.get(adapter_name)
        return feed is not None and feed.is_fallback_active()

    async def start_feed(self, adapter_name: str, symbols: list[str] | None = None) -> bool:
        """Start hardened feed for adapter. Returns True if started."""
        if adapter_name not in _FEED_CLASSES:
            log_feed_event(adapter_name, "start_feed", error=f"unknown adapter {adapter_name}", level="warning")
            return False
        async with self._lock:
            if adapter_name in self._feeds:
                if symbols:
                    await self._feeds[adapter_name].subscribe(symbols)
                return True
            feed = _FEED_CLASSES[adapter_name]()
            self._feeds[adapter_name] = feed
            if symbols:
                await feed.subscribe(symbols)
            task = asyncio.create_task(feed.run())
            self._tasks[adapter_name] = task
        log_feed_event(adapter_name, "start_feed", message=f"[{adapter_name}] Feed started", symbols=symbols or [])
        return True

    async def stop_feed(self, adapter_name: str) -> None:
        """Stop feed for adapter."""
        async with self._lock:
            feed = self._feeds.pop(adapter_name, None)
            task = self._tasks.pop(adapter_name, None)
        if feed:
            await feed.stop()
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        log_feed_event(adapter_name, "stop_feed", message=f"[{adapter_name}] Feed stopped")

    async def stop_all(self) -> None:
        """Stop all feeds."""
        for name in list(self._feeds.keys()):
            await self.stop_feed(name)


# Singleton for app lifecycle
_feed_manager: FeedManager | None = None


def get_feed_manager() -> FeedManager:
    global _feed_manager
    if _feed_manager is None:
        _feed_manager = FeedManager()
    return _feed_manager

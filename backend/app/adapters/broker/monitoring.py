"""
Structured monitoring logs for the market data pipeline.
Emit events: connect, disconnect, reconnect, heartbeat, lag, token_refresh, fallback, resubscribe.
"""

import logging
import time
from typing import Any

logger = logging.getLogger("strikegenius.feed")


def log_feed_event(
    adapter: str,
    event: str,
    *,
    level: str = "info",
    message: str | None = None,
    latency_ms: float | None = None,
    lag_sec: float | None = None,
    attempt: int | None = None,
    max_retries: int | None = None,
    symbols: list[str] | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured feed event for monitoring."""
    payload: dict[str, Any] = {
        "adapter": adapter,
        "event": event,
        "ts": time.time(),
    }
    if latency_ms is not None:
        payload["latency_ms"] = round(latency_ms, 2)
    if lag_sec is not None:
        payload["lag_sec"] = round(lag_sec, 2)
    if attempt is not None:
        payload["attempt"] = attempt
    if max_retries is not None:
        payload["max_retries"] = max_retries
    if symbols is not None:
        payload["symbols"] = symbols
    if error is not None:
        payload["error"] = error
    if extra:
        payload.update(extra)
    msg = message or f"feed.{adapter}.{event}"
    log_fn = getattr(logger, level, logger.info)
    log_fn(msg, extra={"feed": payload})


def log_connect(adapter: str, latency_ms: float | None = None, error: str | None = None) -> None:
    msg = f"[{adapter}] WebSocket connected" if not error else f"[{adapter}] WebSocket connect failed: {error}"
    log_feed_event(adapter, "connect", message=msg, latency_ms=latency_ms, error=error, level="warning" if error else "info")


def log_disconnect(adapter: str, reason: str | None = None) -> None:
    log_feed_event(adapter, "disconnect", message=f"[{adapter}] WebSocket disconnected", error=reason, level="info")


def log_reconnect(adapter: str, attempt: int, max_retries: int, delay_sec: float, error: str | None = None) -> None:
    log_feed_event(
        adapter,
        "reconnect",
        message=f"[{adapter}] Reconnect attempt {attempt}/{max_retries} in {delay_sec:.1f}s",
        attempt=attempt,
        max_retries=max_retries,
        error=error,
        extra={"delay_sec": round(delay_sec, 1)},
        level="warning" if error else "info",
    )


def log_heartbeat(adapter: str, latency_ms: float | None = None, error: str | None = None) -> None:
    log_feed_event(adapter, "heartbeat", latency_ms=latency_ms, error=error, level="warning" if error else "debug")


def log_lag(adapter: str, lag_sec: float, threshold_sec: float) -> None:
    log_feed_event(
        adapter,
        "lag",
        message=f"[{adapter}] Feed lag {lag_sec:.1f}s exceeds threshold {threshold_sec}s",
        lag_sec=lag_sec,
        extra={"threshold_sec": threshold_sec},
        level="warning",
    )


def log_token_refresh(adapter: str, success: bool, latency_ms: float | None = None, error: str | None = None) -> None:
    log_feed_event(
        adapter,
        "token_refresh",
        message=f"[{adapter}] Token refresh {'ok' if success else 'failed'}",
        latency_ms=latency_ms,
        error=None if success else (error or "unknown"),
        extra={"success": success},
        level="info" if success else "warning",
    )


def log_fallback(adapter: str, reason: str, active: bool = True) -> None:
    log_feed_event(
        adapter,
        "fallback",
        message=f"[{adapter}] Fallback feed {'activated' if active else 'cleared'}: {reason}",
        error=reason if active else None,
        extra={"fallback_active": active},
        level="warning" if active else "info",
    )


def log_resubscribe(adapter: str, symbols: list[str], success: bool) -> None:
    log_feed_event(
        adapter,
        "resubscribe",
        message=f"[{adapter}] Auto resubscribe {len(symbols)} symbols",
        symbols=symbols,
        extra={"success": success},
        level="info",
    )

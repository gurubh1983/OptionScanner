# Market data pipeline (hardened)

WebSocket live feed with:

- **Reconnect**: Exponential backoff (config: `feed_reconnect_base_delay_sec`, `feed_reconnect_max_retries`, `feed_reconnect_max_delay_sec`)
- **Token refresh**: Before expiry (config: `feed_token_refresh_before_expiry_sec`); broker-specific in each feed
- **Heartbeat**: Periodic ping (config: `feed_heartbeat_interval_sec`); monitoring log at DEBUG
- **Lag detection**: If no non-heartbeat message for `feed_lag_threshold_sec`, log and set fallback
- **Fallback feed**: When reconnect exhausted or lag too high, `is_fallback_active()` is True; use REST (get_candles) as fallback
- **Auto resubscribe**: On reconnect, last `subscribe(symbols)` is re-sent

## Monitoring logs

Logger: `strikegenius.feed`. Events: `connect`, `disconnect`, `reconnect`, `heartbeat`, `lag`, `token_refresh`, `fallback`, `resubscribe`.

Each log has `extra["feed"]` with: `adapter`, `event`, `ts`, and optional `latency_ms`, `lag_sec`, `attempt`, `symbols`, `error`.

To enable in your app:

```python
import logging
logging.getLogger("strikegenius.feed").setLevel(logging.DEBUG)
```

## Starting a feed

```python
from app.adapters.broker.feed_manager import get_feed_manager

manager = get_feed_manager()
await manager.start_feed("angel_one", symbols=["NIFTY", "BANKNIFTY"])
# Feed runs in background. Use adapter.get_candles() for REST fallback when manager.is_fallback_active("angel_one").
```

## Adapters

- **Angel One**: `AngelOneFeed` — SmartAPI WebSocket URL and subscribe format
- **Dhan**: `DhanFeed` — Dhan feed URL and subscribe format
- **Zerodha**: `ZerodhaFeed` — Kite WebSocket URL and login/subscribe format

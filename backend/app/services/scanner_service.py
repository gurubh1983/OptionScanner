"""Scanner service: run scan with subscription check and persistence."""

from __future__ import annotations

import uuid

from app.scanner.engine import ScannerEngine
from app.scanner.schemas import ScanRequest, ScanResponse
from app.indicators.engine import IndicatorEngine
from app.services.market_data_service import MarketDataService
from app.services.subscription_service import SubscriptionService
from app.repositories.scan_repository import ScanRepository


class ScannerService:
    def __init__(
        self,
        market_data_service: MarketDataService,
        subscription_service: SubscriptionService,
        scan_repository: ScanRepository,
    ):
        self._market_data = market_data_service
        self._subscription = subscription_service
        self._scan_repo = scan_repository
        self._indicator_engine = IndicatorEngine()
        self._engine = ScannerEngine(indicator_engine=self._indicator_engine)

    async def run_scan(
        self,
        request: ScanRequest,
        user_id: uuid.UUID | None,
    ) -> ScanResponse:
        """Run scan. Enforces subscription limits; loads candles from market data; persists scan."""
        if user_id:
            scans_today = await self._scan_repo.count_scans_today(user_id)
            if not await self._subscription.check_scan_allowance(user_id, scans_today):
                plan_id = await self._subscription.get_effective_plan_for_user(user_id)
                raise ValueError(
                    f"Scan limit reached for your plan ({plan_id}). Upgrade for more scans."
                )
        symbols = request.symbols or ["NIFTY", "BANKNIFTY"]
        symbols = symbols[: request.max_results]
        symbol_series = {}
        for symbol in symbols:
            candles = await self._market_data.get_candles(
                symbol, request.rule.timeframe, limit=500
            )
            symbol_series[symbol] = self._indicator_engine.build_series_from_candles(candles)
        response = self._engine.run_scan(request, symbol_series=symbol_series)
        if user_id:
            await self._scan_repo.create(
                user_id=user_id,
                rule_id=None,
                rule_name=response.rule_name,
                timeframe=response.timeframe,
                result_count=response.total_matched,
                duration_ms=response.duration_ms,
                result_snapshot=[r.model_dump() for r in response.results],
            )
        return response

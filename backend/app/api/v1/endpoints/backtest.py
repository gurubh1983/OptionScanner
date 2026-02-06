"""Backtest API: run backtest and return report with metrics."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.backtest.schemas import BacktestRequest, BacktestResponse
from app.services.backtest_service import BacktestService
from app.services.market_data_service import MarketDataService
from app.api.v1.deps import get_market_data_service

router = APIRouter()


def get_backtest_service(
    market_data: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> BacktestService:
    return BacktestService(market_data_service=market_data)


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest,
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestResponse:
    """
    Run backtest on historical candles (TimescaleDB).
    Returns win rate, PnL, max drawdown, Sharpe, expectancy and trade list.
    """
    try:
        return await service.run(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

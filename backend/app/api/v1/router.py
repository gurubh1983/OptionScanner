"""Aggregate all v1 API routes."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, scans, indicators, billing, admin, backtest, templates_market

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(indicators.router, prefix="/indicators", tags=["indicators"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(templates_market.router, prefix="/templates/market", tags=["templates-market"])

"""Aggregate v1 API routes. Only working endpoints; marketplace is disabled (see endpoints/_disabled)."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, scans, indicators, billing, admin, backtest

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(indicators.router, prefix="/indicators", tags=["indicators"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])

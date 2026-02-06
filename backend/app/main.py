"""
StrikeGenius.ai - FastAPI application entry point.
Chartink + TradingView + Option Chain + AI = One Platform.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: ensure models registered, then create tables. Shutdown: cleanup."""
    # Ensure all models are attached to Base.metadata before create_all
    import app.models  # noqa: F401

    from app.db.session import async_engine, Base

    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created or verified.")
    except Exception as e:
        logger.exception("Database initialization failed: %s", e)
        # Continue boot so /health and /docs still work; API that needs DB will fail with 500
    yield
    await async_engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description="Options Strike Scanner for Indian Markets — Unlimited rules, Chartink-level power, TradingView indicators.",
    version="0.1.0",
    openapi_url=settings.openapi_url,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


def _cors_origins() -> list[str]:
    if settings.cors_origins:
        return [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    return ["*"] if settings.debug else ["https://strikegenius.ai"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    """Root for Railway/proxy health checks."""
    return {"status": "ok", "app": settings.app_name, "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check for load balancers and K8s."""
    return {"status": "ok", "app": settings.app_name}

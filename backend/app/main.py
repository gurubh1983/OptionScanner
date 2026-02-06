from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import async_engine
from app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized")
    except Exception as e:
        print("❌ Database init failed:", e)

    yield

    # Close DB
    await async_engine.dispose()
    print("✅ Database closed")


app = FastAPI(
    title=settings.app_name,
    description="Options Strike Scanner for Indian Markets",
    version="0.1.0",
    openapi_url=settings.openapi_url,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# CORS
origins = (
    [o.strip() for o in settings.cors_origins.split(",")]
    if settings.cors_origins
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(api_router, prefix="/api/v1")


# Root
@app.get("/")
def root():
    return {
        "status": "ok",
        "app": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }


# Health
@app.get("/health")
def health():
    return {"status": "healthy"}

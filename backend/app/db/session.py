"""Async SQLAlchemy engine and session. PostgreSQL + TimescaleDB ready."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

async_engine = create_async_engine(
    settings.database_url,

    echo=settings.debug,

    pool_pre_ping=True,
    pool_recycle=300,

    pool_size=5,
    max_overflow=5,

    connect_args={
        "server_settings": {
            "application_name": "strikegenius"
        }
    },
)

async def warmup_db():
    try:
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        print("✅ DB warmed up")
    except Exception as e:
        print("❌ DB warmup failed:", e)

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all models."""
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()



async def init_db() -> None:
    """Create tables. Use Alembic in production."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

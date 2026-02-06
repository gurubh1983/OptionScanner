"""FastAPI dependencies: DB session, services, auth."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db

# Repositories (core: user, plan, subscription, scan)
from app.repositories.user_repository import UserRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.scan_repository import ScanRepository

# Services
from app.services.auth_service import AuthService
from app.services.subscription_service import SubscriptionService
from app.services.market_data_service import MarketDataService
from app.services.scanner_service import ScannerService
from app.services.simulate_service import SimulateService

# Indicator engine
from app.indicators.engine import IndicatorEngine


security = HTTPBearer(auto_error=False)


# ------------------------
# Repositories
# ------------------------

def get_user_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserRepository:
    return UserRepository(session)


def get_plan_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlanRepository:
    return PlanRepository(session)


def get_subscription_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionRepository:
    return SubscriptionRepository(session)


def get_scan_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ScanRepository:
    return ScanRepository(session)


# ------------------------
# Services
# ------------------------

def get_auth_service(
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> AuthService:
    return AuthService(repo)


def get_subscription_service(
    plan_repo: Annotated[PlanRepository, Depends(get_plan_repo)],
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
) -> SubscriptionService:
    return SubscriptionService(plan_repo, sub_repo)


def get_market_data_service() -> MarketDataService:
    return MarketDataService()


def get_scanner_service(
    market_data: Annotated[MarketDataService, Depends(get_market_data_service)],
    subscription: Annotated[SubscriptionService, Depends(get_subscription_service)],
    scan_repo: Annotated[ScanRepository, Depends(get_scan_repo)],
) -> ScannerService:
    return ScannerService(market_data, subscription, scan_repo)


def get_simulate_service(
    market_data: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> SimulateService:
    return SimulateService(market_data_service=market_data)


def get_indicator_engine() -> IndicatorEngine:
    return IndicatorEngine()


# ------------------------
# Auth helpers
# ------------------------

def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """Return user id (UUID string) from JWT or None if no token."""
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return payload.get("sub")


def get_current_user_id_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """Return user id from JWT or None. Does not raise on invalid token."""
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)

    return payload.get("sub") if payload else None


async def get_current_user_optional(
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
):
    """Return User or None. Use when endpoint needs user email etc."""
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)

    if not payload:
        return None

    import uuid

    try:
        uid = uuid.UUID(payload.get("sub"))
    except Exception:
        return None

    repo = UserRepository(session)

    return await repo.get_by_id(uid)

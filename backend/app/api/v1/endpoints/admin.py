"""Admin: stats from DB (users, scans, subscriptions)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.user import User
from app.models.scan import Scan
from app.models.subscription import Subscription
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

router = APIRouter()


@router.get("/stats")
async def admin_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Admin dashboard stats from DB."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    users_total = (await session.execute(select(func.count(User.id)))).scalar() or 0
    scans_today = (await session.execute(select(func.count(Scan.id)).where(Scan.created_at >= today_start))).scalar() or 0
    active_subs = (await session.execute(select(func.count(Subscription.id)).where(Subscription.status == "active"))).scalar() or 0
    return {
        "users_total": users_total,
        "scans_today": scans_today,
        "active_subscriptions": active_subs,
        "alerts_delivered_today": 0,
    }

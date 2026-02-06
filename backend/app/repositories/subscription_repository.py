"""Subscription repository: active subscription and upsert."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_active_for_user(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .order_by(Subscription.current_period_end.desc().nulls_last())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        plan_id: str,
        status: str,
        provider: str,
        provider_subscription_id: str | None,
        period_start: datetime | None,
        period_end: datetime | None,
        metadata: dict | None,
    ) -> Subscription:
        existing = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        sub = existing.scalar_one_or_none()
        if sub:
            sub.plan_id = plan_id
            sub.status = status
            sub.provider = provider
            sub.provider_subscription_id = provider_subscription_id
            sub.current_period_start = period_start
            sub.current_period_end = period_end
            sub.metadata_ = metadata or sub.metadata_
            await self._session.flush()
            await self._session.refresh(sub)
            return sub
        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status=status,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            current_period_start=period_start,
            current_period_end=period_end,
            metadata_=metadata,
        )
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

    async def update_status(self, provider_subscription_id: str, status: str) -> None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = status
            await self._session.flush()

    async def get_by_provider_subscription_id(self, provider_subscription_id: str) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id)
        )
        return result.scalar_one_or_none()

    async def create_pending(
        self,
        user_id: uuid.UUID,
        plan_id: str,
        provider: str,
        provider_subscription_id: str,
    ) -> Subscription:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            status="pending",
            provider=provider,
            provider_subscription_id=provider_subscription_id,
        )
        self._session.add(sub)
        await self._session.flush()
        await self._session.refresh(sub)
        return sub

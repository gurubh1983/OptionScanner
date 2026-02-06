"""Scan rule (template) repository: save and list rules."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import ScanRule


class ScanRuleRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        rule_ast: dict,
        description: str | None = None,
        is_public: bool = False,
        price_inr: int = 0,
        price_usd: int = 0,
        premium_only: bool = False,
    ) -> ScanRule:
        r = ScanRule(
            user_id=user_id,
            name=name,
            rule_ast=rule_ast,
            description=description,
            is_public=is_public,
            price_inr=price_inr,
            price_usd=price_usd,
            premium_only=premium_only,
        )
        self._session.add(r)
        await self._session.flush()
        await self._session.refresh(r)
        return r

    async def list_for_user(self, user_id: uuid.UUID) -> list[ScanRule]:
        result = await self._session.execute(
            select(ScanRule).where(ScanRule.user_id == user_id).order_by(ScanRule.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_public(self) -> list[ScanRule]:
        result = await self._session.execute(
            select(ScanRule).where(ScanRule.is_public == True).order_by(ScanRule.use_count.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, rule_id: uuid.UUID, user_id: uuid.UUID | None = None) -> ScanRule | None:
        q = select(ScanRule).where(ScanRule.id == rule_id)
        if user_id is not None:
            q = q.where(ScanRule.user_id == user_id)
        result = await self._session.execute(q)
        return result.scalar_one_or_none()

    async def get_public_by_id(self, rule_id: uuid.UUID) -> ScanRule | None:
        result = await self._session.execute(
            select(ScanRule).where(ScanRule.id == rule_id, ScanRule.is_public == True)
        )
        return result.scalar_one_or_none()

    async def list_marketplace(self, limit: int = 100) -> list[ScanRule]:
        result = await self._session.execute(
            select(ScanRule)
            .where(ScanRule.is_public == True)
            .order_by(ScanRule.use_count.desc(), ScanRule.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

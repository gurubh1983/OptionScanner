"""Template purchase repository: record and list purchases."""

from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import TemplatePurchase, ScanRule


class TemplatePurchaseRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        buyer_id: uuid.UUID,
        rule_id: uuid.UUID,
        amount_inr: int,
        amount_usd: int,
        currency: str,
    ) -> TemplatePurchase:
        p = TemplatePurchase(
            buyer_id=buyer_id,
            rule_id=rule_id,
            amount_inr=amount_inr,
            amount_usd=amount_usd,
            currency=currency,
        )
        self._session.add(p)
        await self._session.flush()
        await self._session.refresh(p)
        return p

    async def list_by_buyer(self, buyer_id: uuid.UUID) -> list[TemplatePurchase]:
        result = await self._session.execute(
            select(TemplatePurchase)
            .where(TemplatePurchase.buyer_id == buyer_id)
            .order_by(TemplatePurchase.created_at.desc())
        )
        return list(result.scalars().all())

    async def has_purchased(self, buyer_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            select(TemplatePurchase).where(
                TemplatePurchase.buyer_id == buyer_id,
                TemplatePurchase.rule_id == rule_id,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def count_by_rule(self, rule_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count(TemplatePurchase.id)).where(TemplatePurchase.rule_id == rule_id)
        )
        return result.scalar() or 0

    async def creator_earnings(self, creator_user_id: uuid.UUID) -> list[dict]:
        """Aggregate earnings per rule for the creator. Join purchases with scan_rules."""
        subq = (
            select(
                ScanRule.id.label("rule_id"),
                ScanRule.name.label("rule_name"),
                func.sum(TemplatePurchase.amount_inr).label("total_inr"),
                func.sum(TemplatePurchase.amount_usd).label("total_usd"),
                func.count(TemplatePurchase.id).label("sales_count"),
            )
            .join(TemplatePurchase, TemplatePurchase.rule_id == ScanRule.id)
            .where(ScanRule.user_id == creator_user_id)
            .group_by(ScanRule.id, ScanRule.name)
        )
        result = await self._session.execute(subq)
        rows = result.all()
        return [
            {
                "rule_id": str(r.rule_id),
                "rule_name": r.rule_name,
                "total_inr": r.total_inr or 0,
                "total_usd": r.total_usd or 0,
                "sales_count": r.sales_count or 0,
            }
            for r in rows
        ]

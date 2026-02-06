"""Plan repository: read-only plan lookup."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, plan_id: str) -> Plan | None:
        result = await self._session.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Plan]:
        result = await self._session.execute(select(Plan).order_by(Plan.price_inr))
        return list(result.scalars().all())

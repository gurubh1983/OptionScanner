"""Template rating repository: upsert and aggregate ratings."""

from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import TemplateRating


class TemplateRatingRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, user_id: uuid.UUID, rule_id: uuid.UUID, rating: int, comment: str | None = None) -> TemplateRating:
        result = await self._session.execute(
            select(TemplateRating).where(
                TemplateRating.user_id == user_id,
                TemplateRating.rule_id == rule_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.rating = rating
            existing.comment = comment
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        r = TemplateRating(user_id=user_id, rule_id=rule_id, rating=rating, comment=comment)
        self._session.add(r)
        await self._session.flush()
        await self._session.refresh(r)
        return r

    async def get_aggregate(self, rule_id: uuid.UUID) -> dict | None:
        result = await self._session.execute(
            select(
                func.avg(TemplateRating.rating).label("avg_rating"),
                func.count(TemplateRating.id).label("count"),
            ).where(TemplateRating.rule_id == rule_id)
        )
        row = result.one()
        if row.count == 0:
            return None
        return {"avg_rating": round(float(row.avg_rating), 2), "count": row.count}

    async def get_for_rule(self, rule_id: uuid.UUID, limit: int = 50) -> list[TemplateRating]:
        result = await self._session.execute(
            select(TemplateRating)
            .where(TemplateRating.rule_id == rule_id)
            .order_by(TemplateRating.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

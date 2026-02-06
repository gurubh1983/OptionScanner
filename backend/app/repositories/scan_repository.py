"""Scan repository: count scans today, create scan record."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan


class ScanRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def count_scans_today(self, user_id: uuid.UUID) -> int:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self._session.execute(
            select(func.count(Scan.id)).where(
                Scan.user_id == user_id,
                Scan.created_at >= today_start,
            )
        )
        return result.scalar() or 0

    async def create(
        self,
        user_id: uuid.UUID | None,
        rule_id: uuid.UUID | None,
        rule_name: str,
        timeframe: str,
        result_count: int,
        duration_ms: int,
        result_snapshot: dict | None,
    ) -> Scan:
        scan = Scan(
            user_id=user_id,
            rule_id=rule_id,
            rule_name=rule_name,
            timeframe=timeframe,
            result_count=result_count,
            duration_ms=duration_ms,
            result_snapshot=result_snapshot,
        )
        self._session.add(scan)
        await self._session.flush()
        await self._session.refresh(scan)
        return scan

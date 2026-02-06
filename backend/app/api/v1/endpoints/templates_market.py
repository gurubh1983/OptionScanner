"""Template marketplace: list, detail, purchase, rate, purchase history, creator earnings."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.deps import (
    get_marketplace_service,
    get_current_user_id,
    get_current_user_id_optional,
)
from app.services.marketplace_service import MarketplaceService
from typing import Annotated

router = APIRouter()


class RateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


@router.get("")
async def list_marketplace(
    limit: int = 100,
    marketplace: MarketplaceService = Depends(get_marketplace_service),
) -> list[dict]:
    """List templates in the marketplace (public, with price and rating)."""
    return await marketplace.list_marketplace(limit=limit)


@router.get("/my/purchases")
async def my_purchases(
    marketplace: MarketplaceService = Depends(get_marketplace_service),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    """Current user's purchase history with rule_ast for each."""
    uid = uuid.UUID(user_id)
    return await marketplace.my_purchases(uid)


@router.get("/creator/earnings")
async def creator_earnings(
    marketplace: MarketplaceService = Depends(get_marketplace_service),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Earnings per template and total for the current user (creator)."""
    uid = uuid.UUID(user_id)
    return await marketplace.creator_earnings(uid)


@router.get("/{rule_id}")
async def get_template_detail(
    rule_id: uuid.UUID,
    marketplace: MarketplaceService = Depends(get_marketplace_service),
    user_id: str | None = Depends(get_current_user_id_optional),
) -> dict:
    """Template detail. rule_ast only if purchased, creator, or free. Premium-only requires Pro/Elite."""
    uid = uuid.UUID(user_id) if user_id else None
    detail = await marketplace.get_detail(rule_id, uid)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return detail


@router.post("/{rule_id}/purchase")
async def purchase_template(
    rule_id: uuid.UUID,
    marketplace: MarketplaceService = Depends(get_marketplace_service),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Purchase template. Free templates are recorded; paid templates require premium for premium_only."""
    uid = uuid.UUID(user_id)
    result, err = await marketplace.purchase(uid, rule_id)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return result


@router.post("/{rule_id}/rate")
async def rate_template(
    rule_id: uuid.UUID,
    body: RateRequest,
    marketplace: MarketplaceService = Depends(get_marketplace_service),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Rate a template (1-5). Requires prior purchase."""
    uid = uuid.UUID(user_id)
    result, err = await marketplace.rate(uid, rule_id, body.rating, body.comment)
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)
    return result

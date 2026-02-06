"""Template marketplace: list, purchase, rate, creator earnings. Integrates with subscriptions (premium lock)."""

from __future__ import annotations

import uuid

from app.repositories.scan_rule_repository import ScanRuleRepository
from app.repositories.template_purchase_repository import TemplatePurchaseRepository
from app.repositories.template_rating_repository import TemplateRatingRepository
from app.repositories.user_repository import UserRepository
from app.services.subscription_service import SubscriptionService


class MarketplaceService:
    def __init__(
        self,
        scan_rule_repo: ScanRuleRepository,
        purchase_repo: TemplatePurchaseRepository,
        rating_repo: TemplateRatingRepository,
        user_repo: UserRepository,
        subscription_service: SubscriptionService,
    ):
        self._rule_repo = scan_rule_repo
        self._purchase_repo = purchase_repo
        self._rating_repo = rating_repo
        self._user_repo = user_repo
        self._subscription = subscription_service

    async def _can_access_premium(self, user_id: uuid.UUID | None) -> bool:
        if not user_id:
            return False
        plan = await self._subscription.get_effective_plan_for_user(user_id)
        return plan in ("pro", "elite")

    def _rule_to_list_item(self, rule, avg_rating: dict | None, purchase_count: int, creator_name: str | None) -> dict:
        return {
            "id": str(rule.id),
            "name": rule.name,
            "description": rule.description or "",
            "price_inr": getattr(rule, "price_inr", 0),
            "price_usd": getattr(rule, "price_usd", 0),
            "premium_only": getattr(rule, "premium_only", False),
            "creator_id": str(rule.user_id),
            "creator_name": creator_name,
            "use_count": rule.use_count,
            "avg_rating": avg_rating["avg_rating"] if avg_rating else None,
            "rating_count": avg_rating["count"] if avg_rating else 0,
            "purchase_count": purchase_count,
        }

    async def list_marketplace(self, limit: int = 100) -> list[dict]:
        rules = await self._rule_repo.list_marketplace(limit=limit)
        out = []
        for rule in rules:
            avg = await self._rating_repo.get_aggregate(rule.id)
            purchase_count = await self._purchase_repo.count_by_rule(rule.id)
            creator = await self._user_repo.get_by_id(rule.user_id)
            creator_name = (creator.full_name or creator.email) if creator else None
            out.append(self._rule_to_list_item(rule, avg, purchase_count, creator_name))
        return out

    async def get_detail(self, rule_id: uuid.UUID, user_id: uuid.UUID | None) -> dict | None:
        rule = await self._rule_repo.get_public_by_id(rule_id)
        if not rule:
            return None
        avg = await self._rating_repo.get_aggregate(rule.id)
        purchase_count = await self._purchase_repo.count_by_rule(rule.id)
        creator = await self._user_repo.get_by_id(rule.user_id)
        creator_name = (creator.full_name or creator.email) if creator else None
        has_purchased = False
        if user_id:
            has_purchased = await self._purchase_repo.has_purchased(user_id, rule.id)
        is_creator = user_id == rule.user_id
        premium_only = getattr(rule, "premium_only", False)
        can_access = is_creator or has_purchased or (rule.price_inr == 0 and rule.price_usd == 0)
        if premium_only and user_id:
            can_access = can_access or await self._can_access_premium(user_id)
        if premium_only and not user_id:
            can_access = False
        show_rule_ast = can_access or not premium_only
        return {
            "id": str(rule.id),
            "name": rule.name,
            "description": rule.description or "",
            "price_inr": getattr(rule, "price_inr", 0),
            "price_usd": getattr(rule, "price_usd", 0),
            "premium_only": premium_only,
            "creator_id": str(rule.user_id),
            "creator_name": creator_name,
            "use_count": rule.use_count,
            "avg_rating": avg["avg_rating"] if avg else None,
            "rating_count": avg["count"] if avg else 0,
            "purchase_count": purchase_count,
            "has_purchased": has_purchased,
            "is_creator": is_creator,
            "rule_ast": rule.rule_ast if show_rule_ast else None,
        }

    async def purchase(self, buyer_id: uuid.UUID, rule_id: uuid.UUID) -> tuple[dict | None, str | None]:
        """Purchase template. Returns (result_dict, error_message)."""
        rule = await self._rule_repo.get_public_by_id(rule_id)
        if not rule:
            return None, "Template not found"
        if rule.user_id == buyer_id:
            return None, "Cannot purchase your own template"
        premium_only = getattr(rule, "premium_only", False)
        if premium_only and not await self._can_access_premium(buyer_id):
            return None, "Premium subscription required to purchase this template"
        already = await self._purchase_repo.has_purchased(buyer_id, rule_id)
        if already:
            return None, "Already purchased"
        price_inr = getattr(rule, "price_inr", 0)
        price_usd = getattr(rule, "price_usd", 0)
        currency = "INR" if price_inr else "USD"
        p = await self._purchase_repo.create(
            buyer_id=buyer_id,
            rule_id=rule_id,
            amount_inr=price_inr,
            amount_usd=price_usd,
            currency=currency,
        )
        return {
            "purchase_id": str(p.id),
            "rule_id": str(rule_id),
            "rule_name": rule.name,
            "amount_inr": price_inr,
            "amount_usd": price_usd,
            "currency": currency,
        }, None

    async def rate(self, user_id: uuid.UUID, rule_id: uuid.UUID, rating: int, comment: str | None = None) -> tuple[dict | None, str | None]:
        if rating < 1 or rating > 5:
            return None, "Rating must be 1-5"
        rule = await self._rule_repo.get_public_by_id(rule_id)
        if not rule:
            return None, "Template not found"
        has = await self._purchase_repo.has_purchased(user_id, rule_id)
        if not has:
            return None, "Purchase required to rate"
        r = await self._rating_repo.upsert(user_id, rule_id, rating, comment)
        agg = await self._rating_repo.get_aggregate(rule_id)
        return {"rating": r.rating, "comment": r.comment, "avg_rating": agg["avg_rating"], "rating_count": agg["count"]}, None

    async def my_purchases(self, user_id: uuid.UUID) -> list[dict]:
        purchases = await self._purchase_repo.list_by_buyer(user_id)
        out = []
        for p in purchases:
            rule = await self._rule_repo.get_by_id(p.rule_id, user_id=None)
            if rule:
                out.append({
                    "purchase_id": str(p.id),
                    "rule_id": str(p.rule_id),
                    "rule_name": rule.name,
                    "rule_ast": rule.rule_ast,
                    "amount_inr": p.amount_inr,
                    "amount_usd": p.amount_usd,
                    "currency": p.currency,
                    "purchased_at": p.created_at.isoformat() if p.created_at else None,
                })
        return out

    async def creator_earnings(self, creator_id: uuid.UUID) -> dict:
        rows = await self._purchase_repo.creator_earnings(creator_id)
        total_inr = sum(r["total_inr"] for r in rows)
        total_usd = sum(r["total_usd"] for r in rows)
        return {
            "templates": rows,
            "total_earnings_inr": total_inr,
            "total_earnings_usd": total_usd,
        }

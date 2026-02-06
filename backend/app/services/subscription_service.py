"""Subscription service: plan limits, create subscription, webhook handling."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.adapters.payment import RazorpayPaymentAdapter, StripePaymentAdapter
from app.core.config import settings


class SubscriptionService:
    def __init__(
        self,
        plan_repo: PlanRepository,
        subscription_repo: SubscriptionRepository,
    ):
        self._plan_repo = plan_repo
        self._sub_repo = subscription_repo
        self._razorpay = RazorpayPaymentAdapter()
        self._stripe = StripePaymentAdapter()

    async def get_plan_limits(self, plan_id: str) -> tuple[int, int]:
        """Return (scans_per_day, alerts_per_day). -1 = unlimited."""
        plan = await self._plan_repo.get_by_id(plan_id)
        if not plan:
            return settings.free_scans_per_day, settings.free_alerts_per_day
        return plan.scans_per_day, plan.alerts_per_day

    async def get_effective_plan_for_user(self, user_id: uuid.UUID) -> str:
        """Return plan_id for user (active subscription or 'free')."""
        sub = await self._sub_repo.get_active_for_user(user_id)
        if sub and sub.status == "active":
            return sub.plan_id
        return "free"

    async def check_scan_allowance(self, user_id: uuid.UUID, scans_today: int) -> bool:
        """True if user can run another scan today."""
        plan_id = await self.get_effective_plan_for_user(user_id)
        limit, _ = await self.get_plan_limits(plan_id)
        if limit < 0:
            return True
        return scans_today < limit

    async def list_plans(self) -> list[dict]:
        """Return all plans for API."""
        plans = await self._plan_repo.list_all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "price_inr": p.price_inr,
                "price_usd": float(p.price_usd),
                "scans_per_day": p.scans_per_day,
                "alerts_per_day": p.alerts_per_day,
                "features": p.features or [],
            }
            for p in plans
        ]

    async def create_subscription(
        self,
        user_id: uuid.UUID,
        plan_id: str,
        email: str,
        success_url: str | None = None,
        cancel_url: str | None = None,
        provider: str = "razorpay",
    ) -> dict:
        """Create subscription via Razorpay or Stripe. Returns {url, subscription_id, error}."""
        plan = await self._plan_repo.get_by_id(plan_id)
        if not plan or plan_id == "free":
            return {"error": "Invalid plan"}
        price_inr = plan.price_inr
        price_usd = plan.price_usd
        gateway = self._razorpay if provider == "razorpay" else self._stripe
        amount = price_inr if provider == "razorpay" else (price_usd * 100)
        currency = "INR" if provider == "razorpay" else "USD"
        result = gateway.create_subscription(
            user_id=str(user_id),
            plan_id=plan_id,
            price_amount=int(amount),
            currency=currency,
            metadata={
                "email": email,
                "success_url": success_url or "https://strikegenius.ai/success",
                "cancel_url": cancel_url or "https://strikegenius.ai/pricing",
            },
        )
        if result.get("error"):
            return result
        sub_id = result.get("subscription_id") or result.get("payment_id")
        if sub_id:
            await self._sub_repo.create_pending(user_id, plan_id, provider, str(sub_id))
        return {
            "url": result.get("url") or result.get("client_secret"),
            "subscription_id": sub_id,
            "payment_id": result.get("payment_id"),
        }

    async def handle_razorpay_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify and process Razorpay webhook. Returns True if handled."""
        if not self._razorpay.verify_webhook(payload, signature):
            return False
        event = self._razorpay.parse_webhook_event(payload)
        sub_id = event.get("subscription_id")
        status = event.get("status")
        if not sub_id:
            return True
        sub = await self._sub_repo.get_by_provider_subscription_id(sub_id)
        if sub:
            await self._sub_repo.update_status(sub_id, status or "unknown")
        return True

    async def handle_stripe_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify and process Stripe webhook. Returns True if handled."""
        if not self._stripe.verify_webhook(payload, signature):
            return False
        event = self._stripe.parse_webhook_event(payload)
        sub_id = event.get("subscription_id")
        status = event.get("status")
        if sub_id and status:
            sub = await self._sub_repo.get_by_provider_subscription_id(sub_id)
            if sub:
                await self._sub_repo.update_status(sub_id, status)
        return True

"""
Stripe payment gateway adapter.
Webhook signature verification; subscription create.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings


class StripePaymentAdapter:
    def get_name(self) -> str:
        return "stripe"

    def _secret(self) -> str:
        return getattr(settings, "stripe_webhook_secret", None) or settings.stripe_secret_key or ""

    def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        price_amount: int,
        currency: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if not settings.stripe_secret_key:
            return {
                "subscription_id": None,
                "client_secret": None,
                "payment_id": None,
                "error": "Stripe not configured",
            }
        try:
            import stripe
            stripe.api_key = settings.stripe_secret_key
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer_email=metadata.get("email"),
                line_items=[{
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": price_amount,
                        "recurring": {"interval": "month"},
                        "product_data": {"name": f"Plan {plan_id}"},
                    },
                    "quantity": 1,
                }],
                metadata={**metadata, "user_id": user_id, "plan_id": plan_id},
                success_url=metadata.get("success_url", "https://strikegenius.ai/success"),
                cancel_url=metadata.get("cancel_url", "https://strikegenius.ai/pricing"),
            )
            return {
                "subscription_id": session.get("subscription_id"),
                "client_secret": session.get("client_secret"),
                "payment_id": session.id,
                "url": session.url,
            }
        except Exception as e:
            return {
                "subscription_id": None,
                "client_secret": None,
                "payment_id": None,
                "error": str(e),
            }

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        secret = settings.stripe_webhook_secret
        if not secret or not signature:
            return False
        try:
            import stripe
            stripe.Webhook.construct_event(payload, signature, secret)
            return True
        except Exception:
            return False

    def parse_webhook_event(self, payload: bytes) -> dict[str, Any]:
        try:
            import stripe
            import json
            data = json.loads(payload.decode("utf-8"))
            obj = data.get("data", {}).get("object", {})
            return {
                "event_type": data.get("type", ""),
                "subscription_id": obj.get("id") or obj.get("subscription"),
                "status": obj.get("status"),
                "payload": obj,
            }
        except Exception:
            return {"event_type": "", "subscription_id": None, "status": None, "payload": {}}

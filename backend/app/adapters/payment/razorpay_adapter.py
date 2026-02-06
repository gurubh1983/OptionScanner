"""
Razorpay payment gateway adapter.
Webhook signature verification; subscription create.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from app.core.config import settings


class RazorpayPaymentAdapter:
    def get_name(self) -> str:
        return "razorpay"

    def _secret(self) -> str:
        return settings.razorpay_key_secret or ""

    def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        price_amount: int,
        currency: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._secret():
            return {
                "subscription_id": None,
                "client_secret": None,
                "payment_id": None,
                "error": "Razorpay not configured",
            }
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
            data = {
                "plan_id": plan_id,
                "total_count": 12,
                "quantity": 1,
                "customer_id": user_id,
                "notes": metadata,
            }
            sub = client.subscription.create(data)
            return {
                "subscription_id": sub.get("id"),
                "client_secret": sub.get("short_url"),
                "payment_id": sub.get("id"),
                "status": sub.get("status"),
            }
        except Exception as e:
            return {
                "subscription_id": None,
                "client_secret": None,
                "payment_id": None,
                "error": str(e),
            }

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        secret = getattr(settings, "razorpay_webhook_secret", None) or self._secret()
        if not secret or not signature:
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(self, payload: bytes) -> dict[str, Any]:
        import json
        try:
            data = json.loads(payload.decode("utf-8"))
            event = data.get("event", "")
            payload_data = data.get("payload", {}).get("subscription", {}).get("entity", data.get("payload", {}))
            return {
                "event_type": event,
                "subscription_id": payload_data.get("id") or payload_data.get("subscription_id"),
                "status": payload_data.get("status"),
                "payload": payload_data,
            }
        except Exception:
            return {"event_type": "", "subscription_id": None, "status": None, "payload": {}}

"""Billing: plans from DB, create subscription (Razorpay/Stripe), webhooks with verification."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel

from app.services.subscription_service import SubscriptionService
from app.api.v1.deps import get_subscription_service, get_current_user_id, get_current_user_optional

router = APIRouter()


class PlanOut(BaseModel):
    id: str
    name: str
    price_inr: int
    price_usd: float
    scans_per_day: int
    alerts_per_day: int
    features: list[str]


class CreateSubscriptionRequest(BaseModel):
    plan_id: str
    provider: str = "razorpay"  # razorpay | stripe
    success_url: str | None = None
    cancel_url: str | None = None


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(
    subscription: SubscriptionService = Depends(get_subscription_service),
) -> list[PlanOut]:
    """Subscription tiers from DB (Free, Pro, Elite)."""
    plans = await subscription.list_plans()
    return [PlanOut(**p) for p in plans]


@router.post("/subscribe")
async def create_subscription(
    body: CreateSubscriptionRequest,
    subscription: SubscriptionService = Depends(get_subscription_service),
    user_id: str = Depends(get_current_user_id),
    current_user=Depends(get_current_user_optional),
):
    """Create subscription (Razorpay or Stripe). Returns payment URL or client_secret."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    import uuid
    email = current_user.email if current_user else ""
    result = await subscription.create_subscription(
        user_id=uuid.UUID(user_id),
        plan_id=body.plan_id,
        email=email,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        provider=body.provider,
    )
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request,
    subscription: SubscriptionService = Depends(get_subscription_service),
) -> dict[str, str]:
    """Razorpay webhook: signature verification then update subscription status."""
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if await subscription.handle_razorpay_webhook(body, signature):
        return {"received": "ok"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    subscription: SubscriptionService = Depends(get_subscription_service),
) -> dict[str, str]:
    """Stripe webhook: signature verification then update subscription status."""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    if await subscription.handle_stripe_webhook(body, signature):
        return {"received": "ok"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

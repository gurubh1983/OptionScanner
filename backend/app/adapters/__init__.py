"""Adapters: market data, broker feeds, payment gateways. Pluggable via config."""

from app.adapters.market_data.timescale import TimescaleDBMarketDataAdapter
from app.adapters.broker.base import BrokerAdapterRegistry
from app.adapters.broker.angel_one import AngelOneBrokerAdapter
from app.adapters.broker.dhan import DhanBrokerAdapter
from app.adapters.broker.zerodha import ZerodhaBrokerAdapter
from app.adapters.payment.razorpay_adapter import RazorpayPaymentAdapter
from app.adapters.payment.stripe_adapter import StripePaymentAdapter

__all__ = [
    "TimescaleDBMarketDataAdapter",
    "BrokerAdapterRegistry",
    "AngelOneBrokerAdapter",
    "DhanBrokerAdapter",
    "ZerodhaBrokerAdapter",
    "RazorpayPaymentAdapter",
    "StripePaymentAdapter",
]

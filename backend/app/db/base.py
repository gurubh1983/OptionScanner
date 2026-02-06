"""
Single DeclarativeBase for the app. Re-export from session.
Import only models that exist and are required for create_all (Scan has FK to scan_rules).
"""
from app.db.session import Base

# Register all existing ORM models with Base.metadata so create_all creates every table.
from app.models import (  # noqa: F401
    User,
    Plan,
    Subscription,
    Scan,
    ScanRule,
    TemplatePurchase,
    TemplateRating,
)

__all__ = ["Base"]

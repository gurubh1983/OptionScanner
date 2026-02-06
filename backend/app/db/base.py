from sqlalchemy.orm import DeclarativeBase


# Central Base class for all models
class Base(DeclarativeBase):
    pass


# Import all models so metadata is registered
from app.models.user import User
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.scan import Scan
from app.models.scan_rule import ScanRule
from app.models.template_purchase import TemplatePurchase
from app.models.template_rating import TemplateRating

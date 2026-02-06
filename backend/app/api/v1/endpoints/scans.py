"""Scan execution, validate, simulate. Templates list/save stubbed (feature disabled)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.scanner.schemas import ScanRequest, ScanResponse, ScanRuleAST
from app.services.scanner_service import ScannerService
from app.services.simulate_service import SimulateService
from app.api.v1.deps import get_scanner_service, get_simulate_service, get_current_user_id

router = APIRouter()


class SaveTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    rule_ast: dict
    is_public: bool = False
    price_inr: int = Field(0, ge=0)
    price_usd: int = Field(0, ge=0)
    premium_only: bool = False


class SimulateRequest(BaseModel):
    rule: ScanRuleAST
    symbols: list[str] = Field(default_factory=lambda: ["NIFTY", "BANKNIFTY"], min_length=1, max_length=20)
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    timeframe: str = Field("5m", description="5m, 15m, 1h, 1d")


@router.post("/run", response_model=ScanResponse)
async def run_scan(
    request: ScanRequest,
    scanner: ScannerService = Depends(get_scanner_service),
    user_id: str | None = Depends(get_current_user_id),
):
    """Run a scan. Uses market data. Enforces subscription limits when logged in."""
    import uuid
    try:
        uid = uuid.UUID(user_id) if user_id else None
    except (TypeError, ValueError):
        uid = None
    try:
        return await scanner.run_scan(request, uid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/validate")
def validate_rule(rule: ScanRuleAST) -> dict[str, str]:
    """Validate rule AST without running."""
    return {"status": "valid", "message": "Rule structure is valid"}


@router.post("/simulate")
async def simulate_rule(
    request: SimulateRequest,
    simulate: SimulateService = Depends(get_simulate_service),
) -> dict:
    """Run rule on historical candles; return signal timestamps and stats."""
    return await simulate.run(
        rule=request.rule,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        timeframe=request.timeframe,
    )


# --- Templates: disabled (return stub). Re-enable when ScanRuleRepository is wired. ---

@router.get("/templates")
async def list_templates() -> list[dict]:
    """Templates disabled. Returns empty list until template/marketplace feature is enabled."""
    return []


@router.post("/templates")
async def save_template(body: SaveTemplateRequest) -> dict:
    """Templates disabled. Returns 503 until template/marketplace feature is enabled."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Save template is temporarily disabled. Enable templates feature to use.",
    )

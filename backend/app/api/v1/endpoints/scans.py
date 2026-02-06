"""Scan execution, validate, and save/list templates."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.scanner.schemas import ScanRequest, ScanResponse, ScanRuleAST
from app.services.scanner_service import ScannerService
from app.services.simulate_service import SimulateService
from app.api.v1.deps import get_scanner_service, get_simulate_service, get_current_user_id, get_db
from app.repositories.scan_rule_repository import ScanRuleRepository
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from pydantic import BaseModel, Field

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
    """Run rule on historical candles; return signal timestamps and stats."""

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
    """
    Run a scan. Uses market data (TimescaleDB/broker). Enforces subscription limits.
    Optional auth: when logged in, scan is counted and limits apply.
    """
    try:
        import uuid
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
    """
    Run rule on historical candles bar-by-bar.
    Returns total_signals, signals_by_symbol, signals (list of {symbol, ts}), first_ts, last_ts, bars_evaluated, duration_ms.
    """
    return await simulate.run(
        rule=request.rule,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        timeframe=request.timeframe,
    )


@router.get("/templates")
async def list_templates(
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: str | None = Depends(get_current_user_id),
) -> list[dict]:
    """List saved templates: user's rules (if logged in) plus public ones."""
    repo = ScanRuleRepository(session)
    out: list[dict] = []
    if user_id:
        import uuid
        try:
            uid = uuid.UUID(user_id)
            for r in await repo.list_for_user(uid):
                out.append({
                    "id": str(r.id),
                    "name": r.name,
                    "description": r.description,
                    "rule_ast": r.rule_ast,
                    "is_public": r.is_public,
                    "use_count": r.use_count,
                })
        except ValueError:
            pass
    for r in await repo.list_public():
        if not any(t.get("id") == str(r.id) for t in out):
            out.append({
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "rule_ast": r.rule_ast,
                "is_public": True,
                "use_count": r.use_count,
            })
    return out


@router.post("/templates")
async def save_template(
    body: SaveTemplateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Save rule as template. Requires auth."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    import uuid
    uid = uuid.UUID(user_id)
    repo = ScanRuleRepository(session)
    r = await repo.create(
        uid,
        body.name,
        body.rule_ast,
        body.description,
        body.is_public,
        price_inr=body.price_inr,
        price_usd=body.price_usd,
        premium_only=body.premium_only,
    )
    return {"id": str(r.id), "name": r.name}

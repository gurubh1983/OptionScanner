"""
Pydantic schemas for Scanner: Universal Rule Format (JSON AST).
Supports nested logic, unlimited depth, all operators and meta-indicators.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Operators (Chartink++) ---
ComparisonOp = Literal[">", "<", ">=", "<=", "==", "!="]
CrossOp = Literal["cross_above", "cross_below", "touches", "rejects"]
TrendOp = Literal["rising", "falling", "flat"]
PatternOp = Literal["breakout", "breakdown", "inside_range", "gap_up", "gap_down"]
StatisticalOp = Literal["percentile", "zscore", "stddev", "correlation", "beta"]

Operator = ComparisonOp | CrossOp | TrendOp | PatternOp | StatisticalOp


class LeafRule(BaseModel):
    """Single condition: field op value or field op compare."""

    field: str = Field(..., description="Indicator expression e.g. rsi(14), ema(close,20)")
    operator: str = Field(..., description=">, <, cross_above, rising, etc.")
    value: float | int | None = Field(None, description="Right-hand value for comparison")
    compare: str | None = Field(None, description="Compare to another field e.g. ema(close,50)")
    n: int | None = Field(None, description="Period for trend/pattern ops e.g. rising(5) -> n=5")


class CompositeRule(BaseModel):
    """Nested logic: AND/OR with list of rules (recursive)."""

    logic: Literal["AND", "OR"] = "AND"
    rules: list[LeafRule | CompositeRule] = Field(default_factory=list)


class ScanRuleAST(BaseModel):
    """Top-level scan definition: name, timeframe, and root rule."""

    name: str = Field(..., min_length=1, max_length=255)
    timeframe: str = Field("5m", description="5m, 15m, 1h, 1d")
    logic: Literal["AND", "OR"] = "AND"
    rules: list[LeafRule | CompositeRule] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class StrikeFilter(BaseModel):
    """Strike-level filter: ATM, ITM(n), OTM(n), Range, Delta, Gamma."""

    type: Literal["ATM", "ITM", "OTM", "range", "delta", "gamma"] = "ATM"
    n: int | None = None  # ITM(n), OTM(n)
    range_low: int | None = None  # ATM-5
    range_high: int | None = None  # ATM+5
    delta_min: float | None = None
    delta_max: float | None = None
    gamma_min: float | None = None


class ScanRequest(BaseModel):
    """Request to run a scan."""

    rule: ScanRuleAST
    strike_filter: StrikeFilter | None = None
    symbols: list[str] | None = None  # None = all optionable symbols
    max_results: int = Field(50, ge=1, le=500)


class ScanResult(BaseModel):
    """Single strike/symbol result from scan."""

    symbol: str
    strike: float
    expiry: str
    option_type: Literal["CE", "PE"]
    score: float = Field(..., ge=0, le=100, description="Edge Score 0-100")
    matched_rules: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanResponse(BaseModel):
    """Full scan response."""

    scan_id: str
    rule_name: str
    timeframe: str
    results: list[ScanResult]
    total_matched: int
    duration_ms: int

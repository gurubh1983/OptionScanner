"""Unit tests for Scanner Engine: AST, operators, pattern/statistical."""

import pytest
import numpy as np
from app.scanner.engine import ScannerEngine, _scalar, _to_arr
from app.scanner.schemas import ScanRequest, ScanRuleAST, LeafRule, CompositeRule


def test_scalar():
    assert _scalar(10) == 10.0
    assert _scalar([1, 2, 3]) == 3.0
    assert _scalar(np.array([1, 2, 3])) == 3.0
    assert _scalar(None) is None


def test_scan_rule_ast_validation():
    rule = ScanRuleAST(
        name="Test",
        timeframe="5m",
        logic="AND",
        rules=[
            LeafRule(field="rsi(14)", operator=">", value=60),
            LeafRule(field="ema(close,20)", operator=">", compare="ema(close,50)"),
        ],
    )
    assert rule.name == "Test"
    assert len(rule.rules) == 2


def test_nested_composite_rule():
    rule = ScanRuleAST(
        name="Nested",
        timeframe="15m",
        logic="AND",
        rules=[
            CompositeRule(
                logic="OR",
                rules=[
                    LeafRule(field="rsi(14)", operator=">", value=60),
                    LeafRule(field="rsi(volume,14)", operator=">", value=70),
                ],
            ),
            LeafRule(field="ema(close,20)", operator=">", compare="ema(close,50)"),
        ],
    )
    assert rule.logic == "AND"
    assert isinstance(rule.rules[0], CompositeRule)
    assert rule.rules[0].logic == "OR"


def test_scanner_engine_run_scan():
    engine = ScannerEngine()
    request = ScanRequest(
        rule=ScanRuleAST(
            name="Quick",
            timeframe="5m",
            logic="AND",
            rules=[LeafRule(field="rsi(14)", operator=">", value=0)],
        ),
        max_results=5,
    )
    response = engine.run_scan(request)
    assert response.rule_name == "Quick"
    assert response.timeframe == "5m"
    assert response.duration_ms >= 0
    assert isinstance(response.results, list)


def test_scanner_compare_operators():
    engine = ScannerEngine()
    assert engine._compare(10, ">", 5) is True
    assert engine._compare(10, "<", 5) is False
    assert engine._compare(10, ">=", 10) is True
    assert engine._compare(10, "==", 10) is True


def test_scanner_pattern_breakout():
    engine = ScannerEngine()
    n = 30
    high = np.random.rand(n) * 10 + 100
    low = high - np.random.rand(n) * 2
    close = (high + low) / 2
    close[-1] = float(np.max(high[:-1])) + 1
    series = {"high": high, "low": low, "open": close, "close": close, "volume": np.ones(n)}
    assert engine._pattern(series, "breakout", 20) is True


def test_scanner_statistical_percentile():
    engine = ScannerEngine()
    series = {"close": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}
    # percentile: current (5) is 100th percentile; threshold 90 -> True
    ok = engine._statistical(series, "close", "percentile", 90)
    assert ok is True

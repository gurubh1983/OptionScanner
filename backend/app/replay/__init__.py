"""
Replay engine — replay any market day.
Uses stored tick/option chain data. Same bar-by-bar logic as backtest:
see app.backtest.engine.BacktestEngine (run rule on historical candles from TimescaleDB).
"""

'use client';

import { useState } from 'react';
import Link from 'next/link';

interface BacktestMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  expectancy: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
}

interface TradeRecord {
  symbol: string;
  entry_ts: string;
  exit_ts: string;
  entry_price: number;
  exit_price: number;
  side: string;
  pnl: number;
  pnl_pct: number;
  bars_held: number;
}

interface BacktestResult {
  backtest_id: string;
  rule_name: string;
  start_date: string;
  end_date: string;
  timeframe: string;
  symbols: string[];
  initial_capital: number;
  final_equity: number;
  metrics: BacktestMetrics;
  trades: TradeRecord[];
  equity_curve: { ts: string; equity: number }[];
  duration_ms: number;
}

export default function BacktestPage() {
  const [ruleName, setRuleName] = useState('Momentum Backtest');
  const [timeframe, setTimeframe] = useState('5m');
  const [symbolsStr, setSymbolsStr] = useState('NIFTY,BANKNIFTY');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [positionSizePct, setPositionSizePct] = useState(10);
  const [exitAfterBars, setExitAfterBars] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState('');

  const runBacktest = async () => {
    setLoading(true);
    setResult(null);
    setError('');
    try {
      const symbols = symbolsStr.split(',').map(s => s.trim()).filter(Boolean);
      if (!symbols.length) {
        setError('Add at least one symbol');
        return;
      }
      const res = await fetch('/api/v1/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rule: {
            name: ruleName,
            timeframe,
            logic: 'AND',
            rules: [
              { field: 'rsi(14)', operator: '>', value: 60 },
              { field: 'ema(close,20)', operator: '>', compare: 'ema(close,50)' },
            ],
          },
          symbols,
          start_date: startDate,
          end_date: endDate,
          timeframe,
          initial_capital: initialCapital,
          position_size_pct: positionSizePct,
          exit_after_bars: exitAfterBars,
          allow_short: false,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Backtest failed');
        return;
      }
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface-50">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold text-zinc-900">StrikeGenius.ai</Link>
          <span className="text-sm text-zinc-500">Backtest</span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6">
        <h1 className="text-xl font-bold text-zinc-900 mb-4">Historical backtest</h1>
        <p className="text-sm text-zinc-600 mb-6">Run your scan rule on TimescaleDB candles. Win rate, PnL, drawdown, Sharpe, expectancy.</p>

        <div className="grid gap-4 sm:grid-cols-2 mb-6">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Rule name</label>
            <input
              type="text"
              value={ruleName}
              onChange={e => setRuleName(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border border-surface-200"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Timeframe</label>
            <select
              value={timeframe}
              onChange={e => setTimeframe(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border border-surface-200"
            >
              <option value="5m">5m</option>
              <option value="15m">15m</option>
              <option value="1h">1h</option>
              <option value="1d">1d</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Symbols (comma)</label>
            <input
              type="text"
              value={symbolsStr}
              onChange={e => setSymbolsStr(e.target.value)}
              placeholder="NIFTY, BANKNIFTY"
              className="w-full px-4 py-2 rounded-xl border border-surface-200"
            />
          </div>
          <div className="sm:col-span-2 grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">Start date</label>
              <input
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border border-surface-200"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-700 mb-1">End date</label>
              <input
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                className="w-full px-4 py-2 rounded-xl border border-surface-200"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Initial capital (₹)</label>
            <input
              type="number"
              value={initialCapital}
              onChange={e => setInitialCapital(Number(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-surface-200"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Position size %</label>
            <input
              type="number"
              min={1}
              max={100}
              value={positionSizePct}
              onChange={e => setPositionSizePct(Number(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-surface-200"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1">Exit after bars</label>
            <input
              type="number"
              min={1}
              value={exitAfterBars}
              onChange={e => setExitAfterBars(Number(e.target.value))}
              className="w-full px-4 py-2 rounded-xl border border-surface-200"
            />
          </div>
        </div>

        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
        <button
          onClick={runBacktest}
          disabled={loading}
          className="w-full sm:w-auto px-8 py-3 rounded-xl bg-primary-600 text-white font-medium disabled:opacity-50"
        >
          {loading ? 'Running backtest…' : 'Run backtest'}
        </button>

        {result && (
          <div className="mt-8 space-y-6">
            <h2 className="text-lg font-semibold text-zinc-900">Report</h2>
            <div className="p-4 rounded-2xl bg-white border border-surface-200">
              <p className="text-sm text-zinc-500 mb-2">{result.rule_name} · {result.start_date} → {result.end_date} · {result.duration_ms}ms</p>
              <p className="text-sm text-zinc-600">Initial: ₹{result.initial_capital.toLocaleString()} → Final: ₹{result.final_equity.toLocaleString()}</p>
            </div>

            <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
              <MetricCard label="Win rate" value={`${result.metrics.win_rate}%`} />
              <MetricCard label="Total PnL" value={`₹${result.metrics.total_pnl.toLocaleString()}`} sub={result.metrics.total_pnl_pct !== undefined ? `${result.metrics.total_pnl_pct}%` : undefined} />
              <MetricCard label="Max drawdown" value={`₹${result.metrics.max_drawdown.toLocaleString()}`} sub={result.metrics.max_drawdown_pct !== undefined ? `${result.metrics.max_drawdown_pct}%` : undefined} />
              <MetricCard label="Sharpe" value={String(result.metrics.sharpe_ratio)} />
              <MetricCard label="Expectancy" value={`₹${result.metrics.expectancy.toLocaleString()}`} />
              <MetricCard label="Trades" value={String(result.metrics.total_trades)} sub={`W:${result.metrics.winning_trades} L:${result.metrics.losing_trades}`} />
              <MetricCard label="Profit factor" value={String(result.metrics.profit_factor)} />
            </div>

            {result.equity_curve.length > 0 && (
              <div className="p-4 rounded-2xl bg-white border border-surface-200">
                <h3 className="text-sm font-medium text-zinc-700 mb-2">Equity curve</h3>
                <div className="h-48 flex items-end gap-px">
                  {result.equity_curve.filter((_, i) => i % Math.max(1, Math.floor(result.equity_curve.length / 80)) === 0).map((p, i) => {
                    const maxEq = Math.max(...result.equity_curve.map(x => x.equity));
                    const minEq = Math.min(...result.equity_curve.map(x => x.equity));
                    const h = maxEq > minEq ? ((p.equity - minEq) / (maxEq - minEq)) * 100 : 50;
                    return <div key={i} className="flex-1 min-w-0 bg-primary-500 rounded-t" style={{ height: `${h}%` }} title={`${p.ts} ₹${p.equity}`} />;
                  })}
                </div>
                <p className="text-xs text-zinc-500 mt-2">Start ₹{result.equity_curve[0]?.equity} → End ₹{result.equity_curve[result.equity_curve.length - 1]?.equity}</p>
              </div>
            )}

            <div className="rounded-2xl bg-white border border-surface-200 overflow-hidden">
              <h3 className="text-sm font-medium text-zinc-700 p-3 border-b border-surface-200">Trades ({result.trades.length})</h3>
              <div className="overflow-x-auto max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-zinc-500 border-b border-surface-200">
                      <th className="p-2">Symbol</th>
                      <th className="p-2">Entry</th>
                      <th className="p-2">Exit</th>
                      <th className="p-2">PnL</th>
                      <th className="p-2">PnL %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.slice(0, 50).map((t, i) => (
                      <tr key={i} className="border-b border-surface-100">
                        <td className="p-2 font-medium">{t.symbol}</td>
                        <td className="p-2 text-zinc-600">{t.entry_price.toFixed(2)}</td>
                        <td className="p-2 text-zinc-600">{t.exit_price.toFixed(2)}</td>
                        <td className={`p-2 ${t.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>{t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}</td>
                        <td className={`p-2 ${t.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>{t.pnl_pct >= 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {result.trades.length > 50 && <p className="p-2 text-xs text-zinc-500">Showing first 50 of {result.trades.length}</p>}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="p-4 rounded-xl bg-white border border-surface-200">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="text-lg font-semibold text-zinc-900">{value}</p>
      {sub != null && <p className="text-xs text-zinc-500">{sub}</p>}
    </div>
  );
}

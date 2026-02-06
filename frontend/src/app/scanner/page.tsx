'use client';

import { useState } from 'react';
import Link from 'next/link';

interface ScanResultRow {
  symbol: string;
  strike: number;
  option_type: string;
  score: number;
  matched_rules: string[];
}

export default function ScannerPage() {
  const [ruleName, setRuleName] = useState('Super Momentum Options');
  const [timeframe, setTimeframe] = useState('5m');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScanResultRow[]>([]);
  const [durationMs, setDurationMs] = useState(0);

  const runScan = async () => {
    setLoading(true);
    setResults([]);
    try {
      const res = await fetch('/api/v1/scans/run', {
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
              { field: 'oi_change(5)', operator: '>', value: 8 },
            ],
          },
          max_results: 50,
        }),
      });
      const data = await res.json();
      setResults(data.results || []);
      setDurationMs(data.duration_ms ?? 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface-50">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold text-zinc-900">StrikeGenius.ai</Link>
          <span className="text-sm text-zinc-500">Scanner</span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6">
        <div className="mb-6 p-4 rounded-2xl bg-white border border-surface-200">
          <label className="block text-sm font-medium text-zinc-700 mb-2">Rule name</label>
          <input
            type="text"
            value={ruleName}
            onChange={(e) => setRuleName(e.target.value)}
            className="w-full px-4 py-2 rounded-xl border border-surface-200 mb-4"
          />
          <label className="block text-sm font-medium text-zinc-700 mb-2">Timeframe</label>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="w-full px-4 py-2 rounded-xl border border-surface-200 mb-4"
          >
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="1d">1d</option>
          </select>
          <button
            onClick={runScan}
            disabled={loading}
            className="w-full py-3 rounded-xl bg-primary-600 text-white font-medium touch-target disabled:opacity-50"
          >
            {loading ? 'Scanning…' : 'Run scan'}
          </button>
        </div>

        {durationMs > 0 && (
          <p className="text-sm text-zinc-500 mb-2">Completed in {durationMs}ms · {results.length} results</p>
        )}

        <div className="rounded-2xl bg-white border border-surface-200 overflow-hidden">
          {results.length === 0 && !loading && (
            <div className="p-8 text-center text-zinc-500">Run a scan to see results.</div>
          )}
          {results.length > 0 && (
            <ul className="divide-y divide-surface-200">
              {results.map((r, i) => (
                <li key={i} className="p-4 flex justify-between items-start">
                  <div>
                    <span className="font-medium text-zinc-900">{r.symbol}</span>
                    <span className="text-zinc-500 ml-2">{r.option_type}</span>
                    <p className="text-xs text-zinc-500 mt-1">{r.matched_rules?.slice(0, 2).join(' · ')}</p>
                  </div>
                  <span className="text-primary-600 font-semibold">Edge {r.score}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

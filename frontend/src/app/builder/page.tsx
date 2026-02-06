'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  type RuleBlock,
  type CompositeBlock,
  type LeafBlock,
  isLeaf,
  isComposite,
  toScanRuleAST,
  emptyRoot,
  defaultLeaf,
  astToCompositeBlock,
  type ScanRuleAST,
  ROOT_PARENT_ID,
  findBlock,
  moveBlock,
  containsBlock,
} from './types';

const OPERATORS = [
  '>', '<', '>=', '<=', '==', '!=',
  'cross_above', 'cross_below', 'touches', 'rejects',
  'rising', 'falling', 'flat',
  'breakout', 'breakdown', 'inside_range', 'gap_up', 'gap_down',
  'percentile', 'zscore', 'stddev',
];

const INDICATOR_PRESETS: { label: string; value: string }[] = [
  { label: 'RSI(14)', value: 'rsi(14)' },
  { label: 'RSI(volume,14)', value: 'rsi(volume,14)' },
  { label: 'EMA(close,20)', value: 'ema(close,20)' },
  { label: 'EMA(close,50)', value: 'ema(close,50)' },
  { label: 'SMA(close,20)', value: 'sma(close,20)' },
  { label: 'MACD(close)', value: 'macd(close)' },
  { label: 'ATR(14)', value: 'atr(14)' },
  { label: 'OBV', value: 'obv' },
  { label: 'Close', value: 'close' },
  { label: 'Volume', value: 'volume' },
  { label: 'OI change(5)', value: 'oi_change(5)' },
  { label: 'PCR', value: 'pcr' },
];

export default function BuilderPage() {
  const [ruleName, setRuleName] = useState('My Scan');
  const [timeframe, setTimeframe] = useState('5m');
  const [root, setRoot] = useState<CompositeBlock>(() => ({ ...emptyRoot(), children: [defaultLeaf()] }));
  type DragState = { nodeId: string; parentId: string; sourceIndex: number };
  const [drag, setDrag] = useState<DragState | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [validateMsg, setValidateMsg] = useState<string | null>(null);
  const [indicators, setIndicators] = useState<{ categories: Record<string, string[]>; all: string[] }>({ categories: {}, all: [] });
  const [templates, setTemplates] = useState<{ id: string; name: string; rule_ast: ScanRuleAST }[]>([]);

  const [simStartDate, setSimStartDate] = useState('2024-01-01');
  const [simEndDate, setSimEndDate] = useState('2024-12-31');
  const [simSymbolsStr, setSimSymbolsStr] = useState('NIFTY,BANKNIFTY');
  const [simulateLoading, setSimulateLoading] = useState(false);
  const [simulateResult, setSimulateResult] = useState<{
    total_signals: number;
    signals_by_symbol: Record<string, number>;
    signals: { symbol: string; ts: string }[];
    first_ts: string | null;
    last_ts: string | null;
    bars_evaluated: number;
    duration_ms: number;
    start_date: string;
    end_date: string;
    rule_name: string;
    timeframe: string;
  } | null>(null);
  const [simulateError, setSimulateError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/v1/indicators/list')
      .then(r => r.json())
      .then(d => setIndicators(d))
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/v1/scans/templates', { credentials: 'include' })
      .then(r => r.ok ? r.json() : [])
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, []);

  const getAST = useCallback((): ScanRuleAST => toScanRuleAST(ruleName, timeframe, root), [ruleName, timeframe, root]);

  const updateRoot = useCallback((updater: (prev: CompositeBlock) => CompositeBlock) => {
    setRoot(updater);
  }, []);

  const canDrop = useCallback(
    (targetParentId: string, targetIndex: number): boolean => {
      if (!drag) return false;
      const src = findBlock(root, drag.nodeId);
      if (!src) return false;
      if (drag.parentId === targetParentId && drag.sourceIndex === targetIndex) return false;
      if (drag.parentId === targetParentId && drag.sourceIndex === targetIndex - 1) return false;
      if (src.block.id === targetParentId) return false;
      if (isComposite(src.block) && containsBlock(src.block, targetParentId)) return false;
      return true;
    },
    [drag, root]
  );

  const handleMove = useCallback(
    (targetParentId: string, targetIndex: number) => {
      if (!drag || !canDrop(targetParentId, targetIndex)) return;
      setRoot(prev =>
        moveBlock(prev, drag.parentId, drag.sourceIndex, targetParentId, targetIndex)
      );
      setDrag(null);
    },
    [drag, canDrop]
  );

  const runScan = async () => {
    setLoading(true);
    setResults([]);
    try {
      const res = await fetch('/api/v1/scans/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule: getAST(), max_results: 50 }),
      });
      const data = await res.json();
      if (res.ok) setResults(data.results || []);
    } finally {
      setLoading(false);
    }
  };

  const validate = async () => {
    setValidateMsg(null);
    try {
      const res = await fetch('/api/v1/scans/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(getAST()),
      });
      const data = await res.json();
      setValidateMsg(res.ok ? (data.message || 'Valid') : (data.detail || 'Invalid'));
    } catch {
      setValidateMsg('Request failed');
    }
  };

  const saveTemplate = async () => {
    try {
      const res = await fetch('/api/v1/scans/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name: ruleName,
          description: `Rule: ${ruleName}`,
          rule_ast: getAST(),
          is_public: false,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setTemplates(prev => [...prev, { id: data.id, name: data.name, rule_ast: getAST() }]);
        setValidateMsg('Template saved');
      } else {
        setValidateMsg('Save failed (login required)');
      }
    } catch {
      setValidateMsg('Save failed');
    }
  };

  const loadTemplate = (t: { rule_ast: ScanRuleAST }) => {
    const ast = t.rule_ast;
    setRuleName(ast.name);
    setTimeframe(ast.timeframe);
    setRoot(astToCompositeBlock({ logic: ast.logic, rules: ast.rules || [] }));
  };

  const runSimulate = async () => {
    setSimulateLoading(true);
    setSimulateResult(null);
    setSimulateError(null);
    try {
      const symbols = simSymbolsStr.split(',').map(s => s.trim()).filter(Boolean);
      if (!symbols.length) {
        setSimulateError('Add at least one symbol');
        return;
      }
      const res = await fetch('/api/v1/scans/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rule: getAST(),
          symbols,
          start_date: simStartDate,
          end_date: simEndDate,
          timeframe,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSimulateResult(data);
      } else {
        setSimulateError(data.detail || 'Simulation failed');
      }
    } catch {
      setSimulateError('Request failed');
    } finally {
      setSimulateLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface-50">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold text-zinc-900">StrikeGenius.ai</Link>
          <Link href="/scanner" className="text-sm text-primary-600">Simple scanner</Link>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6">
        <h1 className="text-xl font-bold text-zinc-900 mb-4">Visual rule builder</h1>

        <div className="flex flex-wrap gap-4 mb-4">
          <input
            type="text"
            placeholder="Rule name"
            value={ruleName}
            onChange={e => setRuleName(e.target.value)}
            className="px-4 py-2 rounded-xl border border-surface-200"
          />
          <select
            value={timeframe}
            onChange={e => setTimeframe(e.target.value)}
            className="px-4 py-2 rounded-xl border border-surface-200"
          >
            <option value="5m">5m</option>
            <option value="15m">15m</option>
            <option value="1h">1h</option>
            <option value="1d">1d</option>
          </select>
          <button type="button" onClick={validate} className="px-4 py-2 rounded-xl border border-surface-200 hover:bg-surface-100">
            Validate
          </button>
          <button type="button" onClick={saveTemplate} className="px-4 py-2 rounded-xl border border-primary-500 text-primary-600 hover:bg-primary-50">
            Save template
          </button>
        </div>

        {validateMsg && (
          <p className={`text-sm mb-4 ${validateMsg.startsWith('Valid') || validateMsg === 'Template saved' ? 'text-green-600' : 'text-amber-600'}`}>
            {validateMsg}
          </p>
        )}

        {templates.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="text-sm text-zinc-500">Load:</span>
            {templates.map(t => (
              <button
                key={t.id}
                type="button"
                onClick={() => loadTemplate(t)}
                className="px-3 py-1 rounded-lg bg-surface-200 text-sm hover:bg-surface-300"
              >
                {t.name}
              </button>
            ))}
          </div>
        )}

        <div className="mb-4 p-4 rounded-2xl bg-white border border-surface-200">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-medium text-zinc-700">Match</span>
            <select
              value={root.logic}
              onChange={e => updateRoot(prev => ({ ...prev, logic: e.target.value as 'AND' | 'OR' }))}
              className="px-3 py-1.5 rounded-lg border border-surface-200"
            >
              <option value="AND">All (AND)</option>
              <option value="OR">Any (OR)</option>
            </select>
            <span className="text-xs text-zinc-500">of the following</span>
          </div>
          <RuleBlockList
            parentId={ROOT_PARENT_ID}
            blocks={root.children}
            onChange={children => updateRoot(prev => ({ ...prev, children }))}
            root={root}
            drag={drag}
            setDrag={setDrag}
            canDrop={canDrop}
            onMove={handleMove}
            onAddLeaf={() => updateRoot(prev => ({ ...prev, children: [...prev.children, defaultLeaf()] }))}
            onAddGroup={() => updateRoot(prev => ({
              ...prev,
              children: [...prev.children, { id: crypto.randomUUID(), type: 'composite', logic: 'AND', children: [defaultLeaf()] }],
            }))}
          />
        </div>

        <div className="mb-4 p-4 rounded-2xl bg-white border border-surface-200">
          <h2 className="text-sm font-semibold text-zinc-800 mb-3">Rule simulation</h2>
          <p className="text-xs text-zinc-500 mb-3">Run this rule on historical candles and see when it would have fired.</p>
          <div className="flex flex-wrap items-end gap-3 mb-3">
            <label className="flex flex-col gap-1">
              <span className="text-xs text-zinc-500">Start</span>
              <input
                type="date"
                value={simStartDate}
                onChange={e => setSimStartDate(e.target.value)}
                className="px-3 py-2 rounded-lg border border-surface-200 text-sm"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-zinc-500">End</span>
              <input
                type="date"
                value={simEndDate}
                onChange={e => setSimEndDate(e.target.value)}
                className="px-3 py-2 rounded-lg border border-surface-200 text-sm"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs text-zinc-500">Symbols</span>
              <input
                type="text"
                placeholder="NIFTY,BANKNIFTY"
                value={simSymbolsStr}
                onChange={e => setSimSymbolsStr(e.target.value)}
                className="px-3 py-2 rounded-lg border border-surface-200 text-sm w-40"
              />
            </label>
            <button
              type="button"
              onClick={runSimulate}
              disabled={simulateLoading}
              className="px-4 py-2 rounded-xl bg-primary-600 text-white text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {simulateLoading ? 'Simulating…' : 'Simulate'}
            </button>
          </div>
          {simulateError && (
            <p className="text-sm text-amber-600 mb-3">{simulateError}</p>
          )}
          {simulateResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-surface-50 border border-surface-200">
                  <p className="text-xs text-zinc-500">Total signals</p>
                  <p className="text-xl font-semibold text-zinc-900">{simulateResult.total_signals}</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-50 border border-surface-200">
                  <p className="text-xs text-zinc-500">Bars evaluated</p>
                  <p className="text-xl font-semibold text-zinc-900">{simulateResult.bars_evaluated.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-50 border border-surface-200">
                  <p className="text-xs text-zinc-500">Duration</p>
                  <p className="text-xl font-semibold text-zinc-900">{simulateResult.duration_ms} ms</p>
                </div>
                <div className="p-3 rounded-xl bg-surface-50 border border-surface-200">
                  <p className="text-xs text-zinc-500">First / last signal</p>
                  <p className="text-xs font-medium text-zinc-700 truncate" title={simulateResult.first_ts ?? ''}>
                    {simulateResult.first_ts ? new Date(simulateResult.first_ts).toLocaleString() : '—'}
                  </p>
                  <p className="text-xs text-zinc-500 truncate" title={simulateResult.last_ts ?? ''}>
                    {simulateResult.last_ts ? new Date(simulateResult.last_ts).toLocaleString() : '—'}
                  </p>
                </div>
              </div>
              {Object.keys(simulateResult.signals_by_symbol).length > 0 && (
                <div>
                  <p className="text-xs font-medium text-zinc-600 mb-2">Signals by symbol</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(simulateResult.signals_by_symbol).map(([sym, count]) => (
                      <span key={sym} className="px-2 py-1 rounded-lg bg-primary-50 text-primary-700 text-sm">
                        {sym}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <SignalChart signals={simulateResult.signals} />
            </div>
          )}
        </div>

        <details className="mb-4 rounded-2xl bg-white border border-surface-200 overflow-hidden">
          <summary className="p-3 cursor-pointer text-sm font-medium text-zinc-700">Preview AST</summary>
          <pre className="p-4 text-xs bg-surface-50 overflow-auto max-h-64 border-t border-surface-200">
            {JSON.stringify(getAST(), null, 2)}
          </pre>
        </details>

        <button
          onClick={runScan}
          disabled={loading}
          className="w-full py-3 rounded-xl bg-primary-600 text-white font-medium disabled:opacity-50"
        >
          {loading ? 'Scanning…' : 'Run scan'}
        </button>

        {results.length > 0 && (
          <div className="mt-6 rounded-2xl bg-white border border-surface-200 overflow-hidden">
            <p className="p-3 text-sm text-zinc-500">{results.length} results</p>
            <ul className="divide-y divide-surface-200">
              {results.slice(0, 20).map((r: Record<string, unknown>, i: number) => (
                <li key={i} className="p-3 flex justify-between">
                  <span className="font-medium">{String(r.symbol)}</span>
                  <span className="text-primary-600">Edge {Number(r.score)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}

function RuleBlockList({
  parentId,
  blocks,
  onChange,
  root,
  drag,
  setDrag,
  canDrop,
  onMove,
  onAddLeaf,
  onAddGroup,
  depth = 0,
}: {
  parentId: string;
  blocks: RuleBlock[];
  onChange: (blocks: RuleBlock[]) => void;
  root: CompositeBlock;
  drag: { nodeId: string; parentId: string; sourceIndex: number } | null;
  setDrag: (d: { nodeId: string; parentId: string; sourceIndex: number } | null) => void;
  canDrop: (targetParentId: string, targetIndex: number) => boolean;
  onMove: (targetParentId: string, targetIndex: number) => void;
  onAddLeaf: () => void;
  onAddGroup: () => void;
  depth?: number;
}) {
  const updateAt = (idx: number, block: RuleBlock) => {
    const next = [...blocks];
    next[idx] = block;
    onChange(next);
  };
  const removeAt = (idx: number) => onChange(blocks.filter((_, i) => i !== idx));

  return (
    <div className="space-y-2" style={{ marginLeft: depth ? 16 : 0 }}>
      {blocks.map((block, idx) => (
        <div key={block.id}>
          <DropZone
            parentId={parentId}
            index={idx}
            canDrop={canDrop}
            onDrop={onMove}
          />
          {isLeaf(block) ? (
            <LeafBlockEditor
              block={block}
              onChange={upd => updateAt(idx, { ...block, ...upd })}
              onRemove={() => removeAt(idx)}
              onDragStart={() => setDrag({ nodeId: block.id, parentId, sourceIndex: idx })}
              onDragEnd={() => setDrag(null)}
              isDragging={drag?.nodeId === block.id}
            />
          ) : (
            <CompositeBlockEditor
              block={block}
              parentId={parentId}
              index={idx}
              onChange={b => updateAt(idx, b)}
              onRemove={() => removeAt(idx)}
              root={root}
              drag={drag}
              setDrag={setDrag}
              canDrop={canDrop}
              onMove={onMove}
              depth={depth + 1}
            />
          )}
        </div>
      ))}
      <DropZone
        parentId={parentId}
        index={blocks.length}
        canDrop={canDrop}
        onDrop={onMove}
      />
      <div className="flex gap-2 mt-2">
        <button type="button" onClick={onAddLeaf} className="text-sm text-primary-600 font-medium">+ Condition</button>
        <button type="button" onClick={onAddGroup} className="text-sm text-zinc-600">+ AND/OR group</button>
      </div>
    </div>
  );
}

function SignalChart({ signals }: { signals: { symbol: string; ts: string }[] }) {
  if (signals.length === 0) {
    return (
      <div className="rounded-xl border border-surface-200 bg-surface-50 p-4 text-center text-sm text-zinc-500">
        No signals in range
      </div>
    );
  }
  const byDay: Record<string, number> = {};
  for (const s of signals) {
    const day = s.ts.slice(0, 10);
    byDay[day] = (byDay[day] ?? 0) + 1;
  }
  const days = Object.keys(byDay).sort();
  const maxCount = Math.max(...Object.values(byDay), 1);
  return (
    <div>
      <p className="text-xs font-medium text-zinc-600 mb-2">Signals over time (by day)</p>
      <div className="flex items-end gap-0.5 h-24" aria-label="Signal count per day">
        {days.map(day => (
          <div
            key={day}
            className="flex-1 min-w-[4px] rounded-t bg-primary-500 hover:bg-primary-600 transition-colors"
            style={{ height: `${Math.max(4, (byDay[day] / maxCount) * 100)}%` }}
            title={`${day}: ${byDay[day]} signals`}
          />
        ))}
      </div>
      <div className="flex justify-between mt-1 text-xs text-zinc-500">
        <span>{days[0]}</span>
        <span>{days[days.length - 1]}</span>
      </div>
      <p className="mt-2 text-xs text-zinc-500">Latest signals (up to 10)</p>
      <ul className="mt-1 text-xs text-zinc-700 space-y-0.5">
        {signals.slice(-10).reverse().map((s, i) => (
          <li key={i}>{s.symbol} — {new Date(s.ts).toLocaleString()}</li>
        ))}
      </ul>
    </div>
  );
}

function DropZone({
  parentId,
  index,
  canDrop,
  onDrop,
}: {
  parentId: string;
  index: number;
  canDrop: (targetParentId: string, targetIndex: number) => boolean;
  onDrop: (targetParentId: string, targetIndex: number) => void;
}) {
  const [over, setOver] = useState(false);
  const valid = canDrop(parentId, index);
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setOver(false);
    if (valid) onDrop(parentId, index);
  };
  return (
    <div
      onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = valid ? 'move' : 'none'; setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={handleDrop}
      className={`min-h-[10px] rounded transition-all flex items-center justify-center ${
        !over ? 'bg-transparent' : valid ? 'bg-primary-400 ring-2 ring-primary-500 ring-inset' : 'bg-red-200/80 ring-2 ring-red-400 ring-inset'
      }`}
    >
      {over && valid && <span className="text-xs text-white font-medium">Drop here</span>}
    </div>
  );
}

function LeafBlockEditor({
  block,
  onChange,
  onRemove,
  onDragStart,
  onDragEnd,
  isDragging,
}: {
  block: LeafBlock;
  onChange: (upd: Partial<LeafBlock>) => void;
  onRemove: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  isDragging: boolean;
}) {
  const needsValue = !['rising', 'falling', 'flat', 'breakout', 'breakdown', 'inside_range', 'gap_up', 'gap_down'].includes(block.operator);
  const needsN = ['rising', 'falling', 'flat', 'breakout', 'breakdown'].includes(block.operator);
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={`flex flex-wrap items-center gap-2 p-3 rounded-xl border bg-white touch-target ${isDragging ? 'opacity-50 border-primary-500' : 'border-surface-200'}`}
    >
      <span className="cursor-grab text-zinc-400 active:cursor-grabbing" title="Drag">⋮⋮</span>
      <select
        value={INDICATOR_PRESETS.some(p => p.value === block.field) ? block.field : '__custom__'}
        onChange={e => onChange({ field: e.target.value === '__custom__' ? block.field : e.target.value })}
        className="px-2 py-1.5 rounded-lg border border-surface-200 text-sm min-w-[140px]"
      >
        {INDICATOR_PRESETS.map(p => (
          <option key={p.value} value={p.value}>{p.label}</option>
        ))}
        <option value="__custom__">Custom...</option>
      </select>
      {!INDICATOR_PRESETS.some(p => p.value === block.field) && (
        <input
          type="text"
          placeholder="e.g. ema(close,9)"
          value={block.field}
          onChange={e => onChange({ field: e.target.value })}
          className="px-2 py-1.5 rounded-lg border border-surface-200 text-sm w-32"
        />
      )}
      <select
        value={block.operator}
        onChange={e => onChange({ operator: e.target.value })}
        className="px-2 py-1.5 rounded-lg border border-surface-200 text-sm"
      >
        {OPERATORS.map(op => (
          <option key={op} value={op}>{op}</option>
        ))}
      </select>
      {needsValue && (
        <input
          type="number"
          placeholder="Value"
          value={block.value ?? ''}
          onChange={e => onChange({ value: e.target.value ? Number(e.target.value) : undefined })}
          className="w-20 px-2 py-1.5 rounded-lg border border-surface-200 text-sm"
        />
      )}
      {needsN && (
        <input
          type="number"
          placeholder="n"
          value={block.n ?? ''}
          onChange={e => onChange({ n: e.target.value ? Number(e.target.value) : undefined })}
          className="w-14 px-2 py-1.5 rounded-lg border border-surface-200 text-sm"
        />
      )}
      <button type="button" onClick={onRemove} className="text-red-500 text-sm ml-auto">Remove</button>
    </div>
  );
}

function CompositeBlockEditor({
  block,
  parentId,
  index,
  onChange,
  onRemove,
  root,
  drag,
  setDrag,
  canDrop,
  onMove,
  depth,
}: {
  block: CompositeBlock;
  parentId: string;
  index: number;
  onChange: (b: CompositeBlock) => void;
  onRemove: () => void;
  root: CompositeBlock;
  drag: { nodeId: string; parentId: string; sourceIndex: number } | null;
  setDrag: (d: { nodeId: string; parentId: string; sourceIndex: number } | null) => void;
  canDrop: (targetParentId: string, targetIndex: number) => boolean;
  onMove: (targetParentId: string, targetIndex: number) => void;
  depth: number;
}) {
  const isDragging = drag?.nodeId === block.id;
  return (
    <div
      draggable
      onDragStart={() => setDrag({ nodeId: block.id, parentId, sourceIndex: index })}
      onDragEnd={() => setDrag(null)}
      className={`rounded-xl border-2 border-dashed border-surface-300 bg-surface-50/50 p-3 ${isDragging ? 'opacity-50 border-primary-500' : ''}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="cursor-grab text-zinc-400 active:cursor-grabbing" title="Drag group">⋮⋮</span>
        <select
          value={block.logic}
          onChange={e => onChange({ ...block, logic: e.target.value as 'AND' | 'OR' })}
          className="px-2 py-1 rounded-lg border border-surface-200 text-sm font-medium"
        >
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
        <span className="text-xs text-zinc-500">({block.children.length} items)</span>
        <button type="button" onClick={onRemove} className="text-red-500 text-sm ml-auto">Remove group</button>
      </div>
      <RuleBlockList
        parentId={block.id}
        blocks={block.children}
        onChange={children => onChange({ ...block, children })}
        root={root}
        drag={drag}
        setDrag={setDrag}
        canDrop={canDrop}
        onMove={onMove}
        onAddLeaf={() => onChange({ ...block, children: [...block.children, defaultLeaf()] })}
        onAddGroup={() => onChange({
          ...block,
          children: [...block.children, { id: crypto.randomUUID(), type: 'composite', logic: 'AND', children: [defaultLeaf()] }],
        })}
        depth={depth}
      />
    </div>
  );
}

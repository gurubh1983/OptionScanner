'use client';

import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <span className="font-semibold text-lg text-zinc-900">StrikeGenius.ai</span>
          <nav className="flex gap-4">
            <Link href="/login" className="text-sm text-zinc-600 hover:text-primary-600">Log in</Link>
            <Link href="/pricing" className="text-sm font-medium text-primary-600">Pricing</Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-12 md:py-20">
        <section className="text-center mb-16">
          <h1 className="text-3xl md:text-4xl font-bold text-zinc-900 tracking-tight mb-4">
            Chartink + TradingView + Option Chain + AI
          </h1>
          <p className="text-lg text-zinc-600 max-w-xl mx-auto mb-8">
            One platform. Every strike. Infinite rules. Indian options, built for scale.
          </p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link
              href="/scanner"
              className="inline-flex items-center justify-center touch-target px-8 py-3 rounded-xl bg-primary-600 text-white font-medium shadow-sm hover:bg-primary-700 active:scale-[0.98] transition"
            >
              Open Scanner
            </Link>
            <Link
              href="/builder"
              className="inline-flex items-center justify-center touch-target px-8 py-3 rounded-xl border border-primary-600 text-primary-600 font-medium hover:bg-primary-50 transition"
            >
              No-code Builder
            </Link>
            <Link
              href="/backtest"
              className="inline-flex items-center justify-center touch-target px-8 py-3 rounded-xl border border-surface-300 text-zinc-700 font-medium hover:bg-surface-100 transition"
            >
              Backtest
            </Link>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2 mb-16">
          {[
            { title: 'Universal rules', desc: 'Nested AND/OR, unlimited depth, full indicator library.' },
            { title: 'Edge Score™', desc: 'Every signal scored 0–100. Know your edge.' },
            { title: 'Heatmap & Replay', desc: 'Live strike heatmap, replay any market day.' },
            { title: 'AI pattern discovery', desc: 'Cluster setups, suggest scans, auto-optimize.' },
          ].map(({ title, desc }) => (
            <div key={title} className="p-5 rounded-2xl bg-white border border-surface-200 shadow-sm">
              <h3 className="font-semibold text-zinc-900 mb-1">{title}</h3>
              <p className="text-sm text-zinc-600">{desc}</p>
            </div>
          ))}
        </section>

        <section className="text-center text-sm text-zinc-500 safe-bottom pb-8">
          <p>Target: &lt;150ms scan · &lt;300ms load · Mobile-first</p>
        </section>
      </main>
    </div>
  );
}

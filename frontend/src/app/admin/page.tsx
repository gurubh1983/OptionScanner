'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface AdminStats {
  users_total: number;
  scans_today: number;
  active_subscriptions: number;
  alerts_delivered_today: number;
}

export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/admin/stats')
      .then(r => r.json())
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-surface-50">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold text-zinc-900">StrikeGenius.ai</Link>
          <span className="text-sm text-zinc-500">Admin</span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        <h1 className="text-2xl font-bold text-zinc-900 mb-6">Admin dashboard</h1>
        {loading && <p className="text-zinc-500">Loading…</p>}
        {!loading && stats && (
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="p-5 rounded-2xl bg-white border border-surface-200">
              <p className="text-sm text-zinc-500">Total users</p>
              <p className="text-2xl font-bold text-zinc-900">{stats.users_total}</p>
            </div>
            <div className="p-5 rounded-2xl bg-white border border-surface-200">
              <p className="text-sm text-zinc-500">Scans today</p>
              <p className="text-2xl font-bold text-zinc-900">{stats.scans_today}</p>
            </div>
            <div className="p-5 rounded-2xl bg-white border border-surface-200">
              <p className="text-sm text-zinc-500">Active subscriptions</p>
              <p className="text-2xl font-bold text-zinc-900">{stats.active_subscriptions}</p>
            </div>
            <div className="p-5 rounded-2xl bg-white border border-surface-200">
              <p className="text-sm text-zinc-500">Alerts delivered today</p>
              <p className="text-2xl font-bold text-zinc-900">{stats.alerts_delivered_today}</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

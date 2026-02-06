'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Plan {
  id: string;
  name: string;
  price_inr: number;
  price_usd: number;
  scans_per_day: number;
  alerts_per_day: number;
  features: string[];
}

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);

  useEffect(() => {
    fetch('/api/v1/billing/plans')
      .then((r) => r.json())
      .then(setPlans)
      .catch(() => setPlans([]));
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-surface-50">
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur-md border-b border-surface-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold text-zinc-900">StrikeGenius.ai</Link>
          <Link href="/login" className="text-sm text-zinc-600">Log in</Link>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-12">
        <h1 className="text-2xl font-bold text-zinc-900 mb-2">Pricing</h1>
        <p className="text-zinc-600 mb-8">Free, Pro, Elite. Razorpay & Stripe. GST invoices.</p>

        <div className="grid gap-6 md:grid-cols-3">
          {(plans.length ? plans : [
            { id: 'free', name: 'Free', price_inr: 0, price_usd: 0, scans_per_day: 5, alerts_per_day: 5, features: ['5 scans', '5 alerts/day', 'Delayed data'] },
            { id: 'pro', name: 'Pro', price_inr: 999, price_usd: 12, scans_per_day: -1, alerts_per_day: -1, features: ['Unlimited scans', 'Live data', 'Backtest', 'Telegram'] },
            { id: 'elite', name: 'Elite', price_inr: 2499, price_usd: 30, scans_per_day: -1, alerts_per_day: -1, features: ['AI signals', 'API access', 'Custom indicators', 'Priority support'] },
          ]).map((plan) => (
            <div
              key={plan.id}
              className={`p-6 rounded-2xl border ${
                plan.id === 'pro' ? 'border-primary-500 bg-primary-50/50' : 'border-surface-200 bg-white'
              }`}
            >
              <h3 className="font-semibold text-zinc-900">{plan.name}</h3>
              <p className="mt-2 text-2xl font-bold text-zinc-900">
                {plan.price_inr === 0 ? 'Free' : `₹${plan.price_inr}/mo`}
              </p>
              {plan.price_inr > 0 && <p className="text-sm text-zinc-500">${plan.price_usd}/mo</p>}
              <ul className="mt-4 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="text-sm text-zinc-600">• {f}</li>
                ))}
              </ul>
              <Link
                href={plan.id === 'free' ? '/register' : '/register'}
                className="mt-6 block w-full py-2.5 rounded-xl text-center font-medium border border-surface-200 hover:bg-surface-100"
              >
                {plan.id === 'free' ? 'Get started' : 'Subscribe'}
              </Link>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

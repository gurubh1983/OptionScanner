# StrikeGenius.ai

**Chartink + TradingView + Option Chain + AI = One Platform**

Options Strike Scanner for Indian markets — unlimited rules, Chartink-level power, TradingView-level indicators. Commercial-ready SaaS.

## Product vision

- Scan every option strike with infinite logical rules
- Custom indicators + meta-indicators (indicator on indicator)
- Premium monetization (Free / Pro ₹999 / Elite ₹2499)
- Learning + training, replay engine, heatmap scanner
- Scale to 1L+ users; target &lt;150ms scan, &lt;300ms load

## Tech stack

| Layer        | Stack |
|-------------|--------|
| Backend     | Python 3.11, FastAPI, WebSockets, Celery + Redis |
| Data        | Angel One / Dhan / Zerodha APIs, NSE Bhavcopy |
| Database    | PostgreSQL + TimescaleDB, ClickHouse (analytics) |
| Indicators  | TA-Lib, Pandas-TA, custom indicator SDK |
| Frontend    | Next.js, Tailwind, PWA, mobile-first |
| Auth/Billing| JWT, OAuth, Razorpay, Stripe |
| Infra       | Docker, Kubernetes, AWS/GCP |

## Repo structure

```
OptionScanner/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # Auth, scans, indicators, billing, admin (use services)
│   │   ├── core/             # Config, security
│   │   ├── db/               # Session, async engine
│   │   ├── domain/           # Interfaces (IMarketDataProvider, IBrokerFeed, IPaymentGateway, repos)
│   │   ├── adapters/         # TimescaleDB, Angel/Dhan/Zerodha, Razorpay, Stripe (pluggable)
│   │   ├── repositories/     # User, Plan, Subscription, Scan
│   │   ├── services/         # Auth, Subscription, MarketData, Scanner
│   │   ├── indicators/       # Engine + library (RSI, MACD, ATR, PCR, etc.)
│   │   ├── models/           # User, Scan, ScanRule, Subscription, Plan
│   │   ├── scanner/          # Universal rule AST, engine (full operators)
│   │   ├── backtest/         # Backtest & replay engine (TimescaleDB candles, win rate, PnL, Sharpe)
│   │   └── workers/          # Celery tasks
│   ├── alembic/              # Migrations (001 schema, 002 candles)
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/app/              # Home, login, register, scanner, builder, pricing, admin
│   └── public/manifest.json  # PWA
├── docker-compose.yml
├── SETUP.md                  # Full setup instructions
└── README.md
```

## Quick start

### Backend (local)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env     # edit .env with DB URL and SECRET_KEY
# Start PostgreSQL & Redis (or use docker compose for db + redis only)
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

### Frontend (local)

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:3000  
- API calls are proxied to `http://localhost:8000` via Next.js rewrites.

### Full stack with Docker

```bash
docker compose up -d
# Backend: http://localhost:8000  Frontend: http://localhost:3000
```

### Database initialization

- **On startup** the app runs `Base.metadata.create_all()` so all tables (users, plans, subscriptions, scans, scan_rules, template_purchases, template_ratings) are created if missing. No Alembic run is required for a minimal boot.
- **Plans (billing):** If the `plans` table is empty, `GET /api/v1/billing/plans` returns `[]` and subscription limits fall back to config (`free_scans_per_day`, etc.). To seed Free/Pro/Elite plans, run Alembic: `alembic upgrade head` (migration 001 seeds plans).
- **Disabled features (stubbed):** Template list/save (`GET/POST /api/v1/scans/templates`) return empty list and 503. Template marketplace (`/api/v1/templates/market`) is not mounted. Re-enable by wiring `ScanRuleRepository` in deps and including `templates_market` in `app.api.v1.router`.

## Scanner engine (core)

- **Universal rule format (JSON AST)**  
  Nested AND/OR, unlimited depth. Example:

```json
{
  "name": "Super Momentum Options",
  "timeframe": "5m",
  "logic": "AND",
  "rules": [
    { "logic": "OR", "rules": [
      { "field": "rsi(14)", "operator": ">", "value": 60 },
      { "field": "rsi(volume,14)", "operator": ">", "value": 70 }
    ]},
    { "field": "ema(close,20)", "operator": ">", "compare": "ema(close,50)" },
    { "field": "oi.change(5)", "operator": ">", "value": 8 }
  ]
}
```

- **Operators:** `>`, `<`, `>=`, `<=`, `==`, `!=`, `cross_above`, `cross_below`, `rising`, `falling`, `breakout`, `breakdown`, `percentile`, `zscore`, etc.
- **Indicators:** Price (SMA, EMA, VWAP, Bollinger), Momentum (RSI, MACD, CCI), Volume (OBV, CMF), Volatility (ATR, IV), Options (PCR, OI change).
- **Meta-indicators:** e.g. `RSI(RSI(volume,14), 9)` — resolved by the indicator engine DAG.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/api/v1/auth/register` | Register |
| POST   | `/api/v1/auth/login`     | Login (JWT) |
| POST   | `/api/v1/scans/run`     | Run scan (body: ScanRequest) |
| POST   | `/api/v1/scans/validate`| Validate rule AST |
| GET    | `/api/v1/indicators/list` | Indicator library |
| GET    | `/api/v1/billing/plans`  | Subscription plans |
| POST   | `/api/v1/backtest/run`   | Run backtest (rule + date range → win rate, PnL, drawdown, Sharpe, expectancy) |
| GET    | `/health`                | Health check |

## UI/UX (mandate)

- Primary: white / off-white; secondary: soft blue / indigo
- Minimalist, Apple-style spacing, mobile-first, gesture-friendly
- Performance: &lt;150ms scan, &lt;300ms load, &lt;2s cold start

## Security & deployment

- HSM for production secrets; webhook signature validation (Razorpay/Stripe)
- Blue-green / canary; feature flags; A/B testing ready

## License

Proprietary — StrikeGenius.ai


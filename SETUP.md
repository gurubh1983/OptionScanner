# StrikeGenius.ai — Setup Instructions

End-to-end local run with no placeholders. All integrations are pluggable via config.

## Prerequisites

- Python 3.11+
- Node 20+
- PostgreSQL 14+ (optional: TimescaleDB extension)
- Redis (for Celery; optional for basic run)

## 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `DATABASE_URL` / `DATABASE_URL_SYNC`: PostgreSQL URL (default works if DB is local with user `strikegenius` / password `strikegenius` / DB `strikegenius`).
- `SECRET_KEY`: any long random string for JWT.
- `REDIS_URL`: for Celery (e.g. `redis://localhost:6379/0`).
- Optional: `BROKER_ADAPTER=angel_one|dhan|zerodha`, and set the corresponding `*_api_key` for live feeds.
- Optional: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` and/or Stripe keys for payments.

Create DB and run migrations:

```bash
# Create DB (if not exists):
# psql -c "CREATE USER strikegenius WITH PASSWORD 'strikegenius';"
# psql -c "CREATE DATABASE strikegenius OWNER strikegenius;"

alembic upgrade head
```

Start API:

```bash
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

(Optional) Start Celery worker:

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:3000  
- API is proxied to backend via Next.js rewrites (`/api/v1/*` → `http://localhost:8000/api/v1/*`).

## 3. Docker (full stack)

```bash
docker compose up -d
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:3000  
- PostgreSQL: 5432, Redis: 6379  

Then run migrations inside backend container:

```bash
docker compose exec backend alembic upgrade head
```

## 4. What runs without external services

- **No PostgreSQL**: API will fail on DB-dependent routes (auth, scans with user, billing). Use SQLite only if you add a separate SQLite adapter; by default the app expects PostgreSQL.
- **No Redis**: API and scanner work; Celery tasks (async scan, alerts) will not run unless Redis is up.
- **No broker keys**: Market data comes from TimescaleDB `candles` table; if empty, the TimescaleDB adapter returns **seed candles** so scans and indicators run.
- **No Razorpay/Stripe**: Plans still listed from DB; subscribe will return an error if gateway not configured.

## 5. Pluggable integrations

| Integration    | Config / Adapter              | Behavior when unset                    |
|----------------|-------------------------------|----------------------------------------|
| Broker feed    | `BROKER_ADAPTER`, `*_api_key` | TimescaleDB → seed candles             |
| Market data    | TimescaleDB `candles` table   | Seed candles per symbol/timeframe      |
| Payments       | Razorpay / Stripe keys        | Subscribe fails with error             |
| Auth           | DB `users` table              | Register/Login fully functional        |
| Subscriptions  | DB `plans`, `subscriptions`   | Limits enforced from DB                |

## 6. Key URLs

| Page / API              | URL                    |
|-------------------------|------------------------|
| Home                    | http://localhost:3000  |
| Scanner                 | /scanner               |
| No-code rule builder    | /builder               |
| Admin dashboard         | /admin                 |
| Pricing                 | /pricing               |
| Login / Register        | /login, /register      |
| OpenAPI                 | http://localhost:8000/docs |

## 7. Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests/ -v
```

## 8. TimescaleDB (optional)

For production time-series:

1. Install TimescaleDB and create extension in your PostgreSQL database.
2. After `alembic upgrade head`, run:
   ```sql
   SELECT create_hypertable('candles', 'ts', if_not_exists => TRUE);
   ```
3. Backfill `candles` from your broker or NSE; the adapter will use it instead of seed data.

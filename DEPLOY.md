# Deploy to production

## Production environment

1. Copy the production example and set real values:

   ```bash
   cp backend/.env.production.example backend/.env
   ```

2. Required variables:

   - `ENVIRONMENT=production`
   - `DATABASE_URL` — PostgreSQL (e.g. Neon: `postgresql+asyncpg://user:pass@host/db`)
   - `DATABASE_URL_SYNC` — same URL with `postgresql://` (for Alembic)
   - `JWT_SECRET` or `SECRET_KEY` — long random string
   - `CORS_ORIGINS` — comma-separated frontend URLs (e.g. `https://yourapp.vercel.app`)
   - `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` (and webhook secret) if using Razorpay

## Railway

- **Set Root Directory to `backend`** in the service settings so Railpack/Nixpacks builds only the Python app (avoids monorepo detection issues).
- **Backend only:** With root = `backend`, the `Procfile` runs:

  ```text
  web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
  ```

- **Monorepo (root = repo root):** Use the root `Procfile`:

  ```text
  web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

- In Railway dashboard, add env vars from `.env.production.example` (no need to commit `.env`).
- **If you see "Error creating build plan with Railpack"**: switch the service to use the **Dockerfile** builder so Railpack is skipped:
  1. In the service → **Settings** → **Build** (or **Deploy**), set **Builder** to **Dockerfile**.
  2. Set **Dockerfile path** to `Dockerfile` (or `backend/Dockerfile` if root is repo root).
  3. Set **Root Directory** to `backend` so the Dockerfile and `requirements.txt` are found.
  The repo’s `backend/Dockerfile` uses `requirements.txt` only (no ta-lib/pandas-ta) and listens on `$PORT`.

## CORS

CORS is driven by `CORS_ORIGINS`:

- If set: allowed origins = split by comma (e.g. `https://yourapp.vercel.app`).
- If empty: in debug mode allow `*`; otherwise allow `https://strikegenius.ai` only.

## Push to GitHub

From the project root:

```bash
git add backend/.env.production.example backend/Procfile Procfile backend/app/core/config.py backend/app/main.py DEPLOY.md
git commit -m "Production env example, Procfile for Railway, CORS from env"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git   # if not already set
git push -u origin main
```

Use your actual branch name if not `main`.

---

## "Application failed to respond" on Railway

1. **Deploy logs**  
   In Railway → your service → **Deployments** → latest deployment → **View logs**. Check for Python tracebacks or "Address already in use" / port errors.

2. **Env vars**  
   Ensure **DATABASE_URL** (and optionally **DATABASE_URL_SYNC**) are set. If the DB is unreachable, the app can crash on first request that uses the DB.

3. **Root URL**  
   The app serves `GET /` and `GET /health` with no DB. If those work in logs but the browser fails, the issue may be CORS or the URL you’re opening (try `https://your-app.up.railway.app/` and `https://your-app.up.railway.app/health`).

4. **Custom domain**  
   If you added a domain, ensure the service is running and the deployment succeeded (green).

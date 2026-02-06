# Backend audit and stabilization summary

## 1. Project audit (as of stabilization)

### Models (app.models)
| Model | Table | Status |
|-------|--------|--------|
| User | users | Active |
| Plan | plans | Active (billing) |
| Subscription | subscriptions | Active |
| Scan | scans | Active |
| ScanRule | scan_rules | Table created; API/repos disabled |
| TemplatePurchase | template_purchases | Table created; API disabled |
| TemplateRating | template_ratings | Table created; API disabled |

### Repositories
| Repo | Uses | Injected in deps |
|------|------|------------------|
| UserRepository | User | Yes |
| PlanRepository | Plan | Yes |
| SubscriptionRepository | Subscription | Yes |
| ScanRepository | Scan | Yes |
| ScanRuleRepository | ScanRule | No (templates stubbed) |
| TemplatePurchaseRepository | TemplatePurchase | No |
| TemplateRatingRepository | TemplateRating | No |

### Services
| Service | Deps | Injected |
|---------|------|----------|
| AuthService | UserRepository | Yes |
| SubscriptionService | PlanRepository, SubscriptionRepository | Yes |
| ScannerService | MarketDataService, SubscriptionService, ScanRepository | Yes |
| SimulateService | MarketDataService | Yes |
| BacktestService | MarketDataService | Yes (in backtest endpoint) |
| MarketplaceService | (multiple) | No (router excluded) |

### API endpoints (included)
- **auth:** POST /register, POST /login
- **scans:** POST /run, POST /validate, POST /simulate, GET /templates (→ []), POST /templates (→ 503)
- **indicators:** GET /list, GET /resolve
- **billing:** GET /plans, POST /subscribe, POST /webhook/razorpay, POST /webhook/stripe
- **admin:** GET /stats
- **backtest:** POST /run

### Excluded
- **templates_market** router (entire prefix /templates/market) not mounted.

---

## 2. Major changes applied

- **Single Base:** All models use `Base` from `app.db.session`. `app.db.base` re-exports `Base` and imports all models so that `import app.models` registers every table with `Base.metadata` before `create_all`.
- **Startup:** Lifespan in `main.py` imports `app.models`, then runs `Base.metadata.create_all()`. DB failures are logged; app still boots so `/health` and `/docs` work.
- **Dependency injection:** Added `get_plan_repo`; `get_subscription_service` now takes `plan_repo` and `sub_repo` (SubscriptionService constructor matches).
- **Templates:** `list_templates` returns `[]`; `save_template` returns 503. No `ScanRuleRepository` in scans endpoints.
- **Router:** Only auth, scans, indicators, billing, admin, backtest. No templates_market.
- **Scans endpoint:** Removed `ScanRuleRepository` and `get_db` from template handlers; no session needed for stubs.

---

## 3. How to re-enable advanced features

- **Templates (list/save):** In `deps.py` add `get_scan_rule_repo`. In `scans.py` inject it and restore `list_templates` / `save_template` logic using `ScanRuleRepository`.
- **Template marketplace:** In `deps.py` add marketplace-related repos and `get_marketplace_service`. In `router.py` include `templates_market.router` again.

---

## 4. Verify

With DB and env set:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- Open `/docs` — no import errors.
- POST `/api/v1/auth/register` with `{"email":"test@test.com","password":"secret"}` — 200 and JWT.
- POST `/api/v1/auth/login` — 200 and JWT.
- POST `/api/v1/scans/run` with a minimal `ScanRequest` (rule with timeframe + rules) — 200 (or 403 if limit reached when logged in).

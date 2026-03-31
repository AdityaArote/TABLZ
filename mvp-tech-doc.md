# TABLZ — MVP Technical Document
**What to build first, how to build it, and what "done" means**
**Phase 1 + Phase 2 · Weeks 1–8**

---

## What This Document Is

This is the engineering team's ground-level guide for the MVP: the minimum product that proves the core loop works (customer scans QR → orders food → chef receives it → bill is generated). Everything here is scoped to Phase 1 (Weeks 1–4) and Phase 2 (Weeks 5–8) of the TABLZ roadmap. Phase 3+ features are explicitly out of scope.

---

## MVP Scope

### In Scope (Weeks 1–8)

- Restaurant account registration + email verification
- Admin login with JWT auth
- Menu management (create, edit, toggle availability, soft-delete)
- Table management (create, assign QR codes)
- Customer QR scan → session creation → menu browse → order placement
- Chef dashboard order queue with real-time updates (WebSocket)
- Reception dashboard: view orders, update status, finalize bill, generate barcode
- Basic analytics: revenue summary, popular items (7-day rolling)
- Basic error handling and standard error response format
- Email verification flow

### Explicitly Out of Scope (MVP)

- Reservations (Phase 3)
- Table merging (Phase 3)
- Razorpay subscription billing (Phase 3) — MVP restaurants on Free tier
- AI briefings (Phase 4)
- Advanced analytics — peak hours, table turnaround, export (Phase 3–4)
- White-label / custom branding (Phase 4)
- Local (LAN) deployment (Phase 4)
- Staff PIN login (Phase 3)
- Webhooks for Luxury tier (Phase 3)
- DPDP data export/deletion endpoints (Phase 3)

---

## Tech Stack

| Component | Technology | Version / Notes |
|---|---|---|
| Backend | Python / FastAPI | 3.11+ / FastAPI 0.110+ |
| Database | PostgreSQL 15 | via Supabase (free tier for dev) |
| ORM | SQLAlchemy | 2.0 async |
| Migrations | Alembic | |
| Task Queue | Celery + Redis | For daily special resets in Phase 2 |
| Cache | Redis | Upstash for cloud, local Redis for dev |
| Frontend | Next.js 14 | App Router, TypeScript |
| Styling | Tailwind CSS | |
| Real-Time | FastAPI WebSockets | Native, no third-party library |
| Auth | python-jose (JWT) | HS256 algorithm |
| Password Hashing | bcrypt | passlib[bcrypt] |
| Validation | Pydantic v2 | |
| HTTP Client (Claude) | httpx | For AI briefing calls in Phase 4 |
| Email | SendGrid | Via sendgrid Python SDK |
| File Storage | AWS S3 | boto3 |
| QR Generation | qrcode | qrcode[pil] |
| Testing | pytest + pytest-asyncio | |
| E2E Testing | Playwright | |
| Security Scanning | OWASP ZAP + truffleHog | In CI |

---

## Repository Structure

```
tablz/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── deps.py                 # Dependency injection (get_current_restaurant, etc.)
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── restaurant.py
│   │   │   ├── table.py
│   │   │   ├── menu_item.py
│   │   │   ├── order.py
│   │   │   ├── order_item.py
│   │   │   ├── customer_session.py
│   │   │   └── audit_log.py
│   │   │
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── menu.py
│   │   │   ├── order.py
│   │   │   ├── table.py
│   │   │   └── common.py           # ErrorResponse, PaginatedResponse
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── auth_service.py
│   │   │   ├── menu_service.py
│   │   │   ├── order_service.py
│   │   │   ├── table_service.py
│   │   │   └── analytics_service.py
│   │   │
│   │   ├── routers/                # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── menu.py
│   │   │   ├── orders.py
│   │   │   ├── tables.py
│   │   │   ├── analytics.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── core/
│   │   │   ├── security.py         # JWT creation/validation, bcrypt helpers
│   │   │   ├── rate_limit.py       # Redis-backed rate limiting middleware
│   │   │   ├── websocket_manager.py # Room-based WS connection manager
│   │   │   └── errors.py           # Error codes + standard error response builder
│   │   │
│   │   └── celery/
│   │       ├── celery_app.py
│   │       └── tasks.py            # reset_daily_specials, etc.
│   │
│   ├── alembic/                    # DB migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── apps/
│   │   ├── reception/              # Next.js app — Reception dashboard
│   │   ├── customer/               # Next.js PWA — Customer ordering
│   │   └── chef/                   # Next.js app — Chef dashboard
│   └── packages/
│       └── ui/                     # Shared components
│
├── scripts/
│   ├── seed_test_data.py           # Creates 5 restaurants, 50 tables, 200 items, 1000 orders
│   └── generate_qr.py             # Standalone QR generation utility
│
├── docs/
│   └── runbooks/                   # Operational runbooks
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI pipeline
│
└── docker-compose.yml              # Local dev environment
```

---

## Database Setup (Phase 1)

Run migrations in this order. All tables created before any application code is written.

### Migration 001 — Core Tables

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- restaurants
CREATE TABLE restaurants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id VARCHAR(12) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    subscription_tier VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (subscription_tier IN ('free', 'premium', 'vip', 'luxury')),
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    password_hash TEXT NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- tables
CREATE TABLE tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id),
    table_number SMALLINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'available'
        CHECK (status IN ('available', 'occupied', 'merged', 'cleaning', 'reserved')),
    owner_session_id UUID,  -- FK added after customer_sessions table
    merged_into_table_id UUID REFERENCES tables(id),
    is_expandable BOOLEAN NOT NULL DEFAULT false,
    qr_code_token VARCHAR(128) UNIQUE NOT NULL,
    qr_code_url TEXT NOT NULL,
    max_capacity SMALLINT NOT NULL DEFAULT 4,
    last_cleaned_at TIMESTAMPTZ,
    UNIQUE (restaurant_id, table_number)
);

-- menu_items
CREATE TABLE menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL CHECK (price > 0),
    category VARCHAR(20) NOT NULL
        CHECK (category IN ('appetizer', 'main', 'dessert', 'beverage', 'side')),
    cuisine VARCHAR(100),
    dietary_type VARCHAR(30) NOT NULL
        CHECK (dietary_type IN ('vegetarian', 'non_vegetarian', 'vegan', 'contains_nuts')),
    is_daily_special BOOLEAN NOT NULL DEFAULT false,
    is_weekly_special BOOLEAN NOT NULL DEFAULT false,
    is_available BOOLEAN NOT NULL DEFAULT true,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMPTZ,
    image_url TEXT,
    prep_time_minutes SMALLINT NOT NULL DEFAULT 15
);

-- customer_sessions
CREATE TABLE customer_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL REFERENCES tables(id),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id),
    session_token VARCHAR(128) UNIQUE NOT NULL,
    is_table_owner BOOLEAN NOT NULL DEFAULT false,
    device_fingerprint VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    invalidated_at TIMESTAMPTZ
);

-- Add owner_session_id FK now that customer_sessions exists
ALTER TABLE tables
    ADD CONSTRAINT fk_owner_session
    FOREIGN KEY (owner_session_id) REFERENCES customer_sessions(id);

-- orders
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id UUID NOT NULL REFERENCES restaurants(id),
    table_id UUID NOT NULL REFERENCES tables(id),
    session_id UUID NOT NULL REFERENCES customer_sessions(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'received', 'preparing', 'ready', 'served', 'cancelled')),
    special_requests TEXT,
    total_amount NUMERIC(10,2) NOT NULL,
    tax_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    is_finalized BOOLEAN NOT NULL DEFAULT false,
    barcode_token VARCHAR(128) UNIQUE,
    placed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finalized_at TIMESTAMPTZ
);

-- order_items
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    menu_item_id UUID NOT NULL REFERENCES menu_items(id),
    quantity SMALLINT NOT NULL CHECK (quantity > 0),
    unit_price_at_order NUMERIC(10,2) NOT NULL,
    item_notes TEXT
);

-- audit_log
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    restaurant_id UUID REFERENCES restaurants(id),
    actor_type VARCHAR(20) NOT NULL
        CHECK (actor_type IN ('admin', 'staff', 'customer', 'system')),
    actor_id TEXT NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    ip_address INET,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX idx_menu_items_restaurant ON menu_items(restaurant_id) WHERE is_deleted = false;
CREATE INDEX idx_orders_restaurant_status ON orders(restaurant_id, status);
CREATE INDEX idx_orders_table ON orders(table_id);
CREATE INDEX idx_customer_sessions_token ON customer_sessions(session_token);
CREATE INDEX idx_audit_log_restaurant ON audit_log(restaurant_id, created_at DESC);
```

### Migration 002 — Row-Level Security

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_sessions ENABLE ROW LEVEL SECURITY;

-- RLS policies (application sets app.current_restaurant_id via SET LOCAL)
CREATE POLICY tables_isolation ON tables
    USING (restaurant_id = current_setting('app.current_restaurant_id', true)::uuid);

CREATE POLICY menu_items_isolation ON menu_items
    USING (restaurant_id = current_setting('app.current_restaurant_id', true)::uuid);

CREATE POLICY orders_isolation ON orders
    USING (restaurant_id = current_setting('app.current_restaurant_id', true)::uuid);

-- Create application DB user with limited privileges (not superuser)
CREATE USER tablz_app WITH PASSWORD 'your-strong-password';
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO tablz_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tablz_app;
-- Do NOT grant DELETE (soft deletes only) or TRUNCATE
```

---

## Phase 1 Implementation Guide (Weeks 1–4)

### Week 1 — Foundation

**Goal:** Auth works end-to-end. A restaurant can register, verify email, and log in.

**Tasks:**
1. Set up FastAPI app with lifespan events (DB connection pool init/teardown)
2. Implement `config.py` with pydantic-settings — all config from env vars, no hardcoding
3. Implement `database.py` with SQLAlchemy async engine
4. Run migrations (001, 002)
5. Implement `AuthService`:
   - `register_restaurant()` — generates `admin_id` (TBZ-YYXXXX format), bcrypt hash password, send verification email
   - `verify_email()` — time-limited token (24h), mark `email_verified = true`
   - `login()` — validate credentials, check `email_verified`, issue JWT + refresh token, write to audit_log
   - `refresh_token()` — validate refresh token, issue new access JWT, rotate refresh token
   - `logout()` — invalidate refresh token
6. Implement rate limiting middleware (Redis, 5 login attempts → 15-min lockout)
7. Implement standard error response format in `errors.py`
8. Write unit tests for AuthService (80% coverage gate)

**Definition of Done:**
- POST /api/v1/auth/register → 201, generates admin_id, sends verification email
- POST /api/v1/auth/verify-email/:token → 200, email_verified = true
- POST /api/v1/auth/login → 200, returns access token, sets refresh HttpOnly cookie
- POST /api/v1/auth/refresh → 200, new access token
- POST /api/v1/auth/logout → 200, refresh token invalidated
- 6th login attempt → 429 with `Retry-After: 900`
- All responses use standard error format

### Week 2 — Menu & Tables

**Goal:** Admin can build a menu and create tables with QR codes.

**Tasks:**
1. Implement `MenuService`:
   - CRUD with `restaurant_id` scoping
   - `is_deleted` soft-delete (never hard delete)
   - Input sanitization (bleach for description field)
   - `toggle_availability()` for quick on/off
2. Implement `TableService`:
   - Table creation with QR token generation (`secrets.token_urlsafe(96)` → 128 chars)
   - QR image generation (Python `qrcode` lib), upload to S3
   - QR URL construction: `{BASE_URL}/t/{token}`
3. Implement S3 upload helper (async with aioboto3)
4. Add menu and table router endpoints
5. Write integration tests for menu and table endpoints

**Definition of Done:**
- Full CRUD on /api/v1/menu (all endpoints return `restaurant_id`-scoped data)
- POST /api/v1/tables → creates table, generates QR token, uploads QR image to S3
- GET /api/v1/tables/:id/qr → returns QR image URL
- Soft delete: DELETE /api/v1/menu/:id sets is_deleted=true, item disappears from customer view
- OWASP ZAP scan: zero critical findings

### Week 3 — Customer Ordering

**Goal:** A customer can scan a QR, browse the menu, and place an order.

**Tasks:**
1. Implement customer session creation:
   - `POST /api/v1/auth/qr-session` — validates QR token, creates `customer_sessions` row, sets `is_table_owner` for first scanner, updates `tables.status = 'occupied'`
   - Issue session_token as HttpOnly cookie
2. Implement `OrderService`:
   - `create_order()` — idempotency key check (Redis, 24h TTL), snapshot `unit_price_at_order`, compute `total_amount`, write order + order_items
   - Validate `restaurant_id` on all items (prevent cross-restaurant item injection)
   - Write to `audit_log`
3. Order status transition enforcer — server-side state machine:
   ```
   pending → received → preparing → ready → served
   any state → cancelled (admin only)
   ```
   Invalid transitions return HTTP 409 `ORDER_INVALID_TRANSITION`
4. Customer-facing endpoints (authenticated via session token):
   - GET /api/v1/menu (filter: `is_available=true`, `is_deleted=false`)
   - POST /api/v1/orders
   - GET /api/v1/orders (scoped to table session)

**Definition of Done:**
- Full E2E Journey 1 passing: scan → order → status update → finalize (manual Playwright test)
- Idempotency: same `Idempotency-Key` on duplicate POST → returns original order, not duplicate
- Cross-restaurant item injection blocked (422 or 404)
- Order status transitions enforced server-side

### Week 4 — Chef Dashboard & WebSocket

**Goal:** Chef receives real-time order events and can update status.

**Tasks:**
1. Implement WebSocket manager (`websocket_manager.py`):
   - Room-based: `restaurant:{restaurant_id}`
   - Connection auth: validate JWT/session token on connect
   - Heartbeat: server pings every 30s, disconnect on 3 missed pings
   - Token refresh protocol: send `token_expiring_soon` at t-2min, handle `reauth` message
2. Wire `OrderService` to broadcast events after DB writes:
   - `order.created` on new order
   - `order.status_changed` on status update
3. Implement WS reconnect + fallback logic on Chef frontend
4. Implement Reception dashboard order view and status update
5. Implement bill finalization:
   - `POST /api/v1/orders/:id/finalize` — lock order, generate barcode token, upload barcode PDF to S3
6. E2E tests for Journey 1 (full order flow) in Playwright

**Phase 1 Definition of Done (All must pass):**
- E2E Journey 1 passing in CI (Playwright, not manual)
- 80% unit test coverage on AuthService + OrderService
- Zero critical findings from OWASP ZAP
- All API endpoints return standard error format
- WS token refresh working (automated test)

---

## Phase 2 Implementation Guide (Weeks 5–8)

### Week 5–6 — Table Management & Analytics

**Goal:** Full table lifecycle management and basic analytics dashboard.

**Tasks:**
1. Table status lifecycle: available → occupied → cleaning → available
2. Reception dashboard table map (grid view with status color coding)
3. Table cleaning flow: `POST /api/v1/tables/:id/clean` → sets `status = 'cleaning'`, then `last_cleaned_at` + `status = 'available'` when confirmed
4. Analytics endpoints:
   - `GET /api/v1/analytics/summary` — daily revenue, order count, avg order value (7-day rolling for Free tier)
   - `GET /api/v1/analytics/popular-items` — top 10 items by order count
   - `GET /api/v1/analytics/occupancy` — table occupancy rate
5. Celery setup + `reset_daily_specials` task (runs at midnight per restaurant timezone)

### Week 7–8 — Pilot Hardening

**Goal:** First pilot restaurant live. Production-ready stability.

**Tasks:**
1. Load test against staging (k6 scenario: 10 concurrent restaurants, 100 req/min, p95 < 500ms)
2. Backup restore drill on staging
3. Error monitoring setup (Sentry for backend error tracking)
4. HTTPS configuration, security headers (HSTS, CSP, X-Frame-Options)
5. PWA configuration for Customer dashboard (manifest, service worker for offline page)
6. E2E Journey 2 (Admin Onboarding) + Journey 3 placeholder tests

**Phase 2 Definition of Done (All must pass):**
- E2E Journeys 1–3 passing in CI
- WebSocket token refresh automated test passing
- Load test: 10 concurrent restaurants, 100 req/min, p95 < 500ms
- Backup restore test completed and documented
- First pilot restaurant successfully onboarded and transacting

---

## Environment Variables

All configuration via environment variables. Never hardcode. Never commit to git.

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/tablz
DATABASE_URL_SYNC=postgresql://user:password@host:5432/tablz  # for Alembic

# Security
JWT_SECRET_KEY=<256-bit-random>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_REGION=ap-south-1
S3_BUCKET_NAME=tablz-uploads-prod

# Email
SENDGRID_API_KEY=<key>
FROM_EMAIL=noreply@tablz.app

# App
BASE_URL=https://tablz.app
ENVIRONMENT=development  # development | staging | production

# Razorpay (Phase 3)
RAZORPAY_KEY_ID=<key>
RAZORPAY_KEY_SECRET=<secret>
RAZORPAY_MODE=test  # test | live

# Anthropic (Phase 4)
ANTHROPIC_API_KEY=<key>
```

---

## CI/CD Pipeline

`.github/workflows/ci.yml` — runs on every push and PR:

```yaml
jobs:
  test:
    steps:
      - truffleHog secret scan (fail on any secrets found)
      - pip install requirements
      - Run migrations against test DB (Postgres Docker service)
      - pytest --cov=app --cov-fail-under=80
      - Run OWASP ZAP baseline scan against local FastAPI instance
      - axe-core accessibility scan on frontend builds

  e2e:
    steps:
      - Build all Next.js apps
      - Start full stack (docker-compose)
      - Run Playwright E2E tests
      - Fail CI if any Journey 1 test fails

  deploy:
    needs: [test, e2e]
    if: push to main branch
    steps:
      - Deploy backend to Railway/Fly.io
      - Deploy frontends to Vercel
```

---

## Common Implementation Pitfalls

These are the most likely points of failure based on the PRD's security requirements.

**1. Never trust client-provided `restaurant_id` in write operations.**
Always extract `restaurant_id` from the validated JWT payload, not from the request body. The client can send any UUID — only the JWT claim is authoritative.

```python
# WRONG
async def create_menu_item(data: MenuItemCreate, restaurant_id: UUID = Body(...)):
    ...

# CORRECT
async def create_menu_item(
    data: MenuItemCreate,
    current_restaurant: Restaurant = Depends(get_current_restaurant)  # from JWT
):
    ...
```

**2. Set app.current_restaurant_id before every DB query.**
RLS only works if you set the session variable.

```python
async def get_db_with_rls(restaurant_id: UUID, db: AsyncSession):
    await db.execute(
        text("SET LOCAL app.current_restaurant_id = :id"),
        {"id": str(restaurant_id)}
    )
    return db
```

**3. Write to DB before broadcasting WebSocket events.**
If WS broadcast fails, the order still exists in DB. If you write to WS first and DB fails, the chef sees an order that doesn't exist — dangerous.

```python
# CORRECT order of operations
async def create_order(data: OrderCreate, ...) -> Order:
    order = await db.create(Order(...))    # 1. Write to DB
    await db.commit()                       # 2. Commit
    await ws_manager.broadcast(            # 3. Then broadcast
        room=f"restaurant:{order.restaurant_id}",
        event={"type": "order.created", "order": order.dict()}
    )
    return order
```

**4. Validate QR token lookups against restaurant_id.**
A customer could theoretically modify the QR token in a request to access a different restaurant's table. Always double-check:

```python
table = await db.get(Table, qr_token=token)
if table.restaurant_id != expected_restaurant_id:
    raise ResourceNotFoundError()  # Return 404, not 403 (don't confirm existence)
```

**5. Snapshot prices at order time.**
Do not store a reference to current price. Store the price at the moment of order:

```python
order_item = OrderItem(
    menu_item_id=item.id,
    quantity=item.quantity,
    unit_price_at_order=menu_item.price,  # Snapshot, not FK to current price
)
```

---

## Testing Checklist

Before merging any feature branch, verify:

- [ ] Unit tests pass with ≥ 80% coverage on modified service files
- [ ] Integration tests pass for all modified API endpoints
- [ ] All responses use standard error format (`success`, `error.code`, `error.message`, `error.request_id`)
- [ ] No secrets committed (truffleHog passes)
- [ ] OWASP ZAP scan: zero critical findings on new endpoints
- [ ] restaurant_id scoping verified: manually test that authenticated Restaurant A cannot access Restaurant B's resources
- [ ] Input validation: test with missing required fields (422), invalid types (422), SQL injection strings (sanitized, not 500)
- [ ] Rate limiting: verify lockout triggers on appropriate endpoints

---

## Definition of MVP Complete

MVP is complete when **all of the following are true**:

1. E2E Journey 1 (Full Order Flow) passes in CI
2. E2E Journey 2 (Admin Onboarding) passes in CI
3. 80% unit test coverage on AuthService, OrderService, MenuService, TableService
4. Zero critical findings from OWASP ZAP
5. All API endpoints return standard error format
6. Load test: 10 concurrent restaurants, 100 req/min, p95 < 500ms on staging
7. WebSocket token refresh works without disconnect (automated test)
8. At least one pilot restaurant has successfully placed and fulfilled 10 real orders
9. Backup restore test documented on staging

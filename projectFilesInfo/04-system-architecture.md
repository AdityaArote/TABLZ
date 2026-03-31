# 04 — System Architecture
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Architecture Overview

TABLZ is a multi-tenant SaaS platform organized into five distinct layers. Each layer has a single clear responsibility and communicates only with its adjacent layer.

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTS (Layer 1)                  │
│  Reception Dashboard  │  Customer PWA  │  Chef Dashboard│
│  (Next.js 14)         │  (Next.js PWA) │  (Next.js)     │
└───────────────────────┬────────────────┬────────────────┘
                        │ REST + WebSocket│
┌───────────────────────▼────────────────▼────────────────┐
│                  API GATEWAY (Layer 2)                  │
│           FastAPI — Routing, Auth, Rate Limiting        │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 SERVICE LAYER (Layer 3)                 │
│  OrderService │ MenuService │ TableService │ AuthService │
│  AnalyticsService │ BillingService │ NotificationService │
└───────────┬──────────────────────────────┬──────────────┘
            │                              │
┌───────────▼──────────┐    ┌─────────────▼──────────────┐
│   DATA LAYER (L4)    │    │  REAL-TIME BUS (L5)        │
│   PostgreSQL 15      │    │  WebSocket Manager         │
│   via Supabase + RLS │    │  Per-restaurant channels   │
└──────────────────────┘    └────────────────────────────┘
```

---

## 2. Layer Breakdown

### Layer 1 — Clients

Three browser-based apps. **No direct database access.** All communication via FastAPI backend.

| Dashboard | Framework | Users | Communication |
|-----------|-----------|-------|---------------|
| Reception | Next.js 14, React, Tailwind CSS | Admin/Manager | REST + WebSocket |
| Customer | Next.js PWA, React | Guests (QR scan) | REST + WebSocket |
| Chef | Next.js, React | Kitchen staff | WebSocket (primary) |

**Responsibilities:** Render UI, send REST calls, subscribe to WS channels, handle transparent token refresh.
**Non-responsibilities:** Business rule validation, direct DB queries, payment processing logic.

### Layer 2 — API Gateway

FastAPI single entry point for all client traffic.

- **Routing:** Directs requests to service handlers
- **Auth verification:** Validates JWT / session tokens on every request
- **Subscription enforcement:** Checks `subscription_tier` before tier-gated operations
- **Rate limiting:** Redis-backed per `restaurant_id` and IP
- **Validation:** Pydantic v2 schema validation → 422 on malformed input

### Layer 3 — Service Layer

| Service | Responsibilities |
|---------|-----------------|
| `AuthService` | JWT issuance/validation, session creation, password hashing, rate-limited login |
| `OrderService` | Order creation (idempotency), status transitions (state machine), bill finalization |
| `MenuService` | Menu CRUD, soft-delete, daily/weekly special resets, bulk CSV import |
| `TableService` | Table creation, QR token generation, merge logic, cleaning status |
| `AnalyticsService` | Aggregated metrics, AI briefing data collection |
| `BillingService` | Razorpay subscription management, webhook processing, dunning |
| `NotificationService` | Email (SendGrid), SMS (MSG91 Luxury), AI briefing delivery |

Services communicate via **direct Python method calls** — no inter-service HTTP.

### Layer 4 — Data Layer

PostgreSQL 15 hosted on **Supabase** (AWS ap-south-1 Mumbai).

- **RLS** on all tables with `restaurant_id` — second security perimeter
- **Soft deletes** on all user-facing entities
- **Immutable audit log** — written by DB triggers + application code
- Connection pool: SQLAlchemy async, `pool_size=20`, `max_overflow=10`, `pool_timeout=30s`

### Layer 5 — Real-Time Bus

FastAPI WebSocket manager with per-restaurant channel isolation (`restaurant:{id}`).

Event flow: Order placed → DB write → broadcast `order.created` → Chef/Customer/Reception receive → UI update.

Token refresh protocol: Server sends `token_expiring_soon` at t-2min → Client refreshes via REST → sends `reauth` on WS → no disconnect.

---

## 3. Multi-Tenancy Model

Data isolation enforced at **three levels**:

1. **Application:** All service methods scope by `restaurant_id` from JWT. Cross-restaurant returns `RESOURCE_NOT_FOUND` (not 403).
2. **Database:** PostgreSQL RLS policies on every tenant-scoped table.
3. **WebSocket:** Each restaurant subscribes only to its own channel namespace.

---

## 4. Authentication Architecture

### Admin Auth
- Credentials: `admin_id` (TBZ-YYXXXX) + password (bcrypt hash)
- Access JWT: 15-min TTL, stored in React memory (never localStorage)
- Refresh Token: 30-day TTL, HttpOnly + Secure + SameSite=Strict cookie, rotated on each use
- Rate limit: 5 failed attempts → 15-min lockout (Redis counter)

### Customer Session Auth
- No login. QR scan → server validates token → creates `customer_session` → session token (HttpOnly cookie)
- 4-hour TTL. First scanner = `is_table_owner`. Sessions invalidated on table reset.

### Staff Auth (Phase 3)
- Staff PIN (4–6 digits), bcrypt hashed in `staff` table
- Staff-scoped JWT with `role: chef | reception | manager`

---

## 5. Security Architecture

| Threat | Mitigation |
|--------|-----------|
| SQL injection | Parameterized queries via SQLAlchemy ORM + Pydantic validation |
| IDOR | All queries include `restaurant_id` scope + RLS as second perimeter |
| Credential theft | bcrypt passwords, tokens in HttpOnly cookies |
| Brute force | Redis rate limiting: 5 attempts → 15-min lockout |
| XSS | Sanitized HTML (Bleach) + Content-Security-Policy headers |
| CSRF | SameSite=Strict cookies + CSRF token on state-changing requests |
| Secrets exposure | Env vars only, truffleHog in CI |
| Token replay | Short JWT TTL (15 min), refresh token rotation |
| Data exfiltration via AI | Claude receives aggregated metrics only — no PII |

---

## 6. Supporting Infrastructure

### Task Queue — Celery + Redis

| Job | Schedule | Description |
|-----|----------|-------------|
| `reset_daily_specials` | Daily at midnight (restaurant TZ) | Resets `is_daily_special = false` |
| `reset_weekly_specials` | Weekly at week-start | Resets `is_weekly_special = false` |
| `generate_ai_briefing` | Daily at 7am UTC | Fetches metrics, calls Claude, stores briefing |
| `send_dunning_email` | Daily at 9am | Sends dunning emails based on overdue status |
| `expire_customer_sessions` | Every 15 minutes | Marks sessions past `expires_at` |

### Cache — Redis
- Rate limiting counters, session lookups, idempotency keys
- No PII in cache. All values are IDs, counters, or tokens. TTL-bound.

### File Storage — AWS S3 + CloudFront
- Menu images, barcode PDFs, QR images
- `ap-south-1` (Mumbai) for data residency compliance

---

## 7. Deployment Architecture

### Cloud (Primary)
```
Browser → Vercel (Next.js SSR) → FastAPI (Railway/Fly.io)
                                    ├── Supabase PostgreSQL (Mumbai)
                                    ├── Upstash Redis
                                    ├── Celery workers
                                    └── AWS S3 + CloudFront
```

### Local / LAN (Phase 4)
```
Restaurant LAN → Intel NUC (Docker Compose)
    - Next.js, FastAPI, PostgreSQL, Redis, Celery containers
    - No internet required for core features
    - Admin-triggered updates via Reception dashboard
```

### Environment Tiers

| Environment | Purpose | Razorpay Mode |
|-------------|---------|---------------|
| Development | Developer machines | Test |
| Staging | Integration + load testing | Test |
| Production | Live customers | Live |

---

## 8. Scalability Design

### Current Targets
- Phase 2: 10 restaurants, 100 req/min, p95 < 500ms
- Phase 4: 50 restaurants, 1,000 req/min, p95 < 500ms

### Scaling Levers

| Bottleneck | Solution |
|-----------|---------|
| API throughput | Horizontal scaling (stateless FastAPI) |
| DB read load | Read replicas via Supabase Pro |
| WS connections | Redis Pub/Sub for multi-instance broadcast |
| Task queue | Celery workers scaled independently |
| File delivery | CloudFront CDN |

---

## 9. External Integrations

| Service | Purpose | Data Sent | Auth Method |
|---------|---------|-----------|-------------|
| Razorpay | Subscription billing | Email, tier, amount | API key (server-side) |
| Anthropic Claude | AI briefings | Aggregated metrics, no PII | API key (server-side) |
| AWS S3 | File storage | Images, PDFs | IAM role |
| CloudFront | CDN | File keys | S3 integration |
| SendGrid | Email | Owner email | API key |
| MSG91 | SMS (Luxury) | Phone number | API key |
| Supabase | DB hosting | Application data | Service key |
| Upstash | Redis cloud | Counters, tokens | REST API key |

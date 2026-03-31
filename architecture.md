# TABLZ — Architecture Document
**AI-Powered Restaurant Management Platform**
**v2.0**

---

## Overview

TABLZ is a multi-tenant SaaS platform organized into five distinct layers. Each layer has a single, clear responsibility and communicates only with its adjacent layer. This separation ensures that security vulnerabilities, scaling bottlenecks, and deployment changes can be addressed in isolation without cascading effects.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTS (Layer 1)                  │
│                                                         │
│  Reception Dashboard  │  Customer PWA  │  Chef Dashboard│
│  (Next.js 14)         │  (Next.js PWA) │  (Next.js)     │
└───────────────────────┬────────────────┬────────────────┘
                        │ REST + WebSocket│
┌───────────────────────▼────────────────▼────────────────┐
│                  API GATEWAY (Layer 2)                  │
│           FastAPI — Routing, Auth, Rate Limiting        │
│           JWT verification, Subscription enforcement    │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                 SERVICE LAYER (Layer 3)                 │
│  OrderService │ MenuService │ TableService │ AuthService │
│  AnalyticsService │ BillingService │ NotificationService │
└───────────┬──────────────────────────────┬──────────────┘
            │                              │
┌───────────▼──────────┐    ┌─────────────▼──────────────┐
│   DATA LAYER (Layer 4)│    │  REAL-TIME BUS (Layer 5)   │
│   PostgreSQL 15       │    │  WebSocket Manager         │
│   via Supabase        │    │  (FastAPI WebSockets)      │
│   + Row-Level Security│    │  Per-restaurant channels   │
└──────────────────────┘    └────────────────────────────┘
```

---

## 2. Layer Breakdown

### Layer 1 — Clients

Three browser-based applications. **No direct database access.** All communication goes through the FastAPI backend via REST or WebSocket.

| Dashboard | Framework | Users | Primary Communication |
|---|---|---|---|
| Reception Dashboard | Next.js 14, React, Tailwind CSS | Restaurant admin/manager | REST + WebSocket |
| Customer Dashboard | Next.js PWA, React | Restaurant guests (via QR scan) | REST + WebSocket |
| Chef Dashboard | Next.js, React | Kitchen staff | WebSocket (order events) |

**Client responsibilities:**
- Render UI state
- Send REST API calls for CRUD operations
- Subscribe to WebSocket channels for real-time updates
- Handle token refresh transparently (HttpOnly cookie flow)

**Client non-responsibilities (explicitly out of scope):**
- Business rule validation (server-side only)
- Direct database queries
- Payment processing logic (delegated to Razorpay)

### Layer 2 — API Gateway

FastAPI application that is the **single entry point** for all client traffic.

Responsibilities:
- **Routing:** Directs requests to appropriate service handlers
- **Auth verification:** Validates JWT tokens and customer session tokens on every request
- **Subscription enforcement:** Checks `subscription_tier` before allowing tier-gated operations (e.g., blocking > 10 tables on Free tier)
- **Rate limiting:** Redis-backed rate limiting per `restaurant_id` and IP
- **Request validation:** Pydantic schema validation returns `VALIDATION_ERROR` 422 on malformed input

### Layer 3 — Service Layer

Domain-organized Python modules. All business logic lives here.

| Service | Responsibilities |
|---|---|
| `AuthService` | JWT issuance/validation, session creation, password hashing, email verification, rate-limited login |
| `OrderService` | Order creation (idempotency), status transitions (server-enforced), bill finalization, barcode generation |
| `MenuService` | Menu CRUD, soft-delete, daily/weekly special resets (via Celery), bulk CSV import |
| `TableService` | Table creation, QR token generation, merge logic, cleaning status tracking |
| `AnalyticsService` | Aggregated metrics computation, data collection for AI briefings |
| `BillingService` | Razorpay subscription management, webhook processing, dunning orchestration |
| `NotificationService` | Email via SendGrid, SMS via MSG91 (Luxury tier), AI briefing delivery |

Services communicate via direct Python method calls. No inter-service HTTP calls.

### Layer 4 — Data Layer

**PostgreSQL 15** hosted on Supabase (AWS ap-south-1 / Mumbai region).

Security model:
- **Row-Level Security (RLS)** enabled on all tables containing `restaurant_id`. A restaurant's API can only read/write its own rows, enforced at the DB level as a second perimeter.
- **Soft deletes** on all user-facing entities (`is_deleted`, `deleted_at`) — no hard deletes except on DPDP account erasure requests.
- **Immutable audit log** — `audit_log` table written by both DB triggers and application code. Cannot be deleted by application tier.

Connection pooling: SQLAlchemy async pool, `pool_size=20`, `max_overflow=10`, `pool_timeout=30s`.

### Layer 5 — Real-Time Bus

FastAPI WebSocket manager. Each restaurant gets its own isolated channel namespace (e.g., `restaurant:{restaurant_id}`).

Event flow:
1. Order placed → `OrderService` writes to DB → broadcasts `order.created` event to `restaurant:{id}` channel
2. Chef updates status → broadcasts `order.status_changed` event
3. Reception and Customer dashboards receive event and update UI

**Token refresh protocol:** Server sends `token_expiring_soon` 2 minutes before JWT expiry. Client refreshes via REST, sends `reauth` on WS channel. No disconnect required.

---

## 3. Supporting Infrastructure

### Task Queue — Celery + Redis

Scheduled and background jobs:

| Job | Schedule | Description |
|---|---|---|
| `reset_daily_specials` | Daily at midnight (restaurant timezone) | Sets `is_daily_special = false` for all items |
| `reset_weekly_specials` | Weekly at week-start | Sets `is_weekly_special = false` |
| `generate_ai_briefing` | Daily at 7am UTC | Fetches metrics, calls Claude API, stores briefing |
| `send_dunning_email` | Daily at 9am | Sends dunning emails based on `payment_overdue` status + day count |
| `expire_customer_sessions` | Every 15 minutes | Marks sessions as invalidated past `expires_at` |

### Cache — Redis (Upstash for cloud, local Redis for LAN deployment)

- Rate limiting counters (per restaurant_id + endpoint)
- Session state lookups
- **No PII stored in cache.** All values are IDs, counters, or tokens. TTL-bound.

### File Storage — AWS S3 + CloudFront CDN

- Menu item images uploaded by Reception dashboard
- Barcode PDFs generated on bill finalization
- All stored in `ap-south-1` (Mumbai) bucket for data residency compliance
- CloudFront CDN for image delivery to Customer PWA (low latency menu browsing)

### QR Engine

- Table QR codes contain a cryptographically secure random token (128 chars, stored as `qr_code_token` in `tables` table)
- QR scan URL format: `https://tablz.app/t/{qr_code_token}`
- Token validated server-side; creates a `customer_session` row with `is_table_owner = true` for first scanner
- QR tokens can be regenerated (Reception dashboard) — invalidates all existing sessions for that table

---

## 4. Multi-Tenancy Model

TABLZ is a hard multi-tenant SaaS. Restaurant data isolation is enforced at **three levels**:

1. **Application level:** All service methods accept and scope by `restaurant_id` extracted from the authenticated JWT or session token. Cross-restaurant ID manipulation returns `RESOURCE_NOT_FOUND` (not a 403, to avoid confirming resource existence).
2. **Database level:** PostgreSQL RLS policies on every tenant-scoped table. Even if the application layer has a bug, the DB will refuse cross-tenant reads/writes.
3. **WebSocket level:** Each restaurant is subscribed only to its own channel namespace. No cross-restaurant event leakage.

---

## 5. Authentication & Authorization

### Admin (Restaurant Owner) Authentication

- Credentials: `admin_id` (e.g., `TBZ-240001`) + password
- Password stored as bcrypt hash, never plaintext
- On login: issues short-lived **access JWT** (15-min TTL) + long-lived **refresh token** (HttpOnly cookie, 30-day TTL)
- JWT contains: `restaurant_id`, `admin_id`, `subscription_tier`, `iat`, `exp`
- Failed login: rate-limited at 5 attempts → 15-minute lockout (enforced via Redis counter)

### Customer Session Authentication

- No login required. Customer scans QR → server validates QR token → creates `customer_session` row → issues session token (HttpOnly cookie)
- Session token expires in 4 hours
- First scanner at a table becomes `is_table_owner = true` — has merge privileges
- Sessions are invalidated on table reset by Reception

### Staff Authentication (Phase 3)

- Staff PIN (4–6 digits), stored as bcrypt hash in `staff` table
- Issues a staff-scoped JWT with `role: chef | reception | manager`
- Staff JWTs cannot access admin-only endpoints (subscription management, analytics export)

---

## 6. Security Architecture

### Threat Model Coverage

| Threat | Mitigation |
|---|---|
| SQL injection | Parameterized queries via SQLAlchemy ORM. Pydantic validation on all inputs. |
| IDOR (Insecure Direct Object Reference) | All DB queries include `restaurant_id` scope. RLS as second perimeter. |
| Credential theft | Passwords are bcrypt-hashed. Tokens in HttpOnly cookies (not localStorage). |
| Brute force login | Redis-backed rate limiting: 5 attempts → 15-min lockout per `admin_id`. |
| XSS | Sanitized HTML on all user-generated text fields (description, special_requests). Content-Security-Policy headers. |
| CSRF | SameSite=Strict cookies. CSRF token on state-changing requests from browser. |
| Secrets exposure | Razorpay keys, DB credentials, API keys stored in environment variables. truffleHog in CI to detect accidental secret commits. |
| Token replay | Short JWT TTL (15 min). Refresh token rotation on each use. |
| Data exfiltration via AI | Claude API receives only aggregated, anonymized metrics — no PII, no individual records. |

### Audit Trail

Every security-sensitive action is written to the `audit_log` table:
- All login attempts (success + failure)
- All admin actions on menu, tables, billing
- All DPDP data export/deletion requests
- All subscription changes

Audit log is immutable from the application tier. Retention: 90 days minimum, 1 year for security events.

---

## 7. Deployment Architecture

### Cloud Deployment (Primary)

```
User Browser
     │
     ▼
Vercel CDN (Next.js dashboards — static + SSR)
     │
     ▼
FastAPI on Railway / Fly.io / AWS ECS (auto-scaled)
     │
     ├── Supabase PostgreSQL (AWS ap-south-1)
     ├── Upstash Redis (rate limiting + cache)
     ├── Celery workers (Railway / Fly.io)
     └── AWS S3 + CloudFront (file storage)
```

### Local (LAN) Deployment (Phase 4)

```
Restaurant LAN
     │
     ▼
Intel NUC (mini-PC on LAN)
Docker Compose bundle:
  - Next.js container (all 3 dashboards)
  - FastAPI container
  - PostgreSQL container
  - Redis container
  - Celery container
     │
     ▼
Devices connect via LAN IP (no internet required)
Updates: admin triggers pull via Reception dashboard
Backup: cron at 2am → compressed dump to USB/NAS
```

### Environment Tiers

| Environment | Purpose | DB | Razorpay Mode |
|---|---|---|---|
| Development (local) | Developer machines | Local Postgres / Supabase dev project | Test mode |
| Staging | Integration + load testing | Supabase staging project | Test mode |
| Production | Live customers | Supabase production project | Live mode |

---

## 8. Scalability Design

### Current Sizing Targets

- Phase 2: 10 concurrent restaurants, 100 req/min, p95 < 500ms
- Phase 4: 50 concurrent restaurants, 1,000 req/min, p95 < 500ms

### Scaling Levers

| Bottleneck | Solution |
|---|---|
| API throughput | Horizontal scaling of FastAPI instances (stateless, scales linearly) |
| DB read load | Read replicas via Supabase (available on Pro tier) |
| WebSocket connection count | FastAPI WebSocket manager can be moved to Redis Pub/Sub for multi-instance broadcast |
| Task queue | Celery workers scaled independently of API servers |
| File delivery | CloudFront CDN absorbs menu image load |

---

## 9. External Integrations

| Service | Purpose | Data Sent | Auth Method |
|---|---|---|---|
| Razorpay | Subscription billing | Email, subscription tier, amount | API key (server-side only) |
| Anthropic Claude API (claude-haiku-3) | AI briefings | Aggregated metrics only, no PII | API key (server-side only) |
| AWS S3 | File storage | Menu images, barcode PDFs | IAM role |
| CloudFront | CDN for file delivery | File keys | S3 integration |
| SendGrid | Transactional email | Owner email address | API key |
| MSG91 | SMS (Luxury tier) | Phone number | API key |
| Supabase | Database hosting + auth | All application data | Service key (server-side only) |
| Upstash | Redis (cloud) | Session state, rate limit counters | REST API key |

---

## 10. Key Architectural Decisions & Rationale

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI | Async-native, Pydantic validation built-in, excellent WebSocket support, Python ecosystem for AI/ML integrations |
| Database | PostgreSQL via Supabase | RLS for multi-tenancy, PITR for backup, managed hosting reduces ops burden for solo founder |
| Frontend | Next.js (all three dashboards) | Single framework for all dashboards reduces context switching; SSR for Customer PWA SEO; App Router for efficient code splitting |
| Real-time | WebSocket (not polling) | Sub-300ms kitchen display updates required; polling would create unacceptable UX for chef queue |
| Auth storage | HttpOnly cookies (not localStorage) | Eliminates XSS token theft. SameSite=Strict prevents CSRF. Standard security best practice. |
| AI model | claude-haiku-3 | Best cost/quality ratio for structured analytics briefing. ~₹0.20/briefing vs ₹2.00+ for larger models. |
| Payment gateway | Razorpay | India-first, UPI support, strong webhook reliability, lowest MDR for INR. Stripe/PayPal not viable for India market. |
| Soft deletes | is_deleted flag | Supports DPDP right-to-erasure workflow; prevents accidental data loss; enables downgrade data preservation policy |

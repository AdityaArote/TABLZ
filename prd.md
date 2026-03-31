# TABLZ — Product Requirements Document
**AI-Powered Restaurant Management Platform**
**v2.0 · PRODUCTION READY**

| Field | Value |
|---|---|
| Document Owner | Aditya (Founder) |
| Status | Ready for Development |
| Version | 2.0.0 |
| Target Audience | Engineering, Design, QA, Investors |
| Classification | Confidential |

---

## Changelog: v1.0 → v2.0

v1.0 was a strong architectural draft but was not production-ready. v2.0 adds: testing strategy, error handling & recovery specs, payment gateway decision, data privacy/retention policy, disaster recovery SLAs, subscription lifecycle, AI briefings spec, accessibility requirements, missing DB tables/columns, and missing API endpoints.

| Section | Change | Severity |
|---|---|---|
| New §12 | Testing Strategy (unit, integration, E2E, load) | Critical |
| New §13 | Error Handling & Recovery Specification | Critical |
| §11 resolved | Payment gateway decision: Razorpay (primary) | Critical |
| New §14 | Data Privacy, Retention & DPDP Compliance | Critical |
| New §15 | Disaster Recovery & Backup SLA | Critical |
| New §16 | Subscription Lifecycle (upgrade/downgrade/dunning) | Major |
| New §17 | AI Briefings Full Specification | Major |
| New §18 | Accessibility (WCAG 2.1 AA) Requirements | Major |
| §3 | Added audit_log, tax_configurations tables; is_deleted to menu_items; staff table | Major |
| §5 | Added 8 missing API endpoints; WebSocket token refresh; webhook spec | Major |
| §10 | Added technical definition-of-done gates per milestone | Minor |

---

## 1. Executive Summary

TABLZ is a subscription-based, AI-powered restaurant management SaaS platform that unifies the ordering experience across three synchronized dashboards: **Reception**, **Customer**, and **Chef**. Designed specifically for independent restaurants and small chains that currently operate on fragmented tools — separate POS systems, paper menus, and manual kitchen ticketing.

> **Core Value Proposition:** Replace 4–6 disconnected tools (POS, menu app, reservation system, kitchen display, analytics dashboard, billing) with a single unified platform. Reduce order errors by 40–60%, cut table turn time by 15–20 minutes, and provide daily AI-driven insights that independent restaurant owners cannot currently access at any price point.

### 1.1 Problem Statement

- Independent restaurants rely on 4–6 disconnected tools, leading to data silos and operational errors
- No single affordable platform combines customer-facing ordering with kitchen management and owner analytics
- Manual order-taking creates 8–12% error rates and delays table turns
- Restaurant owners have no real-time visibility into profitability, waste, or table utilization
- Existing solutions (Toast, Square, Lightspeed) are POS-first and cost ₹25,000–65,000/month

### 1.2 Solution

- Unified 3-dashboard platform accessible via single admin credential
- QR-based customer ordering — no app install required (PWA)
- Real-time order routing from customer table to chef kitchen display
- Owner intelligence layer: daily AI briefings, menu engineering, cost analytics
- Flat-fee subscription model starting at free tier for pilot acquisition

### 1.3 Target Market

| Segment | Description | Pain Intensity |
|---|---|---|
| Primary | Independent restaurants (1–3 locations) | Very High — no dedicated tech team |
| Secondary | Small chains (4–15 locations) | High — fragmented tools per location |
| Tertiary | Ghost kitchens, cloud kitchens | Medium — need kitchen-side tooling |

---

## 2. Product Architecture Overview

### 2.1 Platform Components

| Component | Tech Stack | Primary Responsibility |
|---|---|---|
| Reception Dashboard | Next.js 14, React, Tailwind CSS | Menu, tables, billing, analytics |
| Customer Dashboard | Next.js PWA, React | QR-based ordering, payment |
| Chef Dashboard | Next.js, React, WebSocket client | Order queue, status management |
| Backend API | Python / FastAPI | Business logic, auth, data layer |
| Database Layer | PostgreSQL 15 via Supabase | Persistent storage, RLS policies |
| Real-Time Layer | WebSocket (FastAPI) | Live sync across all dashboards |
| QR Engine | Python qrcode lib / AWS Lambda | Unique QR generation per table |
| Task Queue | Celery + Redis | Scheduled jobs, email, specials reset |
| Cache / Rate Limit | Redis (Upstash for cloud) | Session state, rate limiting |
| File Storage | AWS S3 + CloudFront CDN | Menu images, barcode PDFs |

### 2.2 Layered Architecture

- **Layer 1 — Client:** Three browser-based dashboards communicate via REST and WebSocket to the Backend API only. No direct DB access from clients.
- **Layer 2 — API Gateway:** FastAPI handles routing, auth verification, rate limiting, and subscription tier enforcement.
- **Layer 3 — Service Layer:** Domain-specific services (OrderService, MenuService, TableService, AnalyticsService, AuthService, BillingService, NotificationService) contain all business logic.
- **Layer 4 — Data Layer:** PostgreSQL with RLS enforced at DB level as second security perimeter.
- **Layer 5 — Real-Time Bus:** WebSocket manager broadcasts events to subscribed clients. Each restaurant operates in its own isolated channel namespace.

### 2.3 Deployment Models

| Dimension | Cloud Deployment | Local (LAN) Deployment |
|---|---|---|
| Hosting | AWS / GCP / Vercel (managed) | On-premise server / Intel NUC |
| Internet Required | Yes — always-on | No — operates fully on local network |
| Latency | 50–150ms typical | <5ms LAN latency |
| Setup Cost | None — SaaS model | Hardware cost (~₹17,000–35,000 one-time) |
| Data Sovereignty | Data on cloud servers | All data stays on-premise |
| Backup | Automatic cloud backup (daily, 30-day retention) | Scheduled local backup via cron |
| Software Updates | Automatic via CI/CD | Admin-triggered pull from update server |
| Best For | Most restaurants — simplest setup | Restaurants with poor/no internet |

> **Local Deployment Packaging (Phase 4):** Ships as a Docker Compose bundle with a setup wizard script. The restaurant admin connects a dedicated mini-PC to their LAN router. Initial setup: run `install.sh`, set admin credentials, scan QR to verify. Updates: admin clicks 'Check for Updates' in Reception dashboard — system pulls latest Docker images and restarts services with zero-downtime rolling restart.

---

## 3. Database Schema

> **v2.0 Changes:** Added `audit_log` table, `tax_configurations` table, `staff` table, `is_deleted` column to `menu_items`. These were missing in v1.0 but referenced in feature specs.

### 3.1 Core Tables

#### 3.1.1 restaurants

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| admin_id | VARCHAR(12) | UNIQUE, NOT NULL | Auto-generated (e.g. TBZ-240001) |
| name | VARCHAR(255) | NOT NULL | Restaurant display name |
| subscription_tier | ENUM | NOT NULL | free / premium / vip / luxury |
| timezone | VARCHAR(50) | NOT NULL | For analytics date bucketing |
| currency | CHAR(3) | NOT NULL | ISO currency code (INR, USD) |
| password_hash | TEXT | NOT NULL | bcrypt hash, never plaintext |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Owner email for notifications |
| email_verified | BOOLEAN | DEFAULT false | Email verification gate |
| is_active | BOOLEAN | DEFAULT true | Soft-disable on subscription lapse |
| created_at | TIMESTAMPTZ | NOT NULL | Account creation timestamp |

#### 3.1.2 tables

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants | Owner restaurant |
| table_number | SMALLINT | NOT NULL | Human-readable table number |
| status | ENUM | NOT NULL | available / occupied / merged / cleaning / reserved |
| owner_session_id | UUID | NULLABLE | FK → customer_sessions; first scanner is owner |
| merged_into_table_id | UUID | NULLABLE | FK → tables; self-reference for merges |
| is_expandable | BOOLEAN | DEFAULT false | Can physically extend |
| qr_code_token | VARCHAR(128) | UNIQUE, NOT NULL | Cryptographically secure token |
| qr_code_url | TEXT | NOT NULL | Full QR scan target URL |
| max_capacity | SMALLINT | NOT NULL | Max seated guests |
| last_cleaned_at | TIMESTAMPTZ | NULLABLE | For cleaning status tracking |

#### 3.1.3 menu_items

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| restaurant_id | UUID | FK, NOT NULL | Row-Level Security key |
| name | VARCHAR(255) | NOT NULL | Dish name |
| description | TEXT | | Sanitized HTML description |
| price | NUMERIC(10,2) | NOT NULL, > 0 | Base price in restaurant currency |
| category | ENUM | NOT NULL | appetizer / main / dessert / beverage / side |
| cuisine | VARCHAR(100) | | Italian, North Indian, Chinese, etc. |
| dietary_type | ENUM | NOT NULL | vegetarian / non_vegetarian / vegan / contains_nuts |
| is_daily_special | BOOLEAN | DEFAULT false | Auto-reset daily at midnight |
| is_weekly_special | BOOLEAN | DEFAULT false | Auto-reset weekly at week-start |
| is_available | BOOLEAN | DEFAULT true | Toggle without deletion |
| is_deleted | BOOLEAN | DEFAULT false | [v2.0 ADDED] Soft-delete flag |
| deleted_at | TIMESTAMPTZ | NULLABLE | [v2.0 ADDED] When soft-deleted |
| image_url | TEXT | NULLABLE | CDN URL for dish photo |
| prep_time_minutes | SMALLINT | DEFAULT 15 | Estimated preparation time |

#### 3.1.4 orders

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| restaurant_id | UUID | FK, NOT NULL | RLS enforcement |
| table_id | UUID | FK → tables | Physical table (may be merged parent) |
| session_id | UUID | FK → customer_sessions | Customer placing the order |
| status | ENUM | NOT NULL | pending / received / preparing / ready / served / cancelled |
| special_requests | TEXT | NULLABLE | Free-text — sanitized on input |
| total_amount | NUMERIC(10,2) | NOT NULL | Computed sum at time of order |
| tax_config_id | UUID | FK → tax_configurations | [v2.0 ADDED] Tax config snapshot |
| tax_amount | NUMERIC(10,2) | NOT NULL, DEFAULT 0 | [v2.0 ADDED] Computed tax at finalization |
| is_finalized | BOOLEAN | DEFAULT false | Locks order for billing |
| barcode_token | VARCHAR(128) | NULLABLE, UNIQUE | Generated on bill finalization |
| placed_at | TIMESTAMPTZ | NOT NULL | Order placement timestamp |
| finalized_at | TIMESTAMPTZ | NULLABLE | Bill finalization timestamp |

#### 3.1.5 order_items

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| order_id | UUID | FK → orders | Parent order |
| menu_item_id | UUID | FK → menu_items | Ordered dish |
| quantity | SMALLINT | NOT NULL, > 0 | |
| unit_price_at_order | NUMERIC(10,2) | NOT NULL | Snapshot — protects against price changes |
| item_notes | TEXT | NULLABLE | e.g. no onion, extra spice |

#### 3.1.6 customer_sessions

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| table_id | UUID | FK → tables | |
| restaurant_id | UUID | FK, NOT NULL | |
| session_token | VARCHAR(128) | UNIQUE, NOT NULL | Secure random token — HttpOnly cookie |
| is_table_owner | BOOLEAN | DEFAULT false | First scanner becomes owner |
| device_fingerprint | VARCHAR(64) | NULLABLE | Anti-abuse device identifier |
| created_at | TIMESTAMPTZ | NOT NULL | |
| expires_at | TIMESTAMPTZ | NOT NULL | Sessions expire after 4 hours |
| invalidated_at | TIMESTAMPTZ | NULLABLE | Explicitly revoked on table reset |

#### 3.1.7 reservations

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| restaurant_id | UUID | FK | |
| table_id | UUID | FK → tables, NULLABLE | Null if any-table preference |
| guest_name | VARCHAR(255) | NOT NULL | |
| guest_phone | VARCHAR(20) | NOT NULL | E.164 format enforced |
| party_size | SMALLINT | NOT NULL, > 0 | |
| reserved_at | TIMESTAMPTZ | NOT NULL | Requested booking datetime |
| status | ENUM | NOT NULL | pending / confirmed / seated / no_show / cancelled |
| notes | TEXT | NULLABLE | Special requests, dietary notes |

#### 3.1.8 tax_configurations [NEW in v2.0]

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| restaurant_id | UUID | FK, NOT NULL | Owner restaurant |
| name | VARCHAR(100) | NOT NULL | e.g. GST, Service Charge, VAT |
| rate_percent | NUMERIC(5,2) | NOT NULL, >= 0 | e.g. 18.00 for 18% GST |
| applies_to | ENUM | NOT NULL | all / food_only / beverages_only |
| is_active | BOOLEAN | DEFAULT true | Toggle without deletion |
| created_at | TIMESTAMPTZ | NOT NULL | |

#### 3.1.9 staff [NEW in v2.0]

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | UUID | PK | |
| restaurant_id | UUID | FK, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | Staff display name |
| role | ENUM | NOT NULL | chef / reception / manager |
| pin_hash | TEXT | NOT NULL | bcrypt hash of 4-6 digit PIN |
| is_active | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| last_login_at | TIMESTAMPTZ | NULLABLE | |

#### 3.1.10 audit_log [NEW in v2.0]

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | BIGSERIAL | PK | High-volume — use integer not UUID |
| restaurant_id | UUID | NULLABLE, FK | Null for system-level events |
| actor_type | ENUM | NOT NULL | admin / staff / customer / system |
| actor_id | TEXT | NOT NULL | admin_id, staff_id, session_id, or system |
| action | VARCHAR(100) | NOT NULL | e.g. order.created, menu.deleted, login.failed |
| resource_type | VARCHAR(50) | NULLABLE | e.g. order, menu_item, table |
| resource_id | UUID | NULLABLE | ID of affected resource |
| ip_address | INET | NULLABLE | Request IP |
| metadata | JSONB | NULLABLE | Additional context (sanitized, no PII) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### 3.2 Subscription Tiers

| Feature | Free | Premium | VIP | Luxury |
|---|---|---|---|---|
| Max Tables | 10 | 30 | 75 | Unlimited |
| Max Menu Items | 50 | 200 | 500 | Unlimited |
| Analytics Depth | 7 days | 90 days | 1 year | Unlimited + export |
| API Access | No | Read-only | Full | Full + webhooks |
| Custom Branding | No | No | Logo only | Full white-label |
| Reservations | No | Yes | Yes | Yes + SMS confirm |
| AI Briefings | No | Weekly | Daily | Real-time |
| Table Merging | No | Yes (3 max) | Yes (5 max) | Yes (unlimited) |
| Priority Support | Email only | Email + chat | Phone + SLA | Dedicated CSM |
| Monthly Price | ₹0 | ₹2,499 | ₹5,999 | ₹14,999 |

---

## 5. API Specification (v2.0 — Updated)

> **v2.0 Additions:** Added 8 missing endpoints, WebSocket token refresh protocol, webhook spec for Luxury tier, and `PATCH /menu/:id/availability` endpoint.

### 5.1 Complete Endpoint Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/v1/auth/register | None | Create restaurant account |
| POST | /api/v1/auth/login | None | Admin login, issue JWT |
| POST | /api/v1/auth/refresh | Refresh token (HttpOnly cookie) | Refresh access token |
| POST | /api/v1/auth/qr-session | QR token | Create customer session from QR scan |
| POST | /api/v1/auth/logout | JWT | Invalidate session |
| POST | /api/v1/auth/verify-email/:token | None | Verify email address |
| POST | /api/v1/auth/forgot-password | None | Request password reset email |
| POST | /api/v1/auth/reset-password | Reset token | Set new password |
| GET | /api/v1/menu | JWT or Session | List menu items (filterable) |
| POST | /api/v1/menu | JWT (Reception) | Create menu item |
| PUT | /api/v1/menu/:id | JWT (Reception) | Update menu item |
| PATCH | /api/v1/menu/:id/availability | JWT (Reception) | [v2.0 ADDED] Toggle is_available |
| DELETE | /api/v1/menu/:id | JWT (Reception) | Soft-delete menu item |
| POST | /api/v1/menu/bulk-import | JWT (Reception, VIP+) | [v2.0 ADDED] CSV bulk import |
| GET | /api/v1/tables | JWT (Reception/Chef) | List all tables with status |
| POST | /api/v1/tables | JWT (Reception) | Create table |
| POST | /api/v1/tables/:id/merge | Customer session (owner) | Merge tables |
| POST | /api/v1/tables/:id/clean | JWT (Reception) | Mark table as cleaned |
| GET | /api/v1/tables/:id/qr | JWT (Reception) | Get/regenerate QR code |
| POST | /api/v1/orders | Customer session | Place order (accepts idempotency_key header) |
| GET | /api/v1/orders | JWT or Session | List orders for table/restaurant |
| PATCH | /api/v1/orders/:id/status | JWT (Chef/Reception) | Update order status |
| POST | /api/v1/orders/:id/finalize | JWT (Reception) | Finalize bill, generate barcode |
| GET | /api/v1/reservations | JWT (Reception) | List reservations |
| POST | /api/v1/reservations | JWT (Reception) | Create reservation |
| PATCH | /api/v1/reservations/:id | JWT (Reception) | Update reservation |
| GET | /api/v1/analytics/summary | JWT (Reception) | Revenue summary |
| GET | /api/v1/analytics/popular-items | JWT (Reception) | Top selling items |
| GET | /api/v1/analytics/occupancy | JWT (Reception) | Table occupancy metrics |
| GET | /api/v1/analytics/peak-hours | JWT (Reception, VIP+) | [v2.0 ADDED] Peak hours heatmap |
| GET | /api/v1/analytics/table-turnaround | JWT (Reception, VIP+) | [v2.0 ADDED] Avg clean-to-reseat time |
| GET | /api/v1/analytics/export | JWT (Reception, Luxury) | [v2.0 ADDED] Export CSV/PDF report |
| GET | /api/v1/account/data-export | JWT (Reception) | [v2.0 ADDED] DPDP data export |
| DELETE | /api/v1/account | JWT (Reception) | [v2.0 ADDED] Account deletion (DPDP) |
| POST | /api/v1/webhooks/razorpay | Razorpay signature | [v2.0 ADDED] Payment webhook handler |
| GET | /api/v1/webhooks | JWT (Reception, Luxury) | [v2.0 ADDED] List webhook endpoints |
| POST | /api/v1/webhooks | JWT (Reception, Luxury) | [v2.0 ADDED] Register webhook URL |
| GET | /api/v1/ai/briefing | JWT (Reception, Premium+) | [v2.0 ADDED] Latest AI briefing |
| GET | /api/v1/tax-configs | JWT (Reception) | [v2.0 ADDED] List tax configurations |
| POST | /api/v1/tax-configs | JWT (Reception) | [v2.0 ADDED] Create tax config |

### 5.2 WebSocket Token Refresh Protocol [NEW in v2.0]

Access tokens expire in 15 minutes. Protocol for WS sessions spanning multiple refresh cycles:

1. Server sends `token_expiring_soon` event 2 minutes before expiry: `{ type: 'token_expiring_soon', expires_in_seconds: 120 }`
2. Client calls `POST /api/v1/auth/refresh` (uses HttpOnly refresh token cookie). Receives new `access_token`.
3. Client sends a `reauth` message on WS channel: `{ type: 'reauth', token: '<new_access_token>' }`
4. Server validates new token, updates session. WS connection remains open — no disconnect.
5. If client fails to reauth within the window: server sends `session_expired` event and closes WS connection gracefully (code 4001). Client reconnects with new token.

---

## 10. Development Milestones (v2.0 — Updated)

Each phase gate includes technical DoD criteria. Engineering team must certify all criteria before phase is considered complete.

| Phase | Duration | Deliverables | Technical Gate (DoD) |
|---|---|---|---|
| Phase 0 — Pre-code | Now | 20 restaurant owner interviews, validated problem statement, 3 signed LOIs from pilot restaurants. Payment gateway sandbox configured. Supabase project provisioned. | Razorpay sandbox keys working. DB schema v2.0 reviewed and approved. All §11 open questions resolved. |
| Phase 1 — Core Flow | Weeks 1–4 | Auth service, DB schema, basic Reception + Customer dashboard (menu browse + order placement → Chef queue). Email verification. Basic error handling. | E2E Journey 1 passing in CI. 80% unit test coverage on Auth and Order services. Zero critical security findings from OWASP ZAP scan. All API endpoints return standard error format. |
| Phase 2 — Operational | Weeks 5–8 | Table management, QR system, billing with barcode, basic analytics, real-time WebSocket, first pilot restaurant live. | E2E Journeys 1–3 passing. WebSocket token refresh working. Load test: 10 concurrent restaurants at 100 req/min with p95 < 500ms. Backup restore test completed on staging. |
| Phase 3 — Monetization | Weeks 9–12 | Reservations, advanced analytics, Razorpay subscription billing, table merging, security hardening. 10 paying customers. | E2E Journeys 1–5 passing. Razorpay webhook handling tested with all event types. Dunning flow tested end-to-end. WCAG 2.1 AA audit completed. Lighthouse a11y score >= 90 on Customer PWA. |
| Phase 4 — AI & Scale | Weeks 13–20 | AI briefings, local deployment packaging, white-label (Luxury), mobile optimization, API webhooks for VIP+. ₹1L MRR. | Load test: 50 concurrent restaurants passing all k6 thresholds (§12.3). AI briefings generating correctly for 5 test restaurants. DPDP data export and deletion flows tested. Disaster recovery runbooks completed and tested. |

---

## 11. Payment Gateway — Razorpay (Resolved)

**Decision:** Razorpay as primary gateway. **Rationale:** India-first, supports UPI + cards + netbanking, strong webhook reliability, sandbox for testing, and lowest MDR for INR transactions.

- Subscription billing: Razorpay Subscriptions API for recurring monthly charges
- One-time payments: not required in MVP (TABLZ bills the restaurant, not end-customers)
- Webhook events to handle: `subscription.activated`, `subscription.charged`, `subscription.halted`, `subscription.cancelled`, `payment.failed`
- Razorpay keys stored server-side only (never in frontend bundle)
- Test mode enforced in dev/staging environments via `RAZORPAY_MODE` env variable

**Payment Flow:** Restaurant signs up → selects tier → redirected to Razorpay checkout → on success, `subscription_tier` updated in DB + webhook received as confirmation. Webhook is the source of truth (not the redirect callback, which can be spoofed).

### Other Resolved Decisions

| Question | Decision | Rationale |
|---|---|---|
| Local deployment hardware | Intel NUC (Phase 4) | More reliable than Pi under kitchen heat/power conditions |
| SMS provider (Luxury tier) | MSG91 | India pricing, DLT registration support, better delivery rates vs Twilio |
| POS integration | Deferred to Phase 5+ | Not in scope for v1 launch |
| AI briefing model | Anthropic Claude API (claude-haiku-3) | Best cost/quality for structured restaurant analytics. Data sent: aggregated metrics only — no PII, no customer data. |

---

## 12. Testing Strategy [NEW in v2.0]

No feature ships to production without passing the test requirements defined in this section. CI/CD pipeline enforces coverage thresholds and blocks merges that fail automated tests.

### 12.1 Testing Pyramid

| Layer | Tool | Coverage Target | Runs On |
|---|---|---|---|
| Unit Tests | pytest (backend), Jest (frontend) | 80% line coverage minimum | Every commit (CI) |
| Integration Tests | pytest + TestClient (FastAPI) | All API endpoints covered | Every PR (CI) |
| E2E Tests | Playwright | Critical user journeys | Pre-merge to main (CI) |
| Load Tests | k6 | See thresholds below | Pre-release (staging) |
| Security Scan | OWASP ZAP + truffleHog | Zero critical findings | Every PR (CI) |
| Accessibility | axe-core + Lighthouse | Zero critical a11y violations | Every PR (CI) |

### 12.2 Critical E2E User Journeys (Must Pass Before Any Release)

- **Journey 1 — Full Order Flow:** Customer scans QR → browses menu → places order → Chef receives order → updates status → Customer sees status update → Reception finalizes bill → barcode generated → table reset to available
- **Journey 2 — Admin Onboarding:** Register restaurant → verify email → create menu items → create tables → generate QR codes → complete first test order
- **Journey 3 — Table Merge:** Owner scans QR → adds guests → scans second table QR to merge → places merged order → single bill generated for merged table
- **Journey 4 — Subscription Upgrade:** Free tier restaurant → upgrade to Premium → verify new limits applied → verify Razorpay webhook processed
- **Journey 5 — Auth Security:** Attempt 6 failed logins → verify 15-min lockout → attempt QR session with expired token → verify rejection

### 12.3 Load Test Thresholds (k6)

Scenario: 50 concurrent restaurants, each with 10 active tables, all placing orders simultaneously. Duration: 10 minutes sustained load.

| Metric | Threshold | Action if Breached |
|---|---|---|
| API p95 response time | < 500ms | Block release — investigate bottleneck |
| API p99 response time | < 2000ms | Block release — investigate bottleneck |
| WebSocket message latency p95 | < 300ms | Block release |
| Error rate (5xx) | < 0.1% | Block release — find and fix errors |
| Throughput | > 1000 req/min sustained | If below — scale horizontally |
| DB connection pool exhaustion | 0 occurrences | Block release — tune pool size |

---

## 13. Error Handling & Recovery Specification [NEW in v2.0]

### 13.1 WebSocket Failure Scenarios

| Scenario | Detection | Recovery Behavior |
|---|---|---|
| WS server goes down | Client heartbeat timeout (3 missed pings) | Exponential backoff reconnect (1s, 2s, 4s, 8s, max 30s). Fall back to 10s HTTP polling on /api/v1/orders for order status. |
| Customer WS token expires (15 min) | Server sends token_expired event before expiry | Client auto-requests token refresh via /api/v1/auth/refresh using HttpOnly refresh token cookie. WS reconnects with new token. Transparent to user. |
| Chef WS disconnects mid-service | Client detects close event | Chef dashboard caches current order queue in memory. Reconnects with backoff. On reconnect, fetches full order queue to reconcile any missed events. |
| Network partition (LAN deployment) | All clients disconnect simultaneously | Each client independently retries. Server maintains order state in DB. On reconnect, clients receive full state snapshot before receiving incremental events. |

### 13.2 Order State Recovery

- Orders are always written to the database **before** the WebSocket event is broadcast. If WS broadcast fails, the order still exists in DB.
- Chef dashboard on reconnect: calls `GET /api/v1/orders?status=pending,received,preparing` to rebuild queue from DB — not from memory.
- **Idempotency:** `POST /api/v1/orders` accepts an optional `idempotency_key` header. Same key = same order returned, not a duplicate.
- Order status transitions are enforced server-side. Invalid transitions return HTTP 409 Conflict.

### 13.3 Payment Failure Handling

- Razorpay charge failure → webhook `payment.failed` received → restaurant marked as `payment_overdue` → 7-day grace period → email reminders on day 1, 3, 7.
- After 7 days: `subscription_tier` downgraded to free → admin notified → data preserved (not deleted) for 90 days.
- All webhook handlers are idempotent (check `razorpay_event_id`).

### 13.4 Database Failure

- Supabase provides automatic failover with replica. RTO for managed failover: < 60 seconds.
- Connection pool: SQLAlchemy async `pool_size=20`, `max_overflow=10`, `pool_timeout=30s`. On timeout: return HTTP 503 with `Retry-After: 5` header.
- Circuit breaker: if DB error rate > 10% in 60s window, open circuit breaker and return cached responses for read endpoints.

### 13.5 Error Response Standards

All errors return:
```json
{
  "success": false,
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human readable",
    "suggestion": "What to do next",
    "http_status": 400,
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

| Error Code | HTTP Status | When Used |
|---|---|---|
| AUTH_TOKEN_EXPIRED | 401 | JWT or session token past expiry |
| AUTH_INSUFFICIENT_ROLE | 403 | Customer session accessing admin endpoint |
| RESOURCE_NOT_FOUND | 404 | ID does not exist or belongs to other restaurant |
| ORDER_DUPLICATE | 409 | Idempotency key already used |
| ORDER_INVALID_TRANSITION | 409 | Invalid status change attempted |
| SUBSCRIPTION_LIMIT_EXCEEDED | 402 | Action blocked by tier limits |
| RATE_LIMIT_EXCEEDED | 429 | Rate limit hit — Retry-After header included |
| VALIDATION_ERROR | 422 | Pydantic schema validation failed |
| INTERNAL_ERROR | 500 | Unexpected server error |
| SERVICE_UNAVAILABLE | 503 | DB circuit breaker open or dependency down |

---

## 14. Data Privacy, Retention & DPDP Compliance [NEW in v2.0]

India's Digital Personal Data Protection Act (DPDP) 2023 is in force. TABLZ handles personal data of restaurant owners (email, phone) and indirectly of their customers (device fingerprints, session data). Compliance is mandatory before launch.

### 14.1 Data Classification

| Data Type | Classification | Examples | Retention |
|---|---|---|---|
| Restaurant owner PII | Sensitive | Email, business name, phone | Duration of account + 3 years |
| Customer session data | Personal | Device fingerprint, session token | 4 hours (session) then anonymized |
| Order data | Business | Items ordered, amounts, timestamps | 3 years (tax compliance) |
| Analytics data | Aggregated | Revenue totals, item counts | Per subscription tier depth |
| Audit logs | Security | Login events, IP addresses | 90 days minimum, 1 year for security events |
| Payment data | Financial | Razorpay subscription ID (no card data) | 7 years (financial compliance) |

### 14.2 Data Subject Rights (DPDP)

- **Right to Access:** `GET /api/v1/account/data-export` — returns all restaurant data as JSON within 72 hours.
- **Right to Erasure:** `DELETE /api/v1/account` — soft-deletes account, anonymizes PII within 30 days. Financial records retained 7 years (legal obligation).
- **Right to Correction:** admin can update email, name, phone via reception dashboard settings at any time.
- **Data Portability:** menu data, order history exportable as CSV (Luxury tier) or on account deletion request (all tiers).

### 14.3 Third-Party Data Sharing

| Third Party | Data Sent | Purpose | DPA |
|---|---|---|---|
| Razorpay | Email, subscription tier, amount | Payment processing | Razorpay DPA — signed on API key activation |
| Anthropic (Claude API) | Aggregated metrics only (revenue totals, item counts, no PII) | AI briefings generation | Anthropic API ToS — no PII transmitted |
| AWS S3 | Menu images (no metadata) | File storage | AWS DPA |
| SendGrid / SMTP | Owner email address | Transactional email | SendGrid DPA |
| MSG91 | Phone number (Luxury tier) | SMS notifications | MSG91 DPA |
| Sentry / Datadog | Anonymized error traces, no PII | Monitoring | Vendor DPA |

### 14.4 Data Storage Location

- Supabase database: **AWS ap-south-1 (Mumbai)** region for India-first compliance.
- S3 bucket: ap-south-1 (Mumbai) region.
- Redis cache: session data only, no PII stored in cache. TTL-bound.
- Logs: shipped to Datadog. Log retention 90 days. PII masked in all logs.

---

## 15. Disaster Recovery & Backup SLA [NEW in v2.0]

### 15.1 Recovery Objectives

| Scenario | RPO (Max Data Loss) | RTO (Max Downtime) | Owner |
|---|---|---|---|
| DB corruption / accidental deletion | 1 hour (hourly snapshots) | < 2 hours | Eng lead |
| DB server failure (Supabase failover) | < 1 minute (streaming replication) | < 60 seconds (auto) | Supabase |
| Application server crash | 0 (DB is source of truth) | < 2 minutes (auto-restart) | CI/CD |
| Full region outage | < 1 hour | < 4 hours (manual failover) | Eng lead |
| Accidental data deletion by admin | 1 hour (last snapshot) | < 2 hours | Eng lead |

### 15.2 Backup Policy

- Automated daily full DB snapshots via Supabase PITR (Point-in-Time Recovery) — retained for 30 days.
- Hourly incremental WAL (Write-Ahead Log) backups — retained for 7 days.
- Backup restore test: conducted monthly. Restore a snapshot to staging, verify data integrity, document results.
- Local deployment: cron job at 2am daily creates a compressed DB dump to an external USB or NAS.

### 15.3 Runbook Locations

All incident runbooks stored in repository wiki at `/docs/runbooks/`. Key runbooks required before launch: DB restore, WebSocket server restart, Redis flush, Razorpay webhook replay, emergency account disable.

---

## 16. Subscription Lifecycle [NEW in v2.0]

### 16.1 Upgrade Flow

Admin clicks 'Upgrade Plan' in Reception → Settings → Subscription → Razorpay hosted checkout → on success, `subscription.activated` webhook → TABLZ backend updates `subscription_tier` in DB immediately → New limits take effect immediately. Prorated billing handled by Razorpay.

### 16.2 Downgrade Flow

Downgrade takes effect at the **end of the current billing cycle** (not immediately).

- Admin requests downgrade → `scheduled_tier` set in DB → current tier remains active until period end.
- 7 days before effective date: email warning listing what will be restricted.
- On effective date: limits enforced. **Data is NOT deleted — only access restricted.**

> **Data on Downgrade — Critical Policy:** Data is NEVER deleted on tier downgrade. If a Premium restaurant (200 menu items) downgrades to Free (50 item limit), their 200 items are preserved but only 50 are visible to customers. Admin sees a warning in the menu management UI. Items surface again immediately on upgrade.

### 16.3 Dunning Schedule

| Day | Action | Channel |
|---|---|---|
| Day 0 (payment fails) | Subscription marked payment_overdue. Grace period begins. | Webhook |
| Day 1 | Email: 'Your payment failed — please update your payment method' | Email |
| Day 3 | Email: 'Action required — 4 days until service restriction' | Email |
| Day 6 | Email: 'Final notice — service restricts tomorrow' | Email + SMS (if available) |
| Day 7 | Tier downgraded to Free. Admin can still log in and update payment. | System |
| Day 30 | Account flagged for potential closure. Admin notified. | Email |
| Day 90 | Account soft-deleted if no payment. Data retained 90 more days, then purged. | System + Email |

---

## 17. AI Briefings Specification [NEW in v2.0]

> **Data Privacy Commitment:** AI briefings use the Anthropic Claude API. ONLY aggregated, anonymized metrics are sent — no customer names, no PII, no individual order details.

### 17.1 Briefing Schedule by Tier

| Tier | Frequency | Delivery Method | Model Used |
|---|---|---|---|
| Free | Not available | — | — |
| Premium | Weekly (Monday 8am) | Email + Reception dashboard | claude-haiku-3 |
| VIP | Daily (8am local time) | Email + Reception dashboard | claude-haiku-3 |
| Luxury | Real-time (on demand + daily) | Reception dashboard widget | claude-haiku-3 |

### 17.2 Data Collected for Briefing (No PII)

- Yesterday's gross revenue, net revenue, number of orders, average order value
- Top 5 menu items by order count and revenue
- Bottom 5 menu items (lowest order count — waste candidates)
- Peak hour distribution (order count by hour, no customer identifiers)
- Table occupancy rate (% of time tables were occupied)
- Average table turn time (minutes from first order to bill finalization)
- Comparison to previous 7-day average for each metric

### 17.3 System Prompt Template

> You are a restaurant business advisor. You will receive yesterday's operational metrics for a restaurant. Generate a concise daily briefing (max 300 words) covering: (1) one key win to celebrate, (2) one operational concern with a specific suggestion, (3) one menu recommendation (promote or consider removing an item), (4) one observation about timing/staffing. Be specific, actionable, and encouraging. Do not mention customer names or any personal information. Respond in plain text, no markdown.

### 17.4 Implementation

- Celery beat task: `generate_ai_briefing` runs daily at 7am UTC.
- Generated briefing stored in `ai_briefings` table (restaurant_id, generated_at, content, model_used, tokens_used).
- Cost estimate: ~2,000 tokens per briefing. At claude-haiku-3 pricing: ~₹0.20/briefing.
- Error handling: if Claude API fails, log error and send briefing next cycle. Never show a broken state to the admin.

---

## 18. Accessibility Requirements [NEW in v2.0]

WCAG 2.1 Level AA for all three dashboards. The Customer PWA is used by the general public on mobile.

| Requirement | Customer PWA | Reception | Chef |
|---|---|---|---|
| Color contrast ratio | 4.5:1 minimum (AA) | 4.5:1 minimum | 4.5:1 minimum |
| Touch target size | 44x44px minimum | 44x44px minimum | 48x48px (gloved hands) |
| Screen reader support | Full (ARIA labels) | Full | Partial (visual-first KDS) |
| Keyboard navigation | Full | Full | Partial |
| Font size minimum | 16px body text | 14px body text | 18px (distance viewing) |
| Error messages | ARIA live region | ARIA live region | ARIA live region |
| Focus indicators | Visible 3px outline | Visible 3px outline | Visible 3px outline |
| Image alt text | Required for all menu images | Required | N/A |
| Motion/animation | Respect prefers-reduced-motion | Respect | Respect |

**Testing Protocol:**
- axe-core integrated into Playwright E2E tests — any critical or serious violation blocks the PR.
- Lighthouse accessibility score target: >= 90 for Customer PWA, >= 85 for Reception and Chef dashboards.
- Manual screen reader test with VoiceOver (iOS) for the Customer PWA before each major release.

---

## 19. Open Questions

All critical decisions from v1.0 have been resolved. The following are lower-priority decisions for later phases.

| Question | Options / Context | Phase Needed By | Owner |
|---|---|---|---|
| Thermal printer / KDS integration | Epson TM webhook bypass vs full POS integration | Phase 5+ | Founder |
| Multi-language menu support | English-only MVP vs i18n from day 1 | Phase 3 | Founder + Eng |
| Customer-facing payment (UPI at table) | Razorpay payment link vs QR UPI vs deferred | Phase 4 | Founder |
| Staff individual PIN login | DB table added in v2.0 schema — implementation timing | Phase 3 | Eng Lead |
| Mobile app (native iOS/Android) | PWA-only vs native app in Phase 5+ | Phase 5+ | Founder |

---

## Document Control

This PRD is the source of truth for all engineering and design decisions. All architectural changes must be logged as changelog entries. No code should be written for features not covered in this document without a corresponding PRD update approved by the Founder. Raise questions as GitHub issues tagged `PRD`.

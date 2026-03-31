# 10 — Development Phases
## TABLZ — AI-Powered Restaurant Management Platform

---

## Phase Overview

| Phase | Duration | Focus | Technical Gate |
|-------|----------|-------|---------------|
| Phase 0 | Pre-code | Validation & setup | Razorpay sandbox working, DB schema approved |
| Phase 1 | Weeks 1–4 | Core order flow | E2E Journey 1 passing in CI |
| Phase 2 | Weeks 5–8 | Operational readiness | First pilot restaurant live |
| Phase 3 | Weeks 9–12 | Monetization | 10 paying customers |
| Phase 4 | Weeks 13–20 | AI & scale | ₹1L MRR target |

---

## Phase 0 — Pre-Code (Before Week 1)

### Deliverables
- 20 restaurant owner interviews completed
- Validated problem statement
- 3 signed LOIs from pilot restaurants
- Razorpay sandbox configured and keys working
- Supabase project provisioned (ap-south-1 Mumbai)
- DB schema v2.0 reviewed and approved

### Gate Criteria
- [ ] Razorpay sandbox keys working (test charge successful)
- [ ] DB schema v2.0 reviewed and approved
- [ ] All open questions from PRD §11 resolved

---

## Phase 1 — Core Flow (Weeks 1–4)

### Week 1 — Foundation
**Goal:** Auth works end-to-end.

| # | Task | Priority |
|---|------|----------|
| 1 | FastAPI app with lifespan events (DB pool init/teardown) | P0 |
| 2 | `config.py` with pydantic-settings | P0 |
| 3 | `database.py` with SQLAlchemy async engine | P0 |
| 4 | Run migrations (001 core tables, 002 RLS) | P0 |
| 5 | AuthService: register, verify_email, login, refresh, logout | P0 |
| 6 | Rate limiting middleware (Redis, 5 attempts → 15-min lockout) | P0 |
| 7 | Standard error response format in `errors.py` | P0 |
| 8 | Unit tests for AuthService (≥80% coverage) | P0 |

**Definition of Done:**
- POST /auth/register → 201, generates admin_id, sends verification email
- POST /auth/verify-email/:token → 200
- POST /auth/login → 200, access token + refresh cookie
- POST /auth/refresh → 200, new access token
- POST /auth/logout → 200, refresh invalidated
- 6th login attempt → 429 with Retry-After: 900

### Week 2 — Menu & Tables
**Goal:** Admin builds menu and creates tables with QR codes.

| # | Task | Priority |
|---|------|----------|
| 1 | MenuService: CRUD, soft-delete, sanitization, availability toggle | P0 |
| 2 | TableService: creation, QR token generation, QR image generation | P0 |
| 3 | S3 upload helper (async with aioboto3) | P0 |
| 4 | Menu and table router endpoints | P0 |
| 5 | Integration tests for menu + table endpoints | P0 |

**Definition of Done:**
- Full CRUD on /menu (restaurant_id-scoped)
- POST /tables creates table, generates QR, uploads to S3
- Soft delete sets is_deleted=true
- OWASP ZAP scan: zero critical findings

### Week 3 — Customer Ordering
**Goal:** Customer scans QR, browses menu, places order.

| # | Task | Priority |
|---|------|----------|
| 1 | Customer session creation (POST /auth/qr-session) | P0 |
| 2 | OrderService: create_order with idempotency, price snapshot, validation | P0 |
| 3 | Order status state machine (server-enforced) | P0 |
| 4 | Customer-facing endpoints (menu browse, order placement, status view) | P0 |

**Definition of Done:**
- Full E2E Journey 1 passing (manual Playwright)
- Idempotency working (duplicate POST returns original order)
- Cross-restaurant item injection blocked
- State machine transitions enforced

### Week 4 — Chef Dashboard & WebSocket
**Goal:** Real-time order events for Chef.

| # | Task | Priority |
|---|------|----------|
| 1 | WebSocket manager (room-based, auth, heartbeat, token refresh) | P0 |
| 2 | Wire OrderService to broadcast events after DB writes | P0 |
| 3 | Chef dashboard WS reconnect + fallback logic | P0 |
| 4 | Reception dashboard order view + status update | P0 |
| 5 | Bill finalization (POST /orders/:id/finalize, barcode generation) | P0 |
| 6 | E2E tests for Journey 1 in Playwright (CI) | P0 |

**Phase 1 Gate:**
- [ ] E2E Journey 1 passing in CI
- [ ] 80% unit test coverage on AuthService + OrderService
- [ ] Zero critical findings from OWASP ZAP
- [ ] All endpoints use standard error format
- [ ] WS token refresh working (automated test)

---

## Phase 2 — Operational (Weeks 5–8)

### Weeks 5–6 — Table Management & Analytics

| # | Task | Priority |
|---|------|----------|
| 1 | Table status lifecycle (available → occupied → cleaning → available) | P0 |
| 2 | Reception table map (grid view with status colors) | P0 |
| 3 | Table cleaning flow (POST /tables/:id/clean) | P0 |
| 4 | Analytics: summary, popular-items, occupancy endpoints | P0 |
| 5 | Celery setup + reset_daily_specials task | P1 |

### Weeks 7–8 — Pilot Hardening

| # | Task | Priority |
|---|------|----------|
| 1 | Load test (k6: 10 restaurants, 100 req/min, p95 < 500ms) | P0 |
| 2 | Backup restore drill on staging | P0 |
| 3 | Error monitoring setup (Sentry) | P0 |
| 4 | HTTPS + security headers (HSTS, CSP, X-Frame-Options) | P0 |
| 5 | PWA config for Customer dashboard (manifest, service worker) | P1 |
| 6 | E2E Journey 2 (Admin Onboarding) + Journey 3 placeholder | P1 |

**Phase 2 Gate:**
- [ ] E2E Journeys 1–3 passing in CI
- [ ] WS token refresh automated test passing
- [ ] Load test: 10 restaurants, 100 req/min, p95 < 500ms
- [ ] Backup restore test completed and documented
- [ ] First pilot restaurant successfully onboarded and transacting

---

## Phase 3 — Monetization (Weeks 9–12)

### Key Deliverables
- Reservation system (CRUD, status lifecycle)
- Advanced analytics (peak hours, table turnaround VIP+, export Luxury)
- Razorpay subscription billing integration
- Webhook processing (subscription events, payment events)
- Dunning flow (7-day grace period, automated emails)
- Table merging (tier-limited)
- Staff PIN login
- WCAG 2.1 AA compliance
- DPDP data export/deletion endpoints

### Target: 10 paying customers

**Phase 3 Gate:**
- [ ] E2E Journeys 1–5 passing
- [ ] Razorpay webhook handling tested (all event types)
- [ ] Dunning flow tested end-to-end
- [ ] WCAG 2.1 AA audit completed
- [ ] Lighthouse a11y score ≥ 90 on Customer PWA

---

## Phase 4 — AI & Scale (Weeks 13–20)

### Key Deliverables
- AI briefings (Claude API integration, Celery scheduled generation)
- Local (LAN) deployment packaging (Docker Compose bundle)
- White-label (Luxury tier)
- Mobile optimization
- API webhooks for VIP+
- Scoring engine (menu performance, table efficiency, operational health)

### Target: ₹1L MRR

**Phase 4 Gate:**
- [ ] Load test: 50 restaurants, 1,000 req/min passing k6 thresholds
- [ ] AI briefings generating correctly for 5 test restaurants
- [ ] DPDP data export and deletion flows tested
- [ ] Disaster recovery runbooks completed and tested
- [ ] Local deployment tested on Intel NUC hardware

---

## Priority Framework

| Priority | Meaning | Example |
|----------|---------|---------|
| P0 | Must have — blocks pilot launch | Auth, ordering, WebSocket |
| P1 | Should have — improves pilot quality | PWA config, Celery specials reset |
| P2 | Nice to have — can ship later | Bulk CSV import, advanced analytics |
| P3 | Future — not in current phase | AI briefings, LAN deployment |

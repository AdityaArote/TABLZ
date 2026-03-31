# 09 — Engineering Scope Definition
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. MVP Scope (Phase 1 + Phase 2 — Weeks 1–8)

### In Scope

| Area | Deliverables |
|------|-------------|
| **Auth** | Restaurant registration, email verification, admin login (JWT), customer QR session, token refresh, logout, rate-limited login |
| **Menu** | CRUD, soft-delete, availability toggle, input sanitization, tier limit enforcement |
| **Tables** | Creation, QR code generation/upload, status lifecycle (available → occupied → cleaning → available) |
| **Customer Flow** | QR scan → session creation → menu browse → order placement with idempotency |
| **Orders** | Server-enforced state machine, price snapshotting, bill finalization, barcode generation |
| **Chef Dashboard** | Real-time order queue via WebSocket, status updates, reconnect/fallback logic |
| **WebSocket** | Room-based channels, heartbeat, token refresh protocol, state snapshots on reconnect |
| **Analytics** | Revenue summary, popular items, occupancy (7-day rolling for Free tier) |
| **Celery** | Daily/weekly special resets |
| **Error Handling** | Standard error response format, all error codes defined |
| **Security** | bcrypt passwords, HttpOnly cookies, RLS, rate limiting, OWASP ZAP scanning |

### Explicitly Out of Scope (MVP)

| Feature | Deferred To | Reason |
|---------|-------------|--------|
| Reservations | Phase 3 | Not part of core order loop |
| Table merging | Phase 3 | Adds complexity to billing |
| Razorpay subscription billing | Phase 3 | MVP restaurants on Free tier |
| AI briefings | Phase 4 | Requires analytics maturity |
| Advanced analytics (peak hours, export) | Phase 3–4 | Not critical for pilot |
| White-label / custom branding | Phase 4 | Luxury-only feature |
| Local (LAN) deployment | Phase 4 | Docker packaging effort |
| Staff PIN login | Phase 3 | DB table ready, implementation deferred |
| Webhooks for Luxury tier | Phase 3 | Enterprise feature |
| DPDP data export/deletion | Phase 3 | Legal compliance, not launch-blocking |
| Multi-language menus | Phase 3+ | English-only MVP |
| Native mobile app | Phase 5+ | PWA first |
| POS/thermal printer integration | Phase 5+ | Not in scope for v1 |

---

## 2. Engineering Constraints

### Technical Constraints

| Constraint | Detail |
|-----------|--------|
| Single backend | One FastAPI instance, no microservices in MVP |
| Single DB | One PostgreSQL 15 instance (Supabase) |
| No SSR for Customer PWA | Static + client-side rendering for speed |
| Python 3.11+ | Required for async features |
| SQLAlchemy 2.0+ | Async ORM required |
| Next.js 14 | App Router for all frontends |

### Operational Constraints

| Constraint | Detail |
|-----------|--------|
| Solo founder | Aditya builds everything — minimize operational overhead |
| Budget | Free-tier services where possible (Supabase free, Vercel free) |
| Target market | India-first (INR, Mumbai region, Razorpay) |
| Data residency | AWS ap-south-1 (Mumbai) for all data storage |

### Performance Constraints

| Metric | Phase 2 Target | Phase 4 Target |
|--------|----------------|----------------|
| Concurrent restaurants | 10 | 50 |
| Request rate | 100 req/min | 1,000 req/min |
| API p95 latency | < 500ms | < 500ms |
| WS message latency p95 | < 300ms | < 300ms |
| Error rate (5xx) | < 0.1% | < 0.1% |

---

## 3. Architecture Boundaries

### What the Frontend Does
- Renders UI state
- Sends REST API calls for CRUD
- Subscribes to WebSocket for real-time updates
- Handles transparent token refresh (HttpOnly cookie flow)

### What the Frontend Does NOT Do
- Business rule validation (server-side only)
- Direct database queries
- Payment processing logic
- Store tokens in localStorage (HttpOnly cookies only)

### What the Backend Does
- All business logic in Service Layer
- JWT and session token validation
- Subscription tier enforcement
- Rate limiting
- Input sanitization
- WebSocket event broadcasting (after DB write)

### What the Backend Does NOT Do
- Serve static frontend assets (Vercel handles this)
- Store secrets in code (env vars only)
- Hard-delete data (soft deletes only)
- Trust client-provided `restaurant_id` in write operations

---

## 4. Critical Implementation Rules

1. **Never trust client-provided `restaurant_id` in write operations.** Extract from validated JWT.
2. **Set `app.current_restaurant_id` before every DB query.** RLS depends on it.
3. **Write to DB before broadcasting WebSocket events.** WS is a display optimization, not state.
4. **Snapshot prices at order time.** `unit_price_at_order`, not a FK to current price.
5. **Validate QR token lookups against `restaurant_id`.** Prevent cross-restaurant access.
6. **All text input sanitized.** Bleach for HTML fields, strip-all for plain text fields.
7. **Return 404 (not 403) for cross-tenant access.** Don't confirm resource existence.

---

## 5. Team & Ownership

| Area | Owner | Technology |
|------|-------|-----------|
| Backend API | Aditya (Founder) | FastAPI, Python |
| Database | Aditya | PostgreSQL, Supabase, Alembic |
| Reception Dashboard | Aditya | Next.js 14, React, Tailwind |
| Customer Dashboard | Aditya | Next.js PWA, React |
| Chef Dashboard | Aditya | Next.js, React, WebSocket |
| DevOps / CI | Aditya | GitHub Actions, Docker |
| Security | Aditya | OWASP ZAP, truffleHog |

---

## 6. Definition of MVP Complete

All of the following must be true:

1. ✅ E2E Journey 1 (Full Order Flow) passes in CI
2. ✅ E2E Journey 2 (Admin Onboarding) passes in CI
3. ✅ 80% unit test coverage on AuthService, OrderService, MenuService, TableService
4. ✅ Zero critical findings from OWASP ZAP
5. ✅ All API endpoints return standard error format
6. ✅ Load test: 10 concurrent restaurants, 100 req/min, p95 < 500ms on staging
7. ✅ WebSocket token refresh works without disconnect (automated test)
8. ✅ At least one pilot restaurant has successfully placed and fulfilled 10 real orders
9. ✅ Backup restore test documented on staging

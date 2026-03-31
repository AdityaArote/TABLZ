# 12 — Testing Strategy
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Testing Philosophy

No feature ships to production without passing the test requirements defined here. The CI/CD pipeline enforces coverage thresholds and blocks merges that fail automated tests.

---

## 2. Testing Pyramid

| Layer | Tool | Coverage Target | Runs On |
|-------|------|----------------|---------|
| Unit Tests | pytest (backend), Jest (frontend) | 80% line coverage minimum | Every commit (CI) |
| Integration Tests | pytest + TestClient (FastAPI) | All API endpoints covered | Every PR (CI) |
| E2E Tests | Playwright | Critical user journeys | Pre-merge to main (CI) |
| Load Tests | k6 | See thresholds below | Pre-release (staging) |
| Security Scan | OWASP ZAP + truffleHog | Zero critical findings | Every PR (CI) |
| Accessibility | axe-core + Lighthouse | Zero critical a11y violations | Every PR (CI) |

---

## 3. Unit Testing

### Backend (pytest + pytest-asyncio)

**Target:** ≥ 80% line coverage on all service files.

**Priority services:**
- `auth_service.py` — JWT, bcrypt, session creation, rate limiting
- `order_service.py` — Ordering, state machine, idempotency, billing
- `menu_service.py` — CRUD, soft-delete, tier limits
- `table_service.py` — QR generation, merge logic, cleaning

**What to test:**
- All business logic paths (success + error)
- Input validation edge cases
- Subscription tier limit enforcement
- Order state machine transitions (valid + invalid)
- Price snapshotting accuracy
- `restaurant_id` scoping (no cross-tenant leaks)

**What NOT to unit test:**
- Database schema (tested via integration tests)
- External API calls (mocked)
- Frontend rendering

### Frontend (Jest + React Testing Library)

**Target:** Component-level tests for key interactions.

- Menu item card rendering with all dietary labels
- Order status display for all states
- WebSocket reconnection logic
- Token refresh flow

---

## 4. Integration Testing

### Backend API Integration (pytest + FastAPI TestClient)

Every API endpoint must have at least one integration test covering:
- ✅ Successful response (correct status code, body shape)
- ✅ Auth required (401 without token)
- ✅ Validation error (422 with bad input)
- ✅ Not found (404 with invalid ID)
- ✅ Tier limit enforcement (402 when applicable)

**Key integration test scenarios:**

| Endpoint | Test Scenarios |
|----------|---------------|
| POST /auth/register | Success (201), duplicate email (409), missing fields (422) |
| POST /auth/login | Success (200), wrong password (401), unverified email (403), rate limited (429) |
| POST /menu | Success (201), tier limit exceeded (402), missing auth (401) |
| DELETE /menu/:id | Soft delete (200), cross-restaurant (404), already deleted (404) |
| POST /orders | Success (201), idempotency (200), cross-restaurant items (404), invalid state (409) |
| PATCH /orders/:id/status | Valid transition (200), invalid transition (409), wrong restaurant (404) |
| POST /tables/:id/merge | Success (200), not owner (403), target occupied (409), tier limit (402) |

---

## 5. E2E Testing (Playwright)

### Critical User Journeys

All must pass before any release.

#### Journey 1 — Full Order Flow (MVP Critical Path)
```
1. Customer scans QR code → lands on menu page
2. Customer browses menu → adds items to cart
3. Customer places order → sees "Order Placed" confirmation
4. Chef dashboard receives order in queue (real-time)
5. Chef taps "Accept" → status changes to "received"
6. Chef taps "Preparing" → customer sees "Preparing"
7. Chef taps "Ready" → customer sees "Ready"
8. Reception marks "Served"
9. Reception finalizes bill → barcode generated
10. Table reset → status returns to "available"
```

#### Journey 2 — Admin Onboarding
```
1. Register restaurant → receive verification email
2. Verify email → log in
3. Create 3 menu items
4. Create 2 tables → QR codes generated
5. Download QR code
6. Complete one test order end-to-end
```

#### Journey 3 — Table Merge
```
1. Customer A scans QR at Table 5 (becomes owner)
2. Customer A merges with Table 8 (available)
3. Customer B scans QR at Table 8 → joins merged session
4. Both customers place orders → single bill for Table 5
5. Reception finalizes → single barcode
6. Both tables reset to available
```

#### Journey 4 — Subscription Upgrade (Phase 3)
```
1. Free tier restaurant hits table limit (10)
2. Admin clicks "Upgrade" → Razorpay checkout
3. On success → subscription_tier = 'premium'
4. Verify new limits applied (30 tables)
5. Verify Razorpay webhook processed
```

#### Journey 5 — Auth Security
```
1. Attempt 6 failed logins → verify 429 with Retry-After
2. Wait lockout period → verify login works again
3. Attempt QR session with expired token → verify rejection
4. Attempt to access Restaurant A's data with Restaurant B's JWT → verify 404
```

---

## 6. Load Testing (k6)

### Scenario
50 concurrent restaurants, 10 active tables each, all ordering simultaneously. Duration: 10 minutes sustained.

### Thresholds

| Metric | Threshold | Action if Breached |
|--------|-----------|-------------------|
| API p95 response time | < 500ms | Block release |
| API p99 response time | < 2000ms | Block release |
| WebSocket message latency p95 | < 300ms | Block release |
| Error rate (5xx) | < 0.1% | Block release |
| Throughput | > 1000 req/min sustained | Scale horizontally if below |
| DB connection pool exhaustion | 0 occurrences | Block release |

### Performance Budget

| Component | Budget |
|-----------|--------|
| Auth (login) | p95 < 200ms |
| Menu fetch (cached) | p95 < 50ms |
| Order placement | p95 < 500ms |
| WS event broadcast | p95 < 300ms |
| DB query (99th pct) | < 100ms |
| AI briefing generation | < 30s (async) |

---

## 7. Security Testing

### Automated (Every PR)

| Tool | Purpose | Gate |
|------|---------|------|
| truffleHog | Secret detection in code | Zero secrets found |
| OWASP ZAP | Vulnerability scanning | Zero critical findings |
| npm audit | Frontend dependency vulnerabilities | Zero critical |
| pip-audit | Backend dependency vulnerabilities | Zero critical |

### Manual (Pre-Release)

- Verify `restaurant_id` scoping: authenticate as Restaurant A, attempt to access Restaurant B resources → must return 404
- Verify rate limiting triggers on all appropriate endpoints
- Verify HttpOnly cookies are not accessible via JavaScript
- Verify SQL injection strings are sanitized (not 500)

---

## 8. Accessibility Testing

### Automated (Every PR)
- **axe-core** integrated into Playwright E2E tests — critical/serious violations block PR
- **Lighthouse** accessibility score:
  - Customer PWA: ≥ 90
  - Reception Dashboard: ≥ 85
  - Chef Dashboard: ≥ 85

### Manual (Pre-Release)
- Screen reader test with VoiceOver (iOS) on Customer PWA
- Keyboard navigation test on all dashboards
- Color contrast verification
- Touch target size verification (44×44px minimum, 48×48px Chef)

---

## 9. Testing Checklist (Per Feature Branch)

Before merging any feature branch:

- [ ] Unit tests pass with ≥ 80% coverage on modified service files
- [ ] Integration tests pass for all modified API endpoints
- [ ] All responses use standard error format
- [ ] No secrets committed (truffleHog passes)
- [ ] OWASP ZAP: zero critical findings on new endpoints
- [ ] `restaurant_id` scoping verified manually
- [ ] Input validation tested (missing fields → 422, invalid types → 422, SQL injection → sanitized)
- [ ] Rate limiting verified on appropriate endpoints
- [ ] Relevant E2E journeys pass

---

## 10. Test Data Management

### Seed Script
`scripts/seed_test_data.py` creates:
- 5 restaurants (one per subscription tier + one free)
- 50 tables (10 per restaurant)
- 200 menu items (40 per restaurant)
- 1,000 orders with realistic distribution

### Test Database
- Separate test database for CI (`tablz_test`)
- Migrations run before tests
- Database wiped between test suites
- Fixtures via factory pattern (`tests/fixtures/factories.py`)

# TABLZ — System Design Document
**AI-Powered Restaurant Management Platform**
**v2.0**

---

## 1. System Overview

TABLZ is a real-time, multi-tenant SaaS platform serving three distinct user types simultaneously: restaurant admins (Reception), kitchen staff (Chef), and restaurant guests (Customer). The core technical challenge is delivering sub-300ms real-time synchronization across all three dashboards while maintaining strict per-restaurant data isolation at scale.

---

## 2. Core Data Flows

### 2.1 The Full Order Lifecycle

This is the most critical system flow. Every design decision in TABLZ optimizes for reliability and speed of this path.

```
Customer scans QR code
        │
        ▼
GET /api/v1/auth/qr-session
  → Validate qr_code_token
  → Create customer_session row (is_table_owner = first scanner)
  → Issue session_token (HttpOnly cookie)
  → Update tables.status = 'occupied'
        │
        ▼
Customer browses menu
GET /api/v1/menu?restaurant_id={id}
  → Returns is_available items only
  → is_deleted items excluded by default
        │
        ▼
Customer places order
POST /api/v1/orders
  Headers: Idempotency-Key: {uuid}
  Body: { table_id, items: [{menu_item_id, quantity, item_notes}] }
        │
        ├── 1. Check idempotency key (Redis) — return existing if duplicate
        ├── 2. Validate session token + table ownership
        ├── 3. Snapshot unit_price_at_order for each item (protects against price changes mid-meal)
        ├── 4. Compute total_amount + tax_amount from active tax_config
        ├── 5. Write order + order_items to PostgreSQL
        ├── 6. Write to audit_log
        └── 7. Broadcast order.created event via WebSocket to restaurant channel
                │
                ▼
        Chef Dashboard receives event
        → Order appears in queue (status: pending)
        → Chef taps to accept → PATCH /api/v1/orders/:id/status {status: 'received'}
        → Broadcast order.status_changed → Customer sees "Order received"
        → Chef taps preparing → received
        → Chef taps ready → preparing
        → Serving staff delivers → Reception marks 'served'
        │
        ▼
Reception finalizes bill
POST /api/v1/orders/:id/finalize
  → Validates all items are served (or explicitly cancelled)
  → Locks order (is_finalized = true)
  → Generates barcode_token
  → Stores barcode PDF to S3
  → Returns barcode URL for printing
        │
        ▼
Table reset
  → customer_sessions invalidated
  → tables.status = 'available' (or 'cleaning')
  → tables.owner_session_id = NULL
```

### 2.2 QR Code Generation & Validation

```
Reception creates table
POST /api/v1/tables
  → Generate cryptographically secure qr_code_token (128 chars, secrets.token_urlsafe)
  → Build qr_code_url: https://tablz.app/t/{token}
  → Generate QR image (Python qrcode lib)
  → Store image to S3
  → Store token + url in tables row
  → Return QR image URL for printing

QR Token Validation (on every scan)
  → Look up qr_code_token in tables
  → Verify table belongs to authenticated restaurant (RLS + explicit check)
  → Verify table is not in 'cleaning' or 'reserved' status
  → Check for existing active customer_session on this table
  → Create new session or join existing group session
```

### 2.3 WebSocket Event System

```
Connection lifecycle:
  1. Client connects: WS /ws/{restaurant_id}
  2. Server validates JWT/session token in connection headers
  3. Client added to room: restaurant:{restaurant_id}
  4. Server sends current state snapshot (pending orders, table statuses)
  5. Client receives incremental events thereafter

Token refresh (transparent, no reconnection):
  t=0min:   Client connects with access_token (15-min TTL)
  t=13min:  Server sends: {type: 'token_expiring_soon', expires_in_seconds: 120}
  t=13min:  Client calls POST /api/v1/auth/refresh (HttpOnly cookie, no JS access)
  t=13min:  Client sends: {type: 'reauth', token: 'new_access_token'}
  t=13min:  Server validates, updates session — no disconnect
  t=15min:  Original token would have expired — new token active

Connection failure recovery:
  Heartbeat: server pings every 30s, client pongs
  3 missed pings → client initiates reconnect
  Reconnect: exponential backoff (1s, 2s, 4s, 8s, max 30s)
  Fallback: HTTP polling on GET /api/v1/orders every 10s if WS unavailable
  On reconnect: server sends full state snapshot before resuming incremental events

Event types:
  order.created          → Chef + Reception see new order
  order.status_changed   → All parties updated on status
  order.finalized        → Table marked ready to reset
  table.status_changed   → Reception map updated
  token_expiring_soon    → Trigger client token refresh
  session_expired        → Graceful WS close (code 4001)
```

### 2.4 Multi-Table Merge Flow

```
Customer A (table owner at Table 5) wants to merge with Table 8:

POST /api/v1/tables/5/merge
  Body: { merge_with_table_id: 8 }
  Auth: Customer session with is_table_owner = true

Server:
  → Validate session is table owner
  → Validate Table 8 is 'available' (cannot merge into occupied table)
  → Check subscription allows merges (Premium: max 3, VIP: max 5, Luxury: unlimited)
  → Update tables SET merged_into_table_id = 5 WHERE id = 8
  → Update tables SET status = 'merged' WHERE id = 8
  → All subsequent orders placed at Table 8 → routed to Table 5's bill
  → Broadcast table.status_changed for both tables

Billing:
  → POST /api/v1/orders/:id/finalize at Table 5 picks up all orders from merged tables
  → Single bill, single barcode
  → On reset: all merged tables released, merged_into_table_id cleared
```

### 2.5 AI Briefing Generation

```
Daily Celery task (7am UTC):

For each restaurant where:
  - subscription_tier IN ('premium', 'vip', 'luxury')
  - AND (tier='premium' AND day_of_week='Monday') OR tier IN ('vip','luxury')

  1. AnalyticsService.get_briefing_metrics(restaurant_id, date=yesterday)
     Returns: {
       gross_revenue, net_revenue, order_count, avg_order_value,
       top_5_items: [{name, count, revenue}],
       bottom_5_items: [{name, count}],
       peak_hours: [{hour: 0-23, order_count}],
       occupancy_rate_pct, avg_turn_time_minutes,
       vs_7day_avg: {revenue_delta_pct, order_count_delta_pct}
     }
     → NO PII. NO customer identifiers. Aggregated only.

  2. Call Anthropic Claude API (claude-haiku-3)
     System prompt: restaurant business advisor persona
     User message: JSON.stringify(metrics)
     Max tokens: 600 (input ~1400 + output ~600 = ~2000 total)

  3. Store in ai_briefings table:
     {restaurant_id, generated_at, content, model_used, tokens_used}

  4. Deliver:
     - Email via SendGrid (Premium, VIP, Luxury)
     - Display in Reception dashboard as dismissable card

  5. Error handling:
     - Claude API timeout/failure → log error, mark briefing as failed
     - Retry next scheduled run (do not retry immediately — avoid doubled charges)
     - Never display broken/partial briefing to admin
```

### 2.6 Subscription Billing Flow

```
Upgrade path:
  Admin → 'Upgrade Plan' → Reception → Settings → Subscription
  → Frontend calls POST /api/v1/billing/create-checkout
  → Backend creates Razorpay Subscription via API
  → Returns Razorpay hosted checkout URL
  → Frontend redirects (do not use redirect callback as source of truth — spoofable)

  Razorpay sends webhook: subscription.activated
  → POST /api/v1/webhooks/razorpay
  → Verify Razorpay webhook signature (HMAC-SHA256)
  → Check razorpay_event_id not already processed (idempotency)
  → Update restaurants.subscription_tier in DB
  → Write to audit_log
  → New limits take effect immediately

Payment failure dunning:
  Webhook: payment.failed
  → Mark restaurant as payment_overdue in DB
  → Day 0: Log event
  → Day 1, 3, 6: Celery scheduled tasks send email (SendGrid)
  → Day 7: Update subscription_tier = 'free'
  → Data preserved, access restricted per tier limits
  → Day 30: Flag for closure review
  → Day 90: Soft-delete account (data retained 90 more days then purged)
```

---

## 3. Database Design Decisions

### 3.1 Why PostgreSQL RLS Over Application-Only Scoping

Application-level scoping (checking `restaurant_id` in every query) is necessary but not sufficient. A single bug in a service method could expose cross-tenant data. RLS adds a mandatory second check at the DB level — even a fully compromised application server cannot read another restaurant's data.

RLS policy example (applied to all tenant-scoped tables):
```sql
CREATE POLICY restaurant_isolation ON orders
  USING (restaurant_id = current_setting('app.current_restaurant_id')::uuid);
```

The FastAPI service layer sets `app.current_restaurant_id` at the start of each request from the validated JWT claim.

### 3.2 Soft Deletes

All user-created entities use soft deletes (`is_deleted`, `deleted_at`) rather than hard deletes. Rationale:
- **Billing integrity:** Deleted menu items may still exist in historical orders. `unit_price_at_order` snapshot + soft delete ensures order history remains accurate.
- **DPDP compliance:** Account deletion flow needs to anonymize (not immediately purge) data, then purge after 90 days.
- **Downgrade policy:** A restaurant downgrading from Premium to Free retains all 200 menu items — 150 are hidden but not deleted.

### 3.3 Price Snapshotting

`order_items.unit_price_at_order` stores the price at the moment of order placement, not a foreign key to the current price. This means:
- Price changes do not retroactively affect placed orders
- Historical analytics remain accurate
- No complex price history table needed

### 3.4 Idempotency Keys

`POST /api/v1/orders` accepts an `Idempotency-Key` header. The server stores the key in Redis with a 24-hour TTL. On duplicate submission:
- Same key → return the original order (HTTP 200, not 201)
- Prevents double-orders from browser retries, slow networks, or duplicate taps

### 3.5 BIGSERIAL for audit_log

The `audit_log` table uses `BIGSERIAL` (integer auto-increment) instead of UUID for the primary key. At high volume (every order, every status change, every login attempt), UUID generation and storage overhead is non-trivial. Integer PKs are smaller, faster to index, and sequential — efficient for time-ordered audit queries.

---

## 4. Security Design

### 4.1 Token Architecture

```
Access JWT (15-min TTL):
  Header: {"alg": "HS256"}
  Payload: {
    "sub": "TBZ-240001",          // admin_id
    "restaurant_id": "uuid",
    "subscription_tier": "premium",
    "role": "admin",
    "iat": 1234567890,
    "exp": 1234568790             // iat + 900 seconds
  }
  Stored: Memory (React state) — never localStorage
  Transmitted: Authorization: Bearer {token} header

Refresh Token (30-day TTL):
  Format: cryptographically secure random string (128 chars)
  Stored: DB column + HttpOnly, Secure, SameSite=Strict cookie
  Rotated: on every use (new token issued, old token invalidated)

Customer Session Token:
  Format: cryptographically secure random string (128 chars)
  Stored: customer_sessions table + HttpOnly cookie
  TTL: 4 hours from creation (expires_at column)
```

### 4.2 Rate Limiting Design

Redis-backed rate limiting. Keys are scoped to prevent cross-restaurant interference:

| Endpoint Category | Key | Limit | Window |
|---|---|---|---|
| Auth (login/register) | `ratelimit:auth:{ip}` | 10 requests | 15 minutes |
| Login failures | `ratelimit:login_fail:{admin_id}` | 5 failures | 15 minutes |
| Order placement | `ratelimit:orders:{restaurant_id}:{session_id}` | 30 requests | 1 minute |
| Menu reads | `ratelimit:menu:{restaurant_id}` | 200 requests | 1 minute |
| Analytics | `ratelimit:analytics:{restaurant_id}` | 60 requests | 1 minute |
| Claude API (briefings) | `ratelimit:ai:{restaurant_id}` | 5 requests | 1 hour |

All rate limit responses return HTTP 429 with `Retry-After` header.

### 4.3 Input Sanitization

Every user-generated text field is sanitized before storage:
- `menu_items.description`: Bleach HTML sanitizer — strips all tags except `<b>`, `<i>`, `<em>`, `<strong>`
- `orders.special_requests`, `order_items.item_notes`: Plain text only, strip all HTML
- Phone numbers: E.164 format validation via `phonenumbers` library
- Prices: Pydantic `Decimal` type with `gt=0` constraint

---

## 5. Real-Time System Design

### 5.1 Channel Isolation

Each restaurant's WebSocket channel is namespaced: `restaurant:{restaurant_id}`. The server's WebSocket manager maintains a room registry:

```python
# Conceptual room structure
rooms = {
    "restaurant:uuid-1": {
        "reception": [ws_conn_1, ws_conn_2],
        "chef": [ws_conn_3],
        "customer": [ws_conn_4, ws_conn_5, ws_conn_6]
    },
    "restaurant:uuid-2": { ... }
}
```

Event broadcast is scoped to `restaurant:{id}` — events from Restaurant A physically cannot reach Restaurant B's WebSocket connections.

### 5.2 Event Ordering Guarantee

WebSocket events are not guaranteed to arrive in order (network conditions). To avoid stale UI states:
- All events include a `version` field (auto-incrementing per-restaurant sequence number stored in Redis)
- Clients that receive out-of-order events (version gap) call the REST API to fetch current state
- DB is always the source of truth; WS events are display optimizations, not state mutations

### 5.3 Chef Dashboard Resilience

The Chef dashboard operates under kitchen conditions (tablets with unstable WiFi, accidental power cycles). Design accommodates this:

- On any disconnect: cache current order queue in device memory
- On reconnect: `GET /api/v1/orders?status=pending,received,preparing` to rebuild full state from DB
- Heartbeat: server pings every 30 seconds, client pongs within 5 seconds or is considered disconnected
- Fallback: HTTP polling every 10 seconds if WS unavailable for > 30 seconds

---

## 6. Analytics System Design

### 6.1 Data Model

Analytics are computed on-demand from the `orders` and `order_items` tables using PostgreSQL aggregate queries. No separate analytics database or ETL pipeline in Phase 1–3. This is intentional — simplicity over premature optimization.

At Phase 4 scale (~50 concurrent restaurants), evaluate:
- Materialized views for common aggregates (refresh hourly)
- Separate read replica for analytics queries (avoid impacting OLTP performance)
- Potential migration to a columnar store if query complexity increases

### 6.2 Analytics Depth by Tier

| Tier | Date Range | Granularity | Export |
|---|---|---|---|
| Free | Last 7 days | Daily | No |
| Premium | Last 90 days | Daily | No |
| VIP | Last 1 year | Daily + Hourly | No |
| Luxury | Unlimited | Daily + Hourly + Per-order | CSV + PDF |

Analytics API enforces date range limits via `subscription_tier` check before executing queries.

### 6.3 AI Briefing Data Pipeline

```
AnalyticsService.get_briefing_metrics(restaurant_id, date):
  
  Queries (all scoped to restaurant_id + date):
  1. SUM(total_amount), COUNT(id), AVG(total_amount) FROM orders WHERE date = yesterday
  2. SUM(oi.quantity), SUM(oi.unit_price_at_order * oi.quantity) 
     FROM order_items oi JOIN menu_items mi
     GROUP BY mi.name ORDER BY quantity DESC LIMIT 5 (top) + ASC LIMIT 5 (bottom)
  3. COUNT(*) FROM orders GROUP BY EXTRACT(HOUR FROM placed_at)
  4. AVG(EXTRACT(EPOCH FROM (finalized_at - placed_at))/60) FROM orders WHERE finalized_at IS NOT NULL
  5. Compare all above to 7-day rolling average

  Output: Pure numeric JSON — no names, no addresses, no phone numbers, no session IDs
  → Sent to Anthropic Claude API as user message content
```

---

## 7. Error Handling Design

### 7.1 Error Response Contract

Every error response across all endpoints follows an identical structure:

```json
{
  "success": false,
  "error": {
    "code": "ORDER_INVALID_TRANSITION",
    "message": "Cannot transition order from 'served' to 'preparing'",
    "suggestion": "Order has already been served. To re-open, use the Reception dashboard to create a new order.",
    "http_status": 409,
    "request_id": "req_01HX...",
    "timestamp": "2025-01-15T14:32:00Z"
  }
}
```

`request_id` is generated per-request and logged in all server logs, enabling support tracing without exposing internal stack traces to clients.

### 7.2 Circuit Breaker Pattern

DB health monitor runs on a background thread:
- Tracks error rate over rolling 60-second window
- If error rate > 10%: opens circuit breaker
  - Read endpoints: return cached response (last known good state from Redis)
  - Write endpoints: return HTTP 503 with `Retry-After: 30`
- Alerts engineering team (PagerDuty / email)
- Circuit breaker closes automatically when error rate drops below 2% over 30 seconds

### 7.3 Idempotent Webhook Handling

All Razorpay webhook handlers check `razorpay_event_id` before processing:

```python
async def handle_subscription_charged(event_data):
    event_id = event_data["id"]
    
    # Idempotency check
    existing = await db.fetch_one(
        "SELECT id FROM processed_webhooks WHERE razorpay_event_id = :id",
        {"id": event_id}
    )
    if existing:
        return  # Already processed — do nothing
    
    # Process event
    await billing_service.record_payment(event_data)
    
    # Mark as processed
    await db.execute(
        "INSERT INTO processed_webhooks (razorpay_event_id, processed_at) VALUES (:id, now())",
        {"id": event_id}
    )
```

---

## 8. Load Testing Design

### 8.1 k6 Test Scenario

Target scenario: 50 concurrent restaurants, each with 10 active tables, all placing orders simultaneously for 10 minutes.

```javascript
// Simplified k6 scenario structure
export const options = {
  scenarios: {
    restaurant_simulation: {
      executor: 'constant-vus',
      vus: 500,  // 50 restaurants × 10 virtual users each
      duration: '10m',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<2000'],
    http_req_failed: ['rate<0.001'],  // < 0.1% error rate
    ws_session_duration: ['p(95)<300'],  // WebSocket message latency
  },
};
```

### 8.2 Performance Budget

| Component | Budget | Monitoring |
|---|---|---|
| Auth (login) | p95 < 200ms | Datadog APM |
| Menu fetch (cached) | p95 < 50ms | Datadog APM |
| Order placement | p95 < 500ms | Datadog APM |
| WS event broadcast | p95 < 300ms | Custom metric |
| DB query (99th pct) | < 100ms | Supabase metrics |
| AI briefing generation | < 30s (async, user not waiting) | Celery monitoring |

---

## 9. Local Deployment System Design

The LAN deployment mode is architecturally identical to cloud, packaged as Docker Compose.

```yaml
# Conceptual docker-compose.yml structure
services:
  frontend:
    image: tablz/frontend:latest
    ports: ["80:3000", "443:3000"]
  
  api:
    image: tablz/api:latest
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/tablz
      REDIS_URL: redis://redis:6379
      ENVIRONMENT: local
    depends_on: [db, redis]
  
  db:
    image: postgres:15
    volumes: ["postgres_data:/var/lib/postgresql/data"]
  
  redis:
    image: redis:7-alpine
  
  celery:
    image: tablz/api:latest
    command: celery -A app.celery worker -B
    depends_on: [api, redis]

volumes:
  postgres_data:
```

**Update mechanism:** Admin clicks 'Check for Updates' in Reception dashboard → backend calls update server → downloads new Docker image tags → performs rolling restart (`docker-compose pull && docker-compose up -d`) with health check validation before old containers are removed.

**Offline capability:** All core features (ordering, kitchen display, billing) work without internet. AI briefings, email notifications, and SMS require internet access and gracefully degrade when offline.

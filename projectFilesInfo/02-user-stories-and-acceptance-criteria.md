# 02 — User Stories & Acceptance Criteria
## TABLZ — AI-Powered Restaurant Management Platform

---

## Role Definitions

| Role | Description | Dashboard |
|------|-------------|-----------|
| **Restaurant Owner / Admin** | Registers the restaurant, manages menu/tables, views analytics, manages subscription | Reception Dashboard |
| **Customer** | Scans QR code at table, browses menu, places orders, views order status | Customer Dashboard (PWA) |
| **Chef / Kitchen Staff** | Receives real-time orders, updates order status through preparation lifecycle | Chef Dashboard |
| **Reception Staff** | Views orders, updates statuses, finalizes bills, manages table lifecycle | Reception Dashboard |
| **System** | Automated processes (Celery tasks, cron jobs, webhook handlers) | N/A |

---

## Epic 1 — Authentication & Registration

### US-1.1: Restaurant Registration
**As a** restaurant owner, **I want to** register my restaurant on TABLZ, **so that** I can start managing my restaurant digitally.

**Acceptance Criteria:**
- [ ] Owner provides: restaurant name, email, password
- [ ] System generates a unique `admin_id` in format `TBZ-YYXXXX` (e.g., TBZ-240001)
- [ ] Password is stored as bcrypt hash — never plaintext
- [ ] Verification email sent via SendGrid with a time-limited token (24h TTL)
- [ ] Account is created with `subscription_tier = 'free'` and `email_verified = false`
- [ ] Response: HTTP 201 with `admin_id`
- [ ] Duplicate email → HTTP 409 with `AUTH_DUPLICATE_EMAIL` error code

### US-1.2: Email Verification
**As a** restaurant owner, **I want to** verify my email address, **so that** I can access my account securely.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/verify-email/:token` validates the token
- [ ] Expired token (>24h) → HTTP 400 with `AUTH_TOKEN_EXPIRED`
- [ ] On success: `email_verified = true` in database
- [ ] Already verified token used again → HTTP 400 with `AUTH_ALREADY_VERIFIED`

### US-1.3: Admin Login
**As a** restaurant owner, **I want to** log in with my admin_id and password, **so that** I can access my dashboard.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/login` with `admin_id` + `password`
- [ ] Validates `email_verified = true` before issuing tokens
- [ ] Returns short-lived access JWT (15-min TTL) in response body
- [ ] Sets long-lived refresh token (30-day TTL) as HttpOnly, Secure, SameSite=Strict cookie
- [ ] JWT payload contains: `restaurant_id`, `admin_id`, `subscription_tier`, `role`, `iat`, `exp`
- [ ] Login event recorded in `audit_log`
- [ ] Unverified email → HTTP 403 with `AUTH_EMAIL_NOT_VERIFIED`
- [ ] Wrong credentials → HTTP 401 with `AUTH_INVALID_CREDENTIALS`

### US-1.4: Rate-Limited Login
**As the** system, **I want to** rate-limit login attempts, **so that** brute-force attacks are prevented.

**Acceptance Criteria:**
- [ ] After 5 failed login attempts for the same `admin_id` → HTTP 429 with `Retry-After: 900`
- [ ] Rate limit tracked in Redis with key `ratelimit:login_fail:{admin_id}`
- [ ] Counter resets after 15-minute lockout window
- [ ] Failed login attempts recorded in `audit_log`

### US-1.5: Token Refresh
**As a** logged-in user, **I want** my session to refresh transparently, **so that** I am not interrupted during active use.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/refresh` uses HttpOnly refresh cookie
- [ ] Returns new access JWT
- [ ] Rotates refresh token (old token invalidated, new token issued)
- [ ] Expired refresh token → HTTP 401

### US-1.6: Logout
**As a** restaurant owner, **I want to** log out securely, **so that** my session is terminated.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/logout` invalidates refresh token
- [ ] Clears HttpOnly cookie
- [ ] Subsequent refresh attempts fail with HTTP 401

---

## Epic 2 — Menu Management

### US-2.1: Create Menu Item
**As a** restaurant owner, **I want to** add items to my menu, **so that** customers can browse and order.

**Acceptance Criteria:**
- [ ] `POST /api/v1/menu` with: name, description, price, category, cuisine, dietary_type, prep_time_minutes
- [ ] `restaurant_id` extracted from JWT (never from request body)
- [ ] `price` must be > 0 (Pydantic validation)
- [ ] `category` enum: `appetizer`, `main`, `dessert`, `beverage`, `side`
- [ ] `dietary_type` enum: `vegetarian`, `non_vegetarian`, `vegan`, `contains_nuts`
- [ ] `description` sanitized via Bleach (strips dangerous HTML tags)
- [ ] Subscription tier limit enforced (Free: 50 items, Premium: 200, VIP: 500, Luxury: unlimited)
- [ ] Exceeding limit → HTTP 402 with `SUBSCRIPTION_LIMIT_EXCEEDED`
- [ ] Response: HTTP 201 with created menu item

### US-2.2: Update Menu Item
**As a** restaurant owner, **I want to** edit existing menu items, **so that** I can keep my menu accurate.

**Acceptance Criteria:**
- [ ] `PUT /api/v1/menu/:id` with updated fields
- [ ] Item must belong to authenticated restaurant (RLS enforced)
- [ ] Soft-deleted items cannot be updated → HTTP 404

### US-2.3: Toggle Availability
**As a** restaurant owner, **I want to** quickly toggle an item's availability, **so that** I can mark sold-out items without deleting them.

**Acceptance Criteria:**
- [ ] `PATCH /api/v1/menu/:id/availability` toggles `is_available`
- [ ] Unavailable items hidden from Customer dashboard
- [ ] Unavailable items still visible in Reception dashboard with visual indicator

### US-2.4: Soft-Delete Menu Item
**As a** restaurant owner, **I want to** remove an item from my menu, **so that** it no longer appears to customers.

**Acceptance Criteria:**
- [ ] `DELETE /api/v1/menu/:id` sets `is_deleted = true` and `deleted_at = now()`
- [ ] Never hard-deletes — preserves historical order integrity
- [ ] Deleted items excluded from all customer-facing queries
- [ ] Historical orders referencing deleted items retain correct `unit_price_at_order`

### US-2.5: Bulk CSV Import
**As a** VIP+ restaurant owner, **I want to** import menu items via CSV, **so that** I can onboard my existing menu quickly.

**Acceptance Criteria:**
- [ ] `POST /api/v1/menu/bulk-import` accepts CSV file upload
- [ ] Available only for VIP and Luxury tiers
- [ ] Validates each row against Pydantic schema
- [ ] Returns a summary: items created, items failed (with row numbers and error details)

---

## Epic 3 — Table Management

### US-3.1: Create Table
**As a** restaurant owner, **I want to** add tables to my restaurant, **so that** customers can be seated and scan QR codes.

**Acceptance Criteria:**
- [ ] `POST /api/v1/tables` with: `table_number`, `max_capacity`, `is_expandable`
- [ ] System generates `qr_code_token` (128 chars via `secrets.token_urlsafe(96)`)
- [ ] QR image generated (Python `qrcode` lib) and uploaded to S3
- [ ] QR scan URL: `{BASE_URL}/t/{qr_code_token}`
- [ ] Subscription tier limit enforced (Free: 10, Premium: 30, VIP: 75, Luxury: unlimited)
- [ ] Duplicate table_number within same restaurant → HTTP 409

### US-3.2: Table Status Lifecycle
**As** reception staff, **I want to** manage the table lifecycle, **so that** I can track occupancy in real-time.

**Acceptance Criteria:**
- [ ] Status transitions: `available` → `occupied` → `cleaning` → `available`
- [ ] `occupied` set automatically when first QR scan creates a customer session
- [ ] `POST /api/v1/tables/:id/clean` sets status to `cleaning` and updates `last_cleaned_at`
- [ ] Confirmation of cleaning sets status back to `available`

### US-3.3: Table Merge
**As a** customer (table owner), **I want to** merge my table with an adjacent empty table, **so that** our entire party can order on a single bill.

**Acceptance Criteria:**
- [ ] `POST /api/v1/tables/:id/merge` with `merge_with_table_id`
- [ ] Only `is_table_owner = true` session can initiate merge
- [ ] Target table must be in `available` status
- [ ] Subscription check: Premium: max 3 merges, VIP: max 5, Luxury: unlimited, Free: no merge
- [ ] Merged table status → `merged`, `merged_into_table_id` set to parent table
- [ ] All orders from merged table routed to parent table's bill
- [ ] On bill finalization: all merged tables released, `merged_into_table_id` cleared

### US-3.4: Regenerate QR Code
**As a** restaurant owner, **I want to** regenerate a table's QR code, **so that** I can invalidate old printed QR codes.

**Acceptance Criteria:**
- [ ] `GET /api/v1/tables/:id/qr` regenerates token and returns new QR image URL
- [ ] Old QR token invalidated — all existing sessions for that table invalidated
- [ ] New QR image uploaded to S3

---

## Epic 4 — Customer Ordering

### US-4.1: QR Scan → Session Creation
**As a** customer, **I want to** scan a QR code at my table, **so that** I can start browsing the menu and ordering.

**Acceptance Criteria:**
- [ ] `POST /api/v1/auth/qr-session` validates `qr_code_token`
- [ ] Creates `customer_session` row with `session_token` (HttpOnly cookie)
- [ ] First scanner at table → `is_table_owner = true`
- [ ] Subsequent scanners → `is_table_owner = false` (join group session)
- [ ] Table status updated to `occupied`
- [ ] Session expires after 4 hours (`expires_at`)
- [ ] Invalid/expired QR token → HTTP 404 `RESOURCE_NOT_FOUND`
- [ ] Table in `cleaning` or `reserved` status → HTTP 409

### US-4.2: Browse Menu
**As a** customer, **I want to** browse the restaurant's menu, **so that** I can choose what to order.

**Acceptance Criteria:**
- [ ] `GET /api/v1/menu` returns items where `is_available = true` AND `is_deleted = false`
- [ ] Menu scoped to customer's restaurant via session token
- [ ] Filterable by: `category`, `dietary_type`, `cuisine`
- [ ] Each item includes: name, description, price, image_url, prep_time_minutes, dietary_type

### US-4.3: Place Order
**As a** customer, **I want to** place an order from my table, **so that** the kitchen starts preparing my food.

**Acceptance Criteria:**
- [ ] `POST /api/v1/orders` with `items: [{menu_item_id, quantity, item_notes}]`
- [ ] Accepts `Idempotency-Key` header — same key returns original order (HTTP 200, not 201)
- [ ] All item `restaurant_id` values validated against session's restaurant (prevents cross-restaurant injection → HTTP 404)
- [ ] `unit_price_at_order` snapshotted at time of order (not FK to current price)
- [ ] `total_amount` computed server-side (sum of item prices × quantities)
- [ ] `tax_amount` computed from active `tax_configurations`
- [ ] Order written to DB → then WebSocket `order.created` broadcast
- [ ] Audit log entry written
- [ ] Response: HTTP 201 with order details

### US-4.4: View Order Status
**As a** customer, **I want to** see real-time updates on my order, **so that** I know when my food is being prepared and ready.

**Acceptance Criteria:**
- [ ] `GET /api/v1/orders` returns orders scoped to customer's table session
- [ ] WebSocket `order.status_changed` events update UI in real-time
- [ ] Status display: pending → received → preparing → ready → served

---

## Epic 5 — Chef Dashboard

### US-5.1: Real-Time Order Queue
**As a** chef, **I want to** see new orders appear instantly, **so that** I can start preparing them without delay.

**Acceptance Criteria:**
- [ ] WebSocket `order.created` events populate order queue in real-time
- [ ] Orders displayed with: table number, items, quantities, special requests, prep time
- [ ] On WS disconnect: cache current queue in device memory
- [ ] On WS reconnect: rebuild queue from `GET /api/v1/orders?status=pending,received,preparing`
- [ ] Fallback: HTTP polling every 10 seconds if WS unavailable >30 seconds

### US-5.2: Update Order Status
**As a** chef, **I want to** update order status as I work, **so that** customers and reception can see progress.

**Acceptance Criteria:**
- [ ] `PATCH /api/v1/orders/:id/status` with `{status: 'received' | 'preparing' | 'ready'}`
- [ ] Server-enforced state machine: `pending → received → preparing → ready → served`
- [ ] Invalid transition → HTTP 409 `ORDER_INVALID_TRANSITION`
- [ ] Status change broadcasts `order.status_changed` via WebSocket
- [ ] Only admin/staff roles can cancel (`any state → cancelled`)

---

## Epic 6 — Billing & Finalization

### US-6.1: Finalize Bill
**As** reception staff, **I want to** finalize a table's bill, **so that** I can collect payment and reset the table.

**Acceptance Criteria:**
- [ ] `POST /api/v1/orders/:id/finalize` locks the order (`is_finalized = true`)
- [ ] Validates all items are `served` or explicitly `cancelled`
- [ ] Generates `barcode_token` (unique)
- [ ] Generates barcode PDF and uploads to S3
- [ ] Returns barcode URL for printing
- [ ] Sets `finalized_at` timestamp
- [ ] Broadcasting `order.finalized` event via WebSocket

### US-6.2: Table Reset
**As** reception staff, **I want to** reset a table after bill payment, **so that** it's available for the next customer.

**Acceptance Criteria:**
- [ ] All `customer_sessions` for the table are invalidated (`invalidated_at = now()`)
- [ ] `tables.status` set to `available` or `cleaning`
- [ ] `tables.owner_session_id` set to NULL
- [ ] If merged tables exist: all `merged_into_table_id` cleared, merged tables set to `available`
- [ ] `table.status_changed` event broadcast via WebSocket

---

## Epic 7 — Analytics

### US-7.1: Revenue Summary
**As a** restaurant owner, **I want to** see my revenue summary, **so that** I can track daily performance.

**Acceptance Criteria:**
- [ ] `GET /api/v1/analytics/summary` returns: daily revenue, order count, avg order value
- [ ] Date range limited by subscription tier (Free: 7 days, Premium: 90 days, VIP: 1 year, Luxury: unlimited)
- [ ] Data scoped to `restaurant_id` from JWT

### US-7.2: Popular Items
**As a** restaurant owner, **I want to** see my most popular items, **so that** I can optimize my menu.

**Acceptance Criteria:**
- [ ] `GET /api/v1/analytics/popular-items` returns top 10 items by order count
- [ ] Includes: item name, order count, total revenue generated

### US-7.3: Table Occupancy
**As a** restaurant owner, **I want to** see table utilization metrics, **so that** I can optimize seating arrangements.

**Acceptance Criteria:**
- [ ] `GET /api/v1/analytics/occupancy` returns table occupancy rate (% of time occupied)
- [ ] Includes average table turn time (first order to bill finalization)

### US-7.4: Peak Hours (VIP+)
**As a** VIP/Luxury restaurant owner, **I want to** see peak hour data, **so that** I can optimize staffing.

**Acceptance Criteria:**
- [ ] `GET /api/v1/analytics/peak-hours` returns order count distribution by hour
- [ ] Available only for VIP and Luxury tiers → else HTTP 402

### US-7.5: Analytics Export (Luxury)
**As a** Luxury restaurant owner, **I want to** export analytics data, **so that** I can use it in external tools.

**Acceptance Criteria:**
- [ ] `GET /api/v1/analytics/export` returns CSV/PDF report
- [ ] Available only for Luxury tier → else HTTP 402

---

## Epic 8 — Subscription Management

### US-8.1: Upgrade Subscription
**As a** restaurant owner, **I want to** upgrade my subscription, **so that** I can access more features.

**Acceptance Criteria:**
- [ ] Admin clicks 'Upgrade Plan' → redirected to Razorpay hosted checkout
- [ ] On success: `subscription.activated` webhook received
- [ ] `subscription_tier` updated in DB immediately
- [ ] New limits take effect immediately
- [ ] Prorated billing handled by Razorpay

### US-8.2: Downgrade Subscription
**As a** restaurant owner, **I want to** downgrade my subscription, **so that** I can reduce costs.

**Acceptance Criteria:**
- [ ] Downgrade takes effect at end of current billing cycle (not immediately)
- [ ] `scheduled_tier` set in DB, current tier remains active until period end
- [ ] 7 days before effective date: email warning sent listing restrictions
- [ ] On effective date: limits enforced but **data is NOT deleted** — only access restricted
- [ ] Items surface again on re-upgrade

### US-8.3: Payment Failure / Dunning
**As the** system, **I want to** handle payment failures gracefully, **so that** restaurants are not abruptly cut off.

**Acceptance Criteria:**
- [ ] Day 0: `payment.failed` webhook → mark `payment_overdue`, grace period begins
- [ ] Day 1: Email — "Your payment failed"
- [ ] Day 3: Email — "Action required — 4 days until restriction"
- [ ] Day 6: Email + SMS — "Final notice"
- [ ] Day 7: Tier downgraded to Free, admin notified, data preserved
- [ ] Day 30: Account flagged for closure review
- [ ] Day 90: Account soft-deleted, data retained 90 more days then purged

---

## Epic 9 — Reservations (Phase 3)

### US-9.1: Create Reservation
**As** reception staff, **I want to** create a reservation for a future guest, **so that** their table is held.

**Acceptance Criteria:**
- [ ] `POST /api/v1/reservations` with: guest_name, guest_phone, party_size, reserved_at, table_id (optional), notes
- [ ] Phone number validated in E.164 format
- [ ] If table_id provided: table's status set to `reserved` at the reserved time
- [ ] Status lifecycle: `pending → confirmed → seated → no_show → cancelled`

---

## Epic 10 — DPDP Compliance

### US-10.1: Data Export
**As a** restaurant owner, **I want to** export all my data, **so that** I can exercise my right to access under DPDP.

**Acceptance Criteria:**
- [ ] `GET /api/v1/account/data-export` returns all restaurant data as JSON
- [ ] Delivered within 72 hours
- [ ] Includes: restaurant info, menu items, orders, table configs, analytics

### US-10.2: Account Deletion
**As a** restaurant owner, **I want to** delete my account, **so that** I can exercise my right to erasure.

**Acceptance Criteria:**
- [ ] `DELETE /api/v1/account` soft-deletes account
- [ ] PII anonymized within 30 days
- [ ] Financial records retained for 7 years (legal obligation)
- [ ] All sessions invalidated immediately

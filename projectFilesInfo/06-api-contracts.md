# 06 — API Contracts
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. API Conventions

- **Base URL:** `https://tablz.app/api/v1`
- **Content-Type:** `application/json`
- **Auth:** JWT via `Authorization: Bearer {token}` or session token via HttpOnly cookie
- **Versioning:** URL path prefix (`/api/v1/`)
- **Idempotency:** `POST /orders` accepts `Idempotency-Key` header (UUID)

### Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human readable description",
    "suggestion": "What to do next",
    "http_status": 400,
    "request_id": "req_uuid",
    "timestamp": "2025-01-15T14:32:00Z"
  }
}
```

### Error Codes

| Code | HTTP | When Used |
|------|------|-----------|
| AUTH_TOKEN_EXPIRED | 401 | JWT or session token past expiry |
| AUTH_INVALID_CREDENTIALS | 401 | Wrong admin_id or password |
| AUTH_EMAIL_NOT_VERIFIED | 403 | Email not yet verified |
| AUTH_INSUFFICIENT_ROLE | 403 | Role cannot access endpoint |
| RESOURCE_NOT_FOUND | 404 | ID doesn't exist or belongs to other restaurant |
| ORDER_DUPLICATE | 409 | Idempotency key already used |
| ORDER_INVALID_TRANSITION | 409 | Invalid status change |
| SUBSCRIPTION_LIMIT_EXCEEDED | 402 | Tier limit reached |
| RATE_LIMIT_EXCEEDED | 429 | Rate limit hit (Retry-After header) |
| VALIDATION_ERROR | 422 | Pydantic validation failed |
| INTERNAL_ERROR | 500 | Unexpected server error |
| SERVICE_UNAVAILABLE | 503 | DB circuit breaker open |

---

## 2. Authentication Endpoints

### POST /auth/register
Create a new restaurant account.

**Auth:** None  
**Request:**
```json
{
  "name": "Spice Garden",
  "email": "owner@spicegarden.in",
  "password": "SecureP@ss123"
}
```
**Response (201):**
```json
{
  "success": true,
  "data": {
    "admin_id": "TBZ-250001",
    "email": "owner@spicegarden.in",
    "message": "Verification email sent"
  }
}
```

### POST /auth/verify-email/:token
**Auth:** None  
**Response (200):** `{ "success": true, "message": "Email verified" }`

### POST /auth/login
**Auth:** None  
**Request:**
```json
{ "admin_id": "TBZ-250001", "password": "SecureP@ss123" }
```
**Response (200):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbG...",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```
**Side effect:** Sets `refresh_token` as HttpOnly, Secure, SameSite=Strict cookie.

### POST /auth/refresh
**Auth:** Refresh token (HttpOnly cookie)  
**Response (200):** Same as login. Old refresh token invalidated, new one set.

### POST /auth/qr-session
**Auth:** QR token in body  
**Request:** `{ "qr_code_token": "abc123..." }`  
**Response (201):**
```json
{
  "success": true,
  "data": {
    "table_id": "uuid",
    "table_number": 5,
    "restaurant_name": "Spice Garden",
    "is_table_owner": true
  }
}
```
**Side effect:** Sets `session_token` as HttpOnly cookie. Updates table status to `occupied`.

### POST /auth/logout
**Auth:** JWT  
**Response (200):** `{ "success": true }`

### POST /auth/forgot-password
**Auth:** None  
**Request:** `{ "email": "owner@spicegarden.in" }`  
**Response (200):** `{ "success": true, "message": "If email exists, reset link sent" }`

### POST /auth/reset-password
**Auth:** Reset token  
**Request:** `{ "token": "...", "new_password": "NewP@ss456" }`  
**Response (200):** `{ "success": true }`

---

## 3. Menu Endpoints

### GET /menu
**Auth:** JWT or Session token  
**Query params:** `category`, `dietary_type`, `cuisine`, `page`, `limit`  
**Response (200):**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "Paneer Tikka",
        "description": "Grilled cottage cheese",
        "price": 349.00,
        "category": "appetizer",
        "cuisine": "North Indian",
        "dietary_type": "vegetarian",
        "is_available": true,
        "is_daily_special": false,
        "image_url": "https://cdn.tablz.app/...",
        "prep_time_minutes": 20
      }
    ],
    "total": 45,
    "page": 1,
    "limit": 20
  }
}
```

### POST /menu
**Auth:** JWT (Reception)  
**Request:**
```json
{
  "name": "Butter Chicken",
  "description": "Rich tomato-based curry",
  "price": 449.00,
  "category": "main",
  "cuisine": "North Indian",
  "dietary_type": "non_vegetarian",
  "prep_time_minutes": 25
}
```
**Response (201):** Created menu item.

### PUT /menu/:id
**Auth:** JWT (Reception)  
**Request:** Same fields as POST (partial update).  
**Response (200):** Updated menu item.

### PATCH /menu/:id/availability
**Auth:** JWT (Reception)  
**Request:** `{ "is_available": false }`  
**Response (200):** Updated item.

### DELETE /menu/:id
**Auth:** JWT (Reception)  
**Response (200):** `{ "success": true }` — sets `is_deleted = true`.

### POST /menu/bulk-import
**Auth:** JWT (Reception, VIP+)  
**Request:** `multipart/form-data` with CSV file.  
**Response (200):**
```json
{
  "success": true,
  "data": { "created": 45, "failed": 3, "errors": [...] }
}
```

---

## 4. Table Endpoints

### GET /tables
**Auth:** JWT  
**Response (200):** Array of tables with status, capacity, QR info.

### POST /tables
**Auth:** JWT (Reception)  
**Request:** `{ "table_number": 12, "max_capacity": 6, "is_expandable": false }`  
**Response (201):** Created table with QR code URL.

### POST /tables/:id/merge
**Auth:** Customer session (owner only)  
**Request:** `{ "merge_with_table_id": "uuid" }`  
**Response (200):** `{ "success": true, "merged_tables": [5, 8] }`

### POST /tables/:id/clean
**Auth:** JWT (Reception)  
**Response (200):** Sets status to `cleaning`, updates `last_cleaned_at`.

### GET /tables/:id/qr
**Auth:** JWT (Reception)  
**Response (200):** `{ "qr_image_url": "https://cdn.tablz.app/qr/...", "qr_code_token": "..." }`

---

## 5. Order Endpoints

### POST /orders
**Auth:** Customer session  
**Headers:** `Idempotency-Key: {uuid}` (optional)  
**Request:**
```json
{
  "items": [
    { "menu_item_id": "uuid", "quantity": 2, "item_notes": "extra spicy" },
    { "menu_item_id": "uuid", "quantity": 1 }
  ],
  "special_requests": "Birthday celebration"
}
```
**Response (201):**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "pending",
    "items": [...],
    "total_amount": 1147.00,
    "tax_amount": 206.46,
    "placed_at": "2025-01-15T14:32:00Z"
  }
}
```

### GET /orders
**Auth:** JWT or Session  
**Query params:** `status`, `table_id`, `page`, `limit`  
**Response (200):** Paginated list of orders.

### PATCH /orders/:id/status
**Auth:** JWT (Chef/Reception)  
**Request:** `{ "status": "preparing" }`  
**Response (200):** Updated order.  
**Error (409):** `ORDER_INVALID_TRANSITION` on invalid state change.

### POST /orders/:id/finalize
**Auth:** JWT (Reception)  
**Response (200):**
```json
{
  "success": true,
  "data": {
    "barcode_url": "https://cdn.tablz.app/barcodes/...",
    "barcode_token": "...",
    "total_amount": 1147.00,
    "tax_amount": 206.46,
    "finalized_at": "2025-01-15T15:45:00Z"
  }
}
```

---

## 6. Analytics Endpoints

### GET /analytics/summary
**Auth:** JWT  
**Query params:** `start_date`, `end_date` (tier-enforced range)  
**Response (200):**
```json
{
  "data": {
    "daily_revenue": 45200.00,
    "order_count": 87,
    "avg_order_value": 519.54
  }
}
```

### GET /analytics/popular-items
**Auth:** JWT  
**Response (200):** Top 10 items by order count.

### GET /analytics/occupancy
**Auth:** JWT  
**Response (200):** `{ "occupancy_rate_pct": 72.5, "avg_turn_time_minutes": 45 }`

### GET /analytics/peak-hours
**Auth:** JWT (VIP+)  
**Response (200):** Array of `{ "hour": 0-23, "order_count": N }`.

### GET /analytics/export
**Auth:** JWT (Luxury only)  
**Response:** CSV or PDF file download.

---

## 7. Other Endpoints

### Reservations
- `GET /reservations` — List (JWT)
- `POST /reservations` — Create (JWT)
- `PATCH /reservations/:id` — Update status (JWT)

### Tax Config
- `GET /tax-configs` — List active configs (JWT)
- `POST /tax-configs` — Create config (JWT)

### Webhooks
- `POST /webhooks/razorpay` — Razorpay webhook handler (signature verified)
- `GET /webhooks` — List registered webhooks (JWT, Luxury)
- `POST /webhooks` — Register webhook URL (JWT, Luxury)

### AI Briefings
- `GET /ai/briefing` — Latest briefing (JWT, Premium+)

### Account / DPDP
- `GET /account/data-export` — Export all data (JWT)
- `DELETE /account` — Request account deletion (JWT)

---

## 8. WebSocket Protocol

**Endpoint:** `WS /ws/{restaurant_id}`  
**Auth:** JWT or session token in connection headers.

### Event Types

| Event | Direction | Payload |
|-------|-----------|---------|
| `order.created` | Server → Client | Full order object |
| `order.status_changed` | Server → Client | `{ order_id, old_status, new_status }` |
| `order.finalized` | Server → Client | `{ order_id, barcode_url }` |
| `table.status_changed` | Server → Client | `{ table_id, old_status, new_status }` |
| `token_expiring_soon` | Server → Client | `{ expires_in_seconds: 120 }` |
| `session_expired` | Server → Client | WS close code 4001 |
| `reauth` | Client → Server | `{ token: "new_jwt" }` |

### Connection Recovery
- Heartbeat: server pings every 30s
- 3 missed pings → client reconnects
- Exponential backoff: 1s, 2s, 4s, 8s, max 30s
- Fallback: HTTP polling every 10s on `GET /orders`

---

## 9. Rate Limits

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Auth (login/register) | 10 req | 15 min |
| Login failures | 5 failures | 15 min |
| Order placement | 30 req | 1 min |
| Menu reads | 200 req | 1 min |
| Analytics | 60 req | 1 min |
| Claude API (briefings) | 5 req | 1 hour |

All 429 responses include `Retry-After` header.

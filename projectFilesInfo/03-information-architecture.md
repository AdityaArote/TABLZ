# 03 — Information Architecture
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Application Map

```
TABLZ Platform
├── Reception Dashboard (Admin / Staff)
│   ├── Login / Registration
│   ├── Dashboard Home (Overview)
│   ├── Menu Management
│   ├── Table Management
│   ├── Order Management
│   ├── Reservations (Phase 3)
│   ├── Analytics
│   ├── AI Briefings (Premium+)
│   └── Settings (Account, Subscription, Tax, Staff, Webhooks)
│
├── Customer Dashboard (PWA — Guest)
│   ├── QR Scan Landing → /t/{qr_token}
│   ├── Menu Browser (category/dietary filters)
│   ├── Cart / Order Placement
│   ├── Order Status (Live via WS)
│   └── Bill View
│
├── Chef Dashboard (Kitchen Staff)
│   └── Single-Screen Order Queue
│       ├── Pending | Preparing | Ready tabs
│       └── Order Detail / Status Update
│
└── Backend API (FastAPI)
    ├── Auth, Menu, Table, Order, Analytics Routes
    ├── Reservation, Billing, Webhook, AI Briefing Routes
    └── WebSocket Manager
```

---

## 2. Navigation Architecture

### 2.1 Reception Dashboard

| Nav Item | Route | Description |
|----------|-------|-------------|
| Dashboard | `/` | Today's stats, recent orders, AI briefing card |
| Menu | `/menu` | CRUD, availability toggles, bulk import |
| Tables | `/tables` | Grid map with status colors, QR management |
| Orders | `/orders` | Active orders, finalization controls |
| Reservations | `/reservations` | List, creation, status updates (Phase 3) |
| Analytics | `/analytics` | Revenue, popular items, occupancy, peak hours |
| Settings | `/settings` | Account, subscription, tax, staff, webhooks |

### 2.2 Customer Dashboard — Flow-Based

```
QR Scan → Menu Browse → Cart → Order Placed → Status View → Bill
```

| Screen | Route | Auth |
|--------|-------|------|
| Landing | `/t/{qr_token}` | QR token |
| Menu | `/menu` | Session token |
| Cart | `/cart` | Session token |
| Orders | `/orders` | Session token |
| Bill | `/bill` | Session token |

### 2.3 Chef Dashboard — Single-Screen

Optimized for kitchen tablets. Single view with Pending / Preparing / Ready order cards and one-tap status transitions.

---

## 3. Data Flow — Order Lifecycle

```
Customer Device          Backend API              Chef Device
     │── POST /orders ──►│                        │
     │                   ├── Write DB + audit_log  │
     │                   ├── WS: order.created ───►│
     │◄── HTTP 201 ──────┤                        │
     │                   │◄── PATCH /status ───────┤
     │◄── WS: changed ──┤── WS: changed ─────────►│
     │                   │◄── POST /finalize ──────(Reception)
     │◄── WS: finalized──┤
```

---

## 4. Content Hierarchies

### Menu Item
- **Identity:** name, description (sanitized HTML), image_url
- **Classification:** category (5 enums), cuisine (free-text), dietary_type (4 enums)
- **Pricing:** price (> 0), currency (inherited)
- **Operations:** is_available, is_daily_special, is_weekly_special, prep_time_minutes
- **Lifecycle:** is_deleted, deleted_at

### Order
- **Identity:** id, restaurant_id, table_id, session_id
- **Items[]:** menu_item_id, quantity, unit_price_at_order (snapshot), item_notes
- **Financial:** total_amount, tax_config_id, tax_amount
- **Status:** pending → received → preparing → ready → served | cancelled
- **Billing:** is_finalized, barcode_token, finalized_at

### Table
- **Identity:** id, restaurant_id, table_number
- **Status:** available | occupied | merged | cleaning | reserved
- **QR:** qr_code_token (128 chars), qr_code_url
- **Config:** max_capacity, is_expandable, owner_session_id, merged_into_table_id

---

## 5. API URL Structure

```
/api/v1/
├── auth/ (register, login, refresh, logout, qr-session, verify-email, forgot/reset-password)
├── menu/ (CRUD, :id/availability, bulk-import)
├── tables/ (CRUD, :id/merge, :id/clean, :id/qr)
├── orders/ (CRUD, :id/status, :id/finalize)
├── reservations/ (CRUD, :id)
├── analytics/ (summary, popular-items, occupancy, peak-hours, table-turnaround, export)
├── tax-configs/ (list, create)
├── webhooks/ (razorpay, list, register)
├── ai/briefing
└── account/ (data-export, delete)
```

---

## 6. State Management

| State | Storage | Scope |
|-------|---------|-------|
| Access JWT | React memory | Never persisted, 15-min TTL |
| Refresh Token | HttpOnly cookie | Browser-managed, 30-day TTL |
| Session Token | HttpOnly cookie | Customer, 4h TTL |
| Chef Order Queue | In-memory cache | Cached on disconnect, rebuilt from DB on reconnect |
| Rate Limits | Redis | Per-endpoint sliding window |
| Idempotency Keys | Redis | 24h TTL |
| WS Rooms | FastAPI in-memory | Connection lifetime |

---

## 7. Access Control Matrix

| Resource | Admin | Reception | Chef | Customer (Owner) | Customer (Guest) |
|----------|-------|-----------|------|-------------------|-------------------|
| Menu CRUD | ✅ | ✅ | ❌ | ❌ | ❌ |
| Menu Read | ✅ | ✅ | ✅ | ✅ | ✅ |
| Table CRUD | ✅ | ✅ | ❌ | ❌ | ❌ |
| Table Merge | ❌ | ❌ | ❌ | ✅ | ❌ |
| Place Order | ❌ | ❌ | ❌ | ✅ | ✅ |
| Update Status | ✅ | ✅ | ✅ | ❌ | ❌ |
| Finalize Bill | ✅ | ✅ | ❌ | ❌ | ❌ |
| Cancel Order | ✅ | ✅ | ❌ | ❌ | ❌ |
| Analytics | ✅ | ✅ | ❌ | ❌ | ❌ |
| Subscription | ✅ | ❌ | ❌ | ❌ | ❌ |
| Data Export | ✅ | ❌ | ❌ | ❌ | ❌ |

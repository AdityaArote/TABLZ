# TABLZ — Phase 1 Complete Walkthrough

## Summary

Phase 1 (Weeks 1–4) of the TABLZ backend is fully implemented. All services, routers, models, and real-time infrastructure are in place.

---

## Backend Architecture

```
backend/app/
├── main.py              ← FastAPI app factory, CORS, lifespan, 6 routers
├── config.py            ← pydantic-settings, all config from env
├── database.py          ← SQLAlchemy async engine (pool_size=20)
├── deps.py              ← DI: get_db, get_current_restaurant (JWT), get_current_session (cookie)
│
├── core/
│   ├── security.py      ← JWT (HS256/15min), bcrypt, token generators
│   ├── errors.py        ← 12 error codes, AppException, standard error format
│   ├── rate_limit.py    ← Redis-backed rate limiting + idempotency keys
│   └── websocket_manager.py ← Room-based WS with heartbeat + token refresh
│
├── models/              ← 9 SQLAlchemy ORM models
│   ├── restaurant.py    ← Core tenant entity (admin_id, auth fields)
│   ├── table.py         ← QR tokens, status lifecycle, merge refs
│   ├── menu_item.py     ← Soft-delete, daily/weekly specials
│   ├── order.py         ← Server-enforced state machine
│   ├── order_item.py    ← Price snapshot at order time
│   ├── customer_session.py ← 4h TTL, table owner tracking
│   ├── audit_log.py     ← Immutable, BIGSERIAL PK
│   ├── tax_config.py    ← Per-restaurant tax rules
│   └── staff.py         ← PIN-based auth (Phase 3)
│
├── schemas/             ← Pydantic v2 request/response models
│   ├── auth.py, menu.py, table.py, order.py, common.py
│
├── services/            ← Business logic layer
│   ├── auth_service.py      ← Register, login (rate-limited), token rotation
│   ├── menu_service.py      ← CRUD, bleach sanitization, tier limits
│   ├── table_service.py     ← QR generation, status transitions, cleaning
│   ├── order_service.py     ← Idempotency, price snapshot, state machine, finalize
│   ├── session_service.py   ← QR scan → session (no login, 4h TTL)
│   └── analytics_service.py ← Revenue, popular items, occupancy (tier-enforced)
│
└── routers/             ← API endpoints
    ├── auth.py          ← 5 endpoints (register, verify, login, refresh, logout)
    ├── menu.py          ← 5 endpoints (list, get, create, update, delete)
    ├── tables.py        ← 4 endpoints (list, get, create, clean, QR)
    ├── orders.py        ← 6 endpoints (QR session, create, list, get, status, finalize)
    ├── analytics.py     ← 3 endpoints (summary, popular items, occupancy)
    └── websocket.py     ← WS /ws/{restaurant_id} with JWT auth protocol
```

## Key Security Features

| Feature | Implementation |
|---------|---------------|
| JWT Access Token | HS256, 15-min TTL, `restaurant_id` in claims |
| Refresh Token | Cryptographic random, HttpOnly cookie, 30-day TTL |
| Tenant Isolation | `restaurant_id` always from JWT, never from request body |
| Rate Limiting | 5 login failures → 15-min lockout (Redis) |
| Idempotency | `Idempotency-Key` header → Redis with 24h TTL |
| Input Sanitization | bleach on all text inputs |
| Order State Machine | Server-enforced: pending → received → preparing → ready → served |

## 5. Next.js Customer Web App (Phase 3)
Built in `frontend/apps/customer-app`. This is the user-facing digital menu accessed via QR scan link.
*   **QR Flow & Sessions:** The magic link (e.g., `/scan?token=abc&t=123`) activates the Customer Session via a Server Action, issuing a secure `HttpOnly` cookie.
*   **Stateful Menu & Cart:** Zustand is used to persist the user's cart (Item -> Quantity -> Price lookup) natively prior to checkout.
*   **Checkout & Barcode:** Submitting an order hits `/api/v1/orders`. On success, users see an algorithmically generated Barcode UI reflecting their Session/Order ID.

## 6. Real-time Chef Dashboard (Phase 4)
Built in `frontend/apps/chef-dashboard`. This is the high-voltage Kanban board for the kitchen.
*   **WebSocket Engine (`useWebSocket`):** Maintains a persistent event-driven connection to the FastAPI `ws_manager`. Upon `order.created` broadcast, the ticket queues up in the UI optimisticly, without page refresh.
*   **State Machine Pipeline:** Staff easily bounce ticket state (`Pending` -> `Preparing` -> `Ready`) using one-click REST actions, which are subsequently synced across all connected clients via WS diffs.
*   **Status Indicators:** Features a live pulsing green connection orb indicating uplink health to the kitchen staff.

---

### Conclusion
The **TABLZ Platform** is fully implemented using the required Midnight Luxe design aesthetic across three independent frontends, integrated harmoniously into a scalable FastAPI backend architecture.

## Frontend Designs (Stitch MCP)

Stitch project `10629934886619244318` with **"Reserve Noir"** design system:
- Reception Login (Desktop)
- Reception Dashboard (Desktop)
- Customer Menu Browse (Mobile)
- Chef Order Queue (Desktop)

## Infrastructure

- `docker-compose.yml` — PostgreSQL 15 + Redis 7
- `Dockerfile` — Python 3.11-slim
- `requirements.txt` — 16 dependencies
- `.env.example` — all config variables documented

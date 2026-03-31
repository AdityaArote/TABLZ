# 07 — Monorepo Structure
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Repository Layout

```
tablz/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app factory + lifespan events
│   │   ├── config.py               # Settings via pydantic-settings (all from env vars)
│   │   ├── database.py             # SQLAlchemy async engine + session factory
│   │   ├── deps.py                 # Dependency injection (get_current_restaurant, get_db, etc.)
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── restaurant.py       # Restaurant model
│   │   │   ├── table.py            # Table model
│   │   │   ├── menu_item.py        # MenuItem model
│   │   │   ├── order.py            # Order model
│   │   │   ├── order_item.py       # OrderItem model
│   │   │   ├── customer_session.py # CustomerSession model
│   │   │   ├── reservation.py      # Reservation model (Phase 3)
│   │   │   ├── tax_config.py       # TaxConfiguration model
│   │   │   ├── staff.py            # Staff model (Phase 3)
│   │   │   ├── audit_log.py        # AuditLog model
│   │   │   ├── ai_briefing.py      # AIBriefing model (Phase 4)
│   │   │   └── processed_webhook.py # ProcessedWebhook model
│   │   │
│   │   ├── schemas/                # Pydantic v2 request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # RegisterRequest, LoginRequest, TokenResponse
│   │   │   ├── menu.py             # MenuItemCreate, MenuItemUpdate, MenuItemResponse
│   │   │   ├── order.py            # OrderCreate, OrderItemCreate, OrderResponse
│   │   │   ├── table.py            # TableCreate, TableResponse
│   │   │   ├── analytics.py        # SummaryResponse, PopularItemsResponse
│   │   │   ├── reservation.py      # ReservationCreate, ReservationResponse
│   │   │   └── common.py           # ErrorResponse, PaginatedResponse, SuccessResponse
│   │   │
│   │   ├── services/               # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py     # JWT, bcrypt, sessions, rate limiting
│   │   │   ├── menu_service.py     # Menu CRUD, soft-delete, specials
│   │   │   ├── order_service.py    # Ordering, state machine, idempotency, billing
│   │   │   ├── table_service.py    # Tables, QR generation, merge logic
│   │   │   ├── analytics_service.py # Metrics computation, briefing data
│   │   │   ├── billing_service.py  # Razorpay subscription, dunning (Phase 3)
│   │   │   └── notification_service.py # Email (SendGrid), SMS (MSG91)
│   │   │
│   │   ├── routers/                # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # /api/v1/auth/*
│   │   │   ├── menu.py             # /api/v1/menu/*
│   │   │   ├── orders.py           # /api/v1/orders/*
│   │   │   ├── tables.py           # /api/v1/tables/*
│   │   │   ├── analytics.py        # /api/v1/analytics/*
│   │   │   ├── reservations.py     # /api/v1/reservations/*
│   │   │   ├── webhooks.py         # /api/v1/webhooks/*
│   │   │   ├── ai_briefing.py      # /api/v1/ai/*
│   │   │   ├── tax_configs.py      # /api/v1/tax-configs/*
│   │   │   ├── account.py          # /api/v1/account/*
│   │   │   └── websocket.py        # WS /ws/{restaurant_id}
│   │   │
│   │   ├── core/                   # Cross-cutting concerns
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # JWT creation/validation, bcrypt helpers
│   │   │   ├── rate_limit.py       # Redis-backed rate limiting middleware
│   │   │   ├── websocket_manager.py # Room-based WS connection manager
│   │   │   └── errors.py           # Error codes + standard error response builder
│   │   │
│   │   └── celery/                 # Background tasks
│   │       ├── __init__.py
│   │       ├── celery_app.py       # Celery app configuration
│   │       └── tasks.py            # reset_daily_specials, generate_ai_briefing, dunning
│   │
│   ├── alembic/                    # Database migrations
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 001_core_tables.py
│   │       └── 002_row_level_security.py
│   │
│   ├── tests/
│   │   ├── unit/                   # Unit tests (pytest)
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_order_service.py
│   │   │   ├── test_menu_service.py
│   │   │   └── test_table_service.py
│   │   ├── integration/            # API integration tests
│   │   │   ├── test_auth_endpoints.py
│   │   │   ├── test_menu_endpoints.py
│   │   │   ├── test_order_endpoints.py
│   │   │   └── test_table_endpoints.py
│   │   └── fixtures/               # Shared test fixtures
│   │       ├── conftest.py
│   │       └── factories.py
│   │
│   ├── requirements.txt            # Python dependencies
│   ├── requirements-dev.txt        # Dev/test dependencies
│   ├── Dockerfile                  # Production container
│   └── .env.example                # Environment variable template
│
├── frontend/
│   ├── apps/
│   │   ├── reception/              # Next.js 14 — Reception Dashboard
│   │   │   ├── src/
│   │   │   │   ├── app/            # App Router pages
│   │   │   │   ├── components/     # Dashboard-specific components
│   │   │   │   ├── hooks/          # Custom React hooks
│   │   │   │   ├── lib/            # API client, WS manager, utils
│   │   │   │   └── types/          # TypeScript type definitions
│   │   │   ├── public/
│   │   │   ├── next.config.js
│   │   │   ├── tailwind.config.ts
│   │   │   ├── tsconfig.json
│   │   │   ├── package.json
│   │   │   └── .env.example
│   │   │
│   │   ├── customer/               # Next.js PWA — Customer Dashboard
│   │   │   ├── src/
│   │   │   │   ├── app/            # App Router (flow-based pages)
│   │   │   │   ├── components/
│   │   │   │   ├── hooks/
│   │   │   │   ├── lib/
│   │   │   │   └── types/
│   │   │   ├── public/
│   │   │   │   ├── manifest.json   # PWA manifest
│   │   │   │   └── sw.js           # Service worker
│   │   │   ├── next.config.js
│   │   │   ├── tailwind.config.ts
│   │   │   ├── tsconfig.json
│   │   │   ├── package.json
│   │   │   └── .env.example
│   │   │
│   │   └── chef/                   # Next.js — Chef Dashboard
│   │       ├── src/
│   │       │   ├── app/            # Single-screen layout
│   │       │   ├── components/     # Order cards, status controls
│   │       │   ├── hooks/
│   │       │   ├── lib/
│   │       │   └── types/
│   │       ├── public/
│   │       ├── next.config.js
│   │       ├── tailwind.config.ts
│   │       ├── tsconfig.json
│   │       ├── package.json
│   │       └── .env.example
│   │
│   └── packages/
│       └── shared/                 # Shared TypeScript types & utilities
│           ├── src/
│           │   ├── types/          # Shared type definitions
│           │   │   ├── order.ts
│           │   │   ├── menu.ts
│           │   │   ├── table.ts
│           │   │   ├── auth.ts
│           │   │   └── websocket.ts
│           │   └── utils/          # Shared utility functions
│           │       ├── api-client.ts
│           │       ├── ws-manager.ts
│           │       └── formatters.ts
│           ├── package.json
│           └── tsconfig.json
│
├── scripts/
│   ├── seed_test_data.py           # Creates 5 restaurants, 50 tables, 200 items, 1000 orders
│   ├── generate_qr.py             # Standalone QR generation utility
│   └── load_test/
│       └── k6_scenario.js         # k6 load test script
│
├── docs/
│   ├── runbooks/                   # Operational runbooks
│   │   ├── db-restore.md
│   │   ├── ws-server-restart.md
│   │   ├── redis-flush.md
│   │   ├── razorpay-webhook-replay.md
│   │   └── emergency-account-disable.md
│   └── api/                       # API documentation
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI/CD pipeline
│
├── docker-compose.yml              # Local dev environment
├── docker-compose.prod.yml         # Production (LAN deployment)
├── .env.example                    # Root environment template
├── .gitignore
└── README.md
```

---

## 2. Dependency Graph

```
frontend/packages/shared  ← used by all 3 apps
frontend/apps/reception   → backend API (REST + WS)
frontend/apps/customer    → backend API (REST + WS)
frontend/apps/chef        → backend API (WS primary)
backend/app/routers       → backend/app/services
backend/app/services      → backend/app/models + backend/app/core
backend/app/models        → PostgreSQL (via SQLAlchemy)
backend/app/celery        → backend/app/services + Redis
```

---

## 3. Package Managers & Build Tools

| Component | Package Manager | Build Tool | Language |
|-----------|----------------|------------|----------|
| Backend | pip | — | Python 3.11+ |
| Frontend apps | npm/pnpm | Next.js | TypeScript |
| Shared package | npm/pnpm | tsc | TypeScript |
| Database | Alembic | — | SQL |
| Load tests | — | k6 | JavaScript |

---

## 4. Key Dependencies

### Backend (requirements.txt)
```
fastapi>=0.110
uvicorn[standard]
sqlalchemy[asyncio]>=2.0
asyncpg
alembic
pydantic>=2.0
pydantic-settings
python-jose[cryptography]
passlib[bcrypt]
redis
celery
httpx
sendgrid
boto3
aioboto3
qrcode[pil]
bleach
phonenumbers
python-multipart
```

### Frontend (per app)
```json
{
  "next": "14.x",
  "react": "^18",
  "react-dom": "^18",
  "tailwindcss": "^3.4",
  "typescript": "^5",
  "@tablz/shared": "workspace:*"
}
```

---

## 5. Docker Compose (Local Dev)

```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    depends_on: [db, redis]
    volumes: ["./backend:/app"]

  db:
    image: postgres:15
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: tablz
      POSTGRES_USER: tablz_app
      POSTGRES_PASSWORD: dev-password
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  celery:
    build: ./backend
    command: celery -A app.celery.celery_app worker -B --loglevel=info
    env_file: ./backend/.env
    depends_on: [api, redis]

volumes:
  postgres_data:
```

---

## 6. Workspace Configuration

For monorepo management with multiple Next.js apps:

```json
// root package.json
{
  "private": true,
  "workspaces": [
    "frontend/apps/*",
    "frontend/packages/*"
  ],
  "scripts": {
    "dev:reception": "npm -w frontend/apps/reception run dev",
    "dev:customer": "npm -w frontend/apps/customer run dev",
    "dev:chef": "npm -w frontend/apps/chef run dev",
    "build:all": "npm -w frontend/apps/reception run build && npm -w frontend/apps/customer run build && npm -w frontend/apps/chef run build",
    "test:frontend": "npm -w frontend/apps/* run test"
  }
}
```

# TABLZ Implementation — Task Tracker

## Phase 1: Week 1 — Foundation (Backend + Auth)
- [x] Scaffold monorepo structure (backend + frontend stubs + docker-compose)
- [x] Backend core: [main.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/main.py), [config.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/config.py), [database.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/database.py), [deps.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/deps.py)
- [x] SQLAlchemy ORM models (restaurant, table, menu_item, order, order_item, customer_session, audit_log)
- [x] Pydantic schemas (auth, common error response)
- [x] Core utilities: [security.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/core/security.py) (JWT + bcrypt), [errors.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/core/errors.py) (standard error format)
- [x] AuthService: register, verify_email, login, refresh, logout
- [x] Auth router endpoints
- [x] Rate limiting middleware ([rate_limit.py](file:///d:/code/Project/tablez-demo2-allByAi/backend/app/core/rate_limit.py))
- [x] [requirements.txt](file:///d:/code/Project/tablez-demo2-allByAi/backend/requirements.txt) + [Dockerfile](file:///d:/code/Project/tablez-demo2-allByAi/backend/Dockerfile) + [.env.example](file:///d:/code/Project/tablez-demo2-allByAi/backend/.env.example)
- [x] Docker Compose for local dev (PostgreSQL + Redis)

## Phase 1: Week 1 — Frontend Design (Stitch MCP)
- [x] Create Stitch project for TABLZ dashboards
- [x] Design Reception Dashboard — login screen
- [x] Design Reception Dashboard — home/overview screen
- [x] Design Customer Dashboard — QR landing + menu browse
- [x] Design Chef Dashboard — order queue screen

## Phase 1: Week 2 — Menu & Tables (Backend)
- [x] MenuService + router (CRUD, soft-delete, availability toggle)
- [x] TableService + router (creation, QR token, status)
- [x] Menu & table Pydantic schemas

## Phase 1: Week 3 — Customer Ordering (Backend)
- [x] Customer session creation (QR scan flow)
- [x] OrderService (create_order, idempotency, price snapshot, state machine)
- [x] Order router endpoints

## Phase 1: Week 4 — WebSocket + Chef Dashboard (Backend)
- [x] WebSocket manager (rooms, heartbeat, token refresh)
- [x] AnalyticsService (revenue, popular items, occupancy)
- [x] Bill finalization endpoint

## Phase 2: Alembic + Celery + Frontend
- [x] Alembic migration setup (alembic.ini, env.py, initial migration)
- [x] Celery setup (celery_app.py, tasks: reset_daily_specials)
- [x] Frontend: Next.js scaffolding (reception-dashboard, customer-app, chef-dashboard)
- [x] Frontend: Shared TypeScript types package
- [x] More Stitch MCP dashboard screens

## Phase 2: Reception Dashboard UI
- [x] Global styling, Tailwind config, fonts (Midnight Luxe preset)
- [x] AuthProvider and API client hook
- [x] UI Components (MagneticButton, GlassCard, etc.)
- [x] Login screen (/login)
- [x] Dashboard shell (Floating navbar, Status overview)
- [x] Live Table Map view
- [x] Orders Queue view

## Phase 3: Customer Web App UI
- [x] Global styling, Tailwind config, fonts (Midnight Luxe)
- [x] SessionProvider (QR validation checking)
- [x] [lib/api.ts](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/customer-app/src/lib/api.ts) (Cookie-included fetch wrapper)
- [x] QR scan landing page (`/scan`)
- [x] Live Menu view (`/menu`)
- [x] Local cart management hook
- [x] Checkout / Send Order view (`/checkout`)
- [x] Digital Receipt & Barcode view (`/receipt/[id]`)
## Phase 4: Chef Dashboard & WebSockets
- [x] Global styling, Tailwind config, fonts (Midnight Luxe)
- [x] AuthProvider & API Client for Staff
- [x] [useWebSocket](file:///d:/code/Project/tablez-demo2-allByAi/frontend/apps/chef-dashboard/src/hooks/useWebSocket.ts#8-66) hook for real-time order streams
- [x] Staff Login View (`/login`)
- [x] Live Kanban Ticket Board View
- [x] Order State Transitions (`pending` -> `preparing` -> `ready`)

# 11 — Environment & DevOps
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Environment Tiers

| Environment | Purpose | DB | Redis | Razorpay | URL |
|-------------|---------|-----|-------|----------|-----|
| Development | Developer machines | Local Postgres / Supabase dev | Local Redis | Test mode | localhost:8000 / localhost:3000 |
| Staging | Integration + load testing | Supabase staging project | Upstash staging | Test mode | staging.tablz.app |
| Production | Live customers | Supabase production | Upstash production | Live mode | tablz.app |

---

## 2. Environment Variables

All configuration via environment variables. **Never hardcode. Never commit to git.**

```bash
# ─── Database ───
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/tablz
DATABASE_URL_SYNC=postgresql://user:password@host:5432/tablz  # Alembic

# ─── Security ───
JWT_SECRET_KEY=<256-bit-random>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── Redis ───
REDIS_URL=redis://localhost:6379/0

# ─── AWS ───
AWS_ACCESS_KEY_ID=<key>
AWS_SECRET_ACCESS_KEY=<secret>
AWS_REGION=ap-south-1
S3_BUCKET_NAME=tablz-uploads-prod

# ─── Email ───
SENDGRID_API_KEY=<key>
FROM_EMAIL=noreply@tablz.app

# ─── App ───
BASE_URL=https://tablz.app
ENVIRONMENT=development  # development | staging | production

# ─── Razorpay (Phase 3) ───
RAZORPAY_KEY_ID=<key>
RAZORPAY_KEY_SECRET=<secret>
RAZORPAY_MODE=test  # test | live

# ─── Anthropic (Phase 4) ───
ANTHROPIC_API_KEY=<key>
```

---

## 3. CI/CD Pipeline

### GitHub Actions — `.github/workflows/ci.yml`

Runs on every push and PR to main.

```yaml
name: TABLZ CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: tablz_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - name: Secret Scan
        run: truffleHog --regex --entropy=False .
      - name: Install Python deps
        run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - name: Run Migrations
        run: cd backend && alembic upgrade head
      - name: Unit + Integration Tests
        run: cd backend && pytest --cov=app --cov-fail-under=80
      - name: OWASP ZAP Scan
        run: |
          uvicorn app.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
          zap-baseline.py -t http://localhost:8000
      - name: Frontend Build
        run: npm run build:all
      - name: axe-core Accessibility
        run: npm run test:a11y

  e2e:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start Full Stack
        run: docker compose up -d
      - name: Wait for healthy
        run: sleep 15
      - name: Run Playwright E2E
        run: npx playwright test
      - name: Fail on Journey 1 failure
        run: echo "Journey 1 must pass"

  deploy:
    needs: [test, e2e]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Backend
        run: echo "Deploy to Railway/Fly.io"
      - name: Deploy Frontends
        run: echo "Deploy to Vercel"
```

---

## 4. Deployment Architecture

### Cloud Deployment (Primary)

```
Browser
  │
  ▼
Vercel CDN (Next.js — SSR + static)
  │
  ▼
FastAPI on Railway / Fly.io / AWS ECS (auto-scaled)
  │
  ├── Supabase PostgreSQL (AWS ap-south-1)
  ├── Upstash Redis (rate limiting + session cache)
  ├── Celery workers (Railway / Fly.io)
  └── AWS S3 + CloudFront (file storage + CDN)
```

### Local / LAN Deployment (Phase 4)

```
Restaurant LAN
  │
  ▼
Intel NUC (Docker Compose bundle)
  ├── Next.js container (all 3 dashboards)
  ├── FastAPI container
  ├── PostgreSQL container
  ├── Redis container
  └── Celery container

- No internet required for core features
- Admin-triggered updates via Reception dashboard
- Backup: cron at 2am → compressed dump to USB/NAS
```

---

## 5. Docker Compose — Production (LAN)

```yaml
services:
  frontend:
    image: tablz/frontend:latest
    ports: ["80:3000", "443:3000"]
    restart: unless-stopped

  api:
    image: tablz/api:latest
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/tablz
      REDIS_URL: redis://redis:6379
      ENVIRONMENT: local
    depends_on: [db, redis]
    restart: unless-stopped

  db:
    image: postgres:15
    volumes: ["postgres_data:/var/lib/postgresql/data"]
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  celery:
    image: tablz/api:latest
    command: celery -A app.celery worker -B
    depends_on: [api, redis]
    restart: unless-stopped

volumes:
  postgres_data:
```

**Update mechanism:** Admin clicks 'Check for Updates' → backend calls update server → `docker compose pull && docker compose up -d` with health check before removing old containers.

---

## 6. Disaster Recovery & Backup

### Recovery Objectives

| Scenario | RPO (Data Loss) | RTO (Downtime) |
|----------|-----------------|----------------|
| DB corruption | 1 hour (hourly WAL) | < 2 hours |
| DB server failure | < 1 minute (replication) | < 60 seconds (auto) |
| App server crash | 0 (DB is truth) | < 2 minutes (auto-restart) |
| Full region outage | < 1 hour | < 4 hours (manual) |

### Backup Policy

- **Daily:** Full DB snapshots via Supabase PITR — 30-day retention
- **Hourly:** Incremental WAL backups — 7-day retention
- **Monthly:** Backup restore test on staging (documented)
- **LAN:** Daily cron at 2am → compressed dump to USB/NAS

### Runbooks

Located in `/docs/runbooks/`:
- `db-restore.md` — Restore from Supabase PITR
- `ws-server-restart.md` — WebSocket server restart
- `redis-flush.md` — Redis cache flush procedure
- `razorpay-webhook-replay.md` — Replay missed webhooks
- `emergency-account-disable.md` — Emergency account lockout

---

## 7. Monitoring & Observability

| Tool | Purpose | Data |
|------|---------|------|
| Sentry | Backend error tracking | Stack traces, request context (no PII) |
| Datadog / Grafana | APM + metrics | Response times, throughput, error rates |
| Supabase Dashboard | DB metrics | Query performance, connections, storage |
| Upstash Dashboard | Redis metrics | Hit rates, memory, operations/sec |
| Vercel Analytics | Frontend performance | Core Web Vitals, page load times |
| k6 | Load testing | Pre-release performance verification |

### Alerting Rules

| Metric | Warning | Critical | Channel |
|--------|---------|----------|---------|
| API error rate (5xx) | > 1% | > 5% | PagerDuty + Email |
| API p95 latency | > 500ms | > 2000ms | Email |
| DB connection pool utilization | > 70% | > 90% | PagerDuty |
| Celery task failure rate | > 5% | > 20% | Email |
| Disk space | > 80% | > 95% | PagerDuty |

---

## 8. Security Headers

Applied to all responses:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; ...
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

## 9. Data Storage Locations

| Data | Location | Region |
|------|----------|--------|
| PostgreSQL | Supabase | AWS ap-south-1 (Mumbai) |
| S3 (images, PDFs) | AWS S3 | ap-south-1 (Mumbai) |
| Redis cache | Upstash | ap-south-1 |
| Logs | Datadog | PII masked, 90-day retention |
| Frontend assets | Vercel CDN | Global edge |
| QR images | S3 + CloudFront | ap-south-1 + global CDN |

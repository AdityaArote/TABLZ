# 01 — Product Requirements Document
## TABLZ — AI-Powered Restaurant Management Platform
**Version:** 2.0 · Production Ready

---

## 1. Executive Summary

TABLZ is a subscription-based, AI-powered restaurant management SaaS platform that unifies the ordering experience across three synchronized dashboards: **Reception**, **Customer**, and **Chef**. It is designed specifically for independent restaurants and small chains operating on fragmented tools — separate POS systems, paper menus, manual kitchen ticketing, and siloed analytics.

### 1.1 Core Value Proposition

Replace 4–6 disconnected tools (POS, menu app, reservation system, kitchen display, analytics dashboard, billing) with a single unified platform. Reduce order errors by 40–60%, cut table turn time by 15–20 minutes, and provide daily AI-driven insights that independent restaurant owners cannot currently access at any price point.

### 1.2 Problem Statement

| # | Problem | Impact |
|---|---------|--------|
| 1 | Independent restaurants rely on 4–6 disconnected tools | Data silos, operational errors, high training friction |
| 2 | No single affordable platform combines customer ordering + kitchen management + owner analytics | Operational blind spots and duplication |
| 3 | Manual order-taking creates 8–12% error rates | Revenue loss, customer dissatisfaction, wasted ingredients |
| 4 | Restaurant owners have no real-time visibility into profitability, waste, or table utilization | Inability to make data-driven decisions |
| 5 | Existing solutions (Toast, Square, Lightspeed) cost ₹25,000–65,000/month | Priced out of reach for independent operators |

### 1.3 Solution Overview

- Unified 3-dashboard platform accessible via a single admin credential
- QR-based customer ordering — no app install required (PWA)
- Real-time order routing from customer table to chef kitchen display
- Owner intelligence layer: daily AI briefings, menu engineering, cost analytics
- Flat-fee subscription model starting at a free tier for pilot acquisition

---

## 2. Target Market

| Segment | Description | Pain Intensity |
|---------|-------------|----------------|
| **Primary** | Independent restaurants (1–3 locations) | Very High — no dedicated tech team |
| **Secondary** | Small chains (4–15 locations) | High — fragmented tools per location |
| **Tertiary** | Ghost kitchens, cloud kitchens | Medium — need kitchen-side tooling |

---

## 3. Platform Components

| Component | Tech Stack | Primary Responsibility |
|-----------|-----------|----------------------|
| Reception Dashboard | Next.js 14, React, Tailwind CSS | Menu, tables, billing, analytics |
| Customer Dashboard | Next.js PWA, React | QR-based ordering, payment |
| Chef Dashboard | Next.js, React, WebSocket client | Order queue, status management |
| Backend API | Python / FastAPI | Business logic, auth, data layer |
| Database Layer | PostgreSQL 15 via Supabase | Persistent storage, RLS policies |
| Real-Time Layer | WebSocket (FastAPI) | Live sync across all dashboards |
| QR Engine | Python qrcode lib | Unique QR generation per table |
| Task Queue | Celery + Redis | Scheduled jobs, email, specials reset |
| Cache / Rate Limit | Redis (Upstash for cloud) | Session state, rate limiting |
| File Storage | AWS S3 + CloudFront CDN | Menu images, barcode PDFs |

---

## 4. Subscription Tiers

| Feature | Free | Premium (₹2,499/mo) | VIP (₹5,999/mo) | Luxury (₹14,999/mo) |
|---------|------|---------------------|------------------|---------------------|
| Max Tables | 10 | 30 | 75 | Unlimited |
| Max Menu Items | 50 | 200 | 500 | Unlimited |
| Analytics Depth | 7 days | 90 days | 1 year | Unlimited + export |
| API Access | No | Read-only | Full | Full + webhooks |
| Custom Branding | No | No | Logo only | Full white-label |
| Reservations | No | Yes | Yes | Yes + SMS confirm |
| AI Briefings | No | Weekly | Daily | Real-time |
| Table Merging | No | Yes (3 max) | Yes (5 max) | Yes (unlimited) |
| Priority Support | Email only | Email + chat | Phone + SLA | Dedicated CSM |

---

## 5. Deployment Models

| Dimension | Cloud Deployment | Local (LAN) Deployment |
|-----------|-----------------|----------------------|
| Hosting | AWS / GCP / Vercel (managed) | On-premise server / Intel NUC |
| Internet Required | Yes — always-on | No — operates fully on local network |
| Latency | 50–150ms typical | <5ms LAN latency |
| Setup Cost | None — SaaS model | Hardware cost (~₹17,000–35,000 one-time) |
| Data Sovereignty | Data on cloud servers | All data stays on-premise |
| Backup | Automatic cloud backup (daily, 30-day retention) | Scheduled local backup via cron |
| Software Updates | Automatic via CI/CD | Admin-triggered pull from update server |
| Best For | Most restaurants — simplest setup | Restaurants with poor/no internet |

Local deployment (Phase 4) ships as a Docker Compose bundle with a setup wizard script.

---

## 6. Core User Journeys

### Journey 1 — Full Order Flow (MVP Critical Path)
Customer scans QR → browses menu → places order → Chef receives order → updates status → Customer sees status update → Reception finalizes bill → barcode generated → table reset to available.

### Journey 2 — Admin Onboarding
Register restaurant → verify email → create menu items → create tables → generate QR codes → complete first test order.

### Journey 3 — Table Merge
Owner scans QR → adds guests → scans second table QR to merge → places merged order → single bill generated for merged table.

### Journey 4 — Subscription Upgrade
Free tier restaurant → upgrade to Premium → verify new limits applied → verify Razorpay webhook processed.

### Journey 5 — Auth Security
Attempt 6 failed logins → verify 15-min lockout → attempt QR session with expired token → verify rejection.

---

## 7. Data Privacy & DPDP Compliance

India's Digital Personal Data Protection Act (DPDP) 2023 is in force. TABLZ handles personal data of restaurant owners and indirectly of their customers. Compliance is mandatory before launch.

### Data Classification

| Data Type | Classification | Retention |
|-----------|---------------|-----------|
| Restaurant owner PII | Sensitive | Duration of account + 3 years |
| Customer session data | Personal | 4 hours (session) then anonymized |
| Order data | Business | 3 years (tax compliance) |
| Analytics data | Aggregated | Per subscription tier depth |
| Audit logs | Security | 90 days minimum, 1 year for security events |
| Payment data | Financial | 7 years (financial compliance) |

### Data Subject Rights (DPDP)

- **Right to Access:** `GET /api/v1/account/data-export` — returns all restaurant data as JSON within 72 hours
- **Right to Erasure:** `DELETE /api/v1/account` — soft-deletes account, anonymizes PII within 30 days. Financial records retained 7 years
- **Right to Correction:** admin can update email, name, phone via reception dashboard settings
- **Data Portability:** menu data, order history exportable as CSV (Luxury) or on account deletion (all tiers)

---

## 8. Accessibility Requirements (WCAG 2.1 AA)

| Requirement | Customer PWA | Reception | Chef |
|-------------|-------------|-----------|------|
| Color contrast ratio | 4.5:1 minimum (AA) | 4.5:1 minimum | 4.5:1 minimum |
| Touch target size | 44×44px minimum | 44×44px minimum | 48×48px (gloved hands) |
| Screen reader support | Full (ARIA labels) | Full | Partial (visual-first KDS) |
| Keyboard navigation | Full | Full | Partial |
| Font size minimum | 16px body text | 14px body text | 18px (distance viewing) |
| Focus indicators | Visible 3px outline | Visible 3px outline | Visible 3px outline |
| Motion/animation | Respect prefers-reduced-motion | Respect | Respect |

---

## 9. AI Briefings Specification

### Briefing Schedule by Tier

| Tier | Frequency | Delivery Method | Model Used |
|------|-----------|----------------|------------|
| Free | Not available | — | — |
| Premium | Weekly (Monday 8am) | Email + Dashboard | claude-haiku-3 |
| VIP | Daily (8am local time) | Email + Dashboard | claude-haiku-3 |
| Luxury | Real-time (on demand + daily) | Dashboard widget | claude-haiku-3 |

### Data Collected (No PII)

- Yesterday's gross revenue, net revenue, order count, average order value
- Top/bottom 5 menu items by order count and revenue
- Peak hour distribution (no customer identifiers)
- Table occupancy rate & average table turn time
- Comparison to previous 7-day average for each metric

### Data Privacy Commitment

AI briefings use Anthropic Claude API. **ONLY** aggregated, anonymized metrics are sent — no customer names, no PII, no individual order details. Cost estimate: ~₹0.20/briefing.

---

## 10. Payment Gateway — Razorpay

**Decision:** Razorpay as primary gateway. India-first, supports UPI + cards + netbanking, strong webhook reliability, sandbox for testing, lowest MDR for INR transactions.

- Subscription billing via Razorpay Subscriptions API
- Webhook events: `subscription.activated`, `subscription.charged`, `subscription.halted`, `subscription.cancelled`, `payment.failed`
- Razorpay keys stored server-side only (never in frontend bundle)
- Test mode enforced in dev/staging via `RAZORPAY_MODE` env variable
- Webhook is the source of truth (not redirect callback)

---

## 11. Open Questions (Deferred)

| Question | Options / Context | Phase Needed By |
|----------|-------------------|-----------------|
| Thermal printer / KDS integration | Epson TM webhook bypass vs full POS integration | Phase 5+ |
| Multi-language menu support | English-only MVP vs i18n from day 1 | Phase 3 |
| Customer-facing payment (UPI at table) | Razorpay payment link vs QR UPI vs deferred | Phase 4 |
| Staff individual PIN login | DB table added — implementation timing | Phase 3 |
| Mobile app (native iOS/Android) | PWA-only vs native app | Phase 5+ |

---

## Document Control

This document is the source of truth for all engineering and design decisions. Architectural changes must be logged as changelog entries. No code should be written for features not covered in this document without an approved update.

# 05 — Database Schema
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Overview

PostgreSQL 15 hosted on Supabase (AWS ap-south-1 / Mumbai). Row-Level Security (RLS) enabled on all tenant-scoped tables. Soft deletes on all user-facing entities. Immutable audit log.

**Connection:** SQLAlchemy 2.0 async engine, `pool_size=20`, `max_overflow=10`, `pool_timeout=30s`.

---

## 2. Entity-Relationship Diagram

```
restaurants ──┐
              ├──< tables ──< customer_sessions
              ├──< menu_items
              ├──< orders ──< order_items ──> menu_items
              ├──< reservations
              ├──< tax_configurations
              ├──< staff
              ├──< audit_log
              └──< ai_briefings
```

---

## 3. Table Definitions

### 3.1 restaurants

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() | Primary key |
| admin_id | VARCHAR(12) | UNIQUE, NOT NULL | Auto-generated (TBZ-YYXXXX) |
| name | VARCHAR(255) | NOT NULL | Restaurant display name |
| subscription_tier | VARCHAR(20) | NOT NULL, DEFAULT 'free', CHECK IN ('free','premium','vip','luxury') | Current tier |
| timezone | VARCHAR(50) | NOT NULL, DEFAULT 'Asia/Kolkata' | For analytics date bucketing |
| currency | CHAR(3) | NOT NULL, DEFAULT 'INR' | ISO currency code |
| password_hash | TEXT | NOT NULL | bcrypt hash |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Owner email |
| email_verified | BOOLEAN | NOT NULL, DEFAULT false | Email verification gate |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | Soft-disable on lapse |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Account creation |

### 3.2 tables

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | Owner restaurant |
| table_number | SMALLINT | NOT NULL | Human-readable |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'available', CHECK IN ('available','occupied','merged','cleaning','reserved') | |
| owner_session_id | UUID | FK → customer_sessions, NULLABLE | First scanner |
| merged_into_table_id | UUID | FK → tables, NULLABLE | Self-reference for merges |
| is_expandable | BOOLEAN | NOT NULL, DEFAULT false | Physical extension |
| qr_code_token | VARCHAR(128) | UNIQUE, NOT NULL | Cryptographic token |
| qr_code_url | TEXT | NOT NULL | Full scan URL |
| max_capacity | SMALLINT | NOT NULL, DEFAULT 4 | Max guests |
| last_cleaned_at | TIMESTAMPTZ | NULLABLE | Cleaning tracking |

**Unique constraint:** `(restaurant_id, table_number)`

### 3.3 menu_items

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | RLS key |
| name | VARCHAR(255) | NOT NULL | Dish name |
| description | TEXT | NULLABLE | Sanitized HTML |
| price | NUMERIC(10,2) | NOT NULL, CHECK > 0 | Base price |
| category | VARCHAR(20) | NOT NULL, CHECK IN ('appetizer','main','dessert','beverage','side') | |
| cuisine | VARCHAR(100) | NULLABLE | Free text |
| dietary_type | VARCHAR(30) | NOT NULL, CHECK IN ('vegetarian','non_vegetarian','vegan','contains_nuts') | |
| is_daily_special | BOOLEAN | NOT NULL, DEFAULT false | Auto-reset daily |
| is_weekly_special | BOOLEAN | NOT NULL, DEFAULT false | Auto-reset weekly |
| is_available | BOOLEAN | NOT NULL, DEFAULT true | Availability toggle |
| is_deleted | BOOLEAN | NOT NULL, DEFAULT false | Soft-delete flag |
| deleted_at | TIMESTAMPTZ | NULLABLE | |
| image_url | TEXT | NULLABLE | CDN URL |
| prep_time_minutes | SMALLINT | NOT NULL, DEFAULT 15 | Estimated prep time |

### 3.4 customer_sessions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| table_id | UUID | FK → tables, NOT NULL | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | |
| session_token | VARCHAR(128) | UNIQUE, NOT NULL | HttpOnly cookie |
| is_table_owner | BOOLEAN | NOT NULL, DEFAULT false | First scanner |
| device_fingerprint | VARCHAR(64) | NULLABLE | Anti-abuse |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| expires_at | TIMESTAMPTZ | NOT NULL | 4 hours from creation |
| invalidated_at | TIMESTAMPTZ | NULLABLE | Revoked on table reset |

### 3.5 orders

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | RLS key |
| table_id | UUID | FK → tables, NOT NULL | |
| session_id | UUID | FK → customer_sessions, NOT NULL | Ordering customer |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending', CHECK IN ('pending','received','preparing','ready','served','cancelled') | |
| special_requests | TEXT | NULLABLE | Sanitized free-text |
| total_amount | NUMERIC(10,2) | NOT NULL | Computed sum |
| tax_config_id | UUID | FK → tax_configurations, NULLABLE | Tax snapshot |
| tax_amount | NUMERIC(10,2) | NOT NULL, DEFAULT 0 | Computed tax |
| is_finalized | BOOLEAN | NOT NULL, DEFAULT false | Bill lock |
| barcode_token | VARCHAR(128) | UNIQUE, NULLABLE | Generated on finalization |
| placed_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| finalized_at | TIMESTAMPTZ | NULLABLE | |

### 3.6 order_items

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| order_id | UUID | FK → orders, NOT NULL | Parent order |
| menu_item_id | UUID | FK → menu_items, NOT NULL | |
| quantity | SMALLINT | NOT NULL, CHECK > 0 | |
| unit_price_at_order | NUMERIC(10,2) | NOT NULL | Price snapshot |
| item_notes | TEXT | NULLABLE | e.g., "no onion" |

### 3.7 reservations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | |
| table_id | UUID | FK → tables, NULLABLE | Null if any-table |
| guest_name | VARCHAR(255) | NOT NULL | |
| guest_phone | VARCHAR(20) | NOT NULL | E.164 format |
| party_size | SMALLINT | NOT NULL, CHECK > 0 | |
| reserved_at | TIMESTAMPTZ | NOT NULL | Booking datetime |
| status | VARCHAR(20) | NOT NULL, CHECK IN ('pending','confirmed','seated','no_show','cancelled') | |
| notes | TEXT | NULLABLE | Special requests |

### 3.8 tax_configurations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | |
| name | VARCHAR(100) | NOT NULL | e.g., GST, Service Charge |
| rate_percent | NUMERIC(5,2) | NOT NULL, CHECK >= 0 | e.g., 18.00 |
| applies_to | VARCHAR(20) | NOT NULL, CHECK IN ('all','food_only','beverages_only') | |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### 3.9 staff

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | Display name |
| role | VARCHAR(20) | NOT NULL, CHECK IN ('chef','reception','manager') | |
| pin_hash | TEXT | NOT NULL | bcrypt hash of 4–6 digit PIN |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| last_login_at | TIMESTAMPTZ | NULLABLE | |

### 3.10 audit_log

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGSERIAL | PK | High-volume, integer PK |
| restaurant_id | UUID | FK → restaurants, NULLABLE | Null for system events |
| actor_type | VARCHAR(20) | NOT NULL, CHECK IN ('admin','staff','customer','system') | |
| actor_id | TEXT | NOT NULL | admin_id, staff_id, session_id, or "system" |
| action | VARCHAR(100) | NOT NULL | e.g., order.created, login.failed |
| resource_type | VARCHAR(50) | NULLABLE | e.g., order, menu_item |
| resource_id | UUID | NULLABLE | Affected resource ID |
| ip_address | INET | NULLABLE | Request IP |
| metadata | JSONB | NULLABLE | Additional context (no PII) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

### 3.11 ai_briefings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| restaurant_id | UUID | FK → restaurants, NOT NULL | |
| generated_at | TIMESTAMPTZ | NOT NULL | |
| content | TEXT | NOT NULL | Generated briefing text |
| model_used | VARCHAR(50) | NOT NULL | e.g., claude-haiku-3 |
| tokens_used | INTEGER | NOT NULL | Token count |

### 3.12 processed_webhooks

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| razorpay_event_id | VARCHAR(100) | UNIQUE, NOT NULL | Idempotency key |
| processed_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

---

## 4. Indexes

```sql
CREATE INDEX idx_menu_items_restaurant ON menu_items(restaurant_id) WHERE is_deleted = false;
CREATE INDEX idx_orders_restaurant_status ON orders(restaurant_id, status);
CREATE INDEX idx_orders_table ON orders(table_id);
CREATE INDEX idx_customer_sessions_token ON customer_sessions(session_token);
CREATE INDEX idx_audit_log_restaurant ON audit_log(restaurant_id, created_at DESC);
```

---

## 5. Row-Level Security

```sql
ALTER TABLE tables ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tables_isolation ON tables
    USING (restaurant_id = current_setting('app.current_restaurant_id', true)::uuid);
CREATE POLICY menu_items_isolation ON menu_items
    USING (restaurant_id = current_setting('app.current_restaurant_id', true)::uuid);
CREATE POLICY orders_isolation ON orders
    USING (restaurant_id = current_setting('app.current_restaurant_id', true)::uuid);
```

Application sets `app.current_restaurant_id` via `SET LOCAL` before every query.

---

## 6. Application DB User

```sql
CREATE USER tablz_app WITH PASSWORD '<strong-password>';
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO tablz_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO tablz_app;
-- No DELETE or TRUNCATE (soft deletes only)
```

---

## 7. Data Retention Policy

| Data Type | Retention |
|-----------|-----------|
| Restaurant owner PII | Account duration + 3 years |
| Customer sessions | 4h session, then anonymized |
| Order data | 3 years (tax compliance) |
| Audit logs | 90 days min, 1 year for security events |
| Payment data | 7 years (financial compliance) |
| AI briefings | Per subscription tier depth |

# 08 — Scoring Engine Specification
## TABLZ — AI-Powered Restaurant Management Platform

---

## 1. Overview

The TABLZ Scoring Engine is the analytics and intelligence layer that powers tier-gated metrics, AI briefings, menu engineering recommendations, and operational health assessments. It computes scores and metrics from raw order, menu, and table data to deliver actionable insights to restaurant owners.

---

## 2. Scoring Domains

### 2.1 Menu Item Performance Score

Each menu item receives a composite performance score based on:

| Factor | Weight | Source | Calculation |
|--------|--------|--------|-------------|
| Order Frequency | 30% | `order_items` | `item_order_count / total_orders_in_period` |
| Revenue Contribution | 30% | `order_items` | `item_revenue / total_revenue_in_period` |
| Margin Efficiency | 20% | `menu_items.price` | Higher price items with high frequency score better |
| Availability Uptime | 10% | `menu_items.is_available` | `hours_available / total_hours_in_period` |
| Customer Repeat Rate | 10% | `order_items + customer_sessions` | Returning sessions ordering same item |

**Score Output:** 0–100 (integer)

**Classification:**

| Score Range | Label | AI Briefing Action |
|-------------|-------|-------------------|
| 80–100 | ⭐ Star | "Celebrate and promote" |
| 60–79 | ✅ Performer | "Maintain current strategy" |
| 40–59 | ⚠️ Average | "Consider repositioning on menu" |
| 20–39 | ⬇️ Underperformer | "Evaluate for removal or repricing" |
| 0–19 | ❌ Dead Weight | "Strongly consider removing" |

### 2.2 Table Efficiency Score

Measures how efficiently each table generates revenue per hour.

| Factor | Weight | Source | Calculation |
|--------|--------|--------|-------------|
| Turn Rate | 40% | `orders.placed_at`, `orders.finalized_at` | `avg_turns_per_day / benchmark_turns` |
| Revenue per Hour | 30% | `orders.total_amount` | `table_revenue / occupied_hours` |
| Occupancy Rate | 20% | `tables.status` changes | `occupied_hours / operating_hours` |
| Cleaning Efficiency | 10% | `tables.last_cleaned_at` | `avg_clean_to_seat_minutes` |

**Score Output:** 0–100

### 2.3 Operational Health Score

Daily aggregate score for the entire restaurant.

| Factor | Weight | Source | Calculation |
|--------|--------|--------|-------------|
| Revenue vs 7-day Average | 25% | `orders` | `today_revenue / avg_7day_revenue * 100` |
| Order Completion Rate | 25% | `orders.status` | `served_orders / (served + cancelled) * 100` |
| Average Prep Time | 20% | `orders.placed_at` → status timestamps | vs `menu_items.prep_time_minutes` target |
| Peak Hour Utilization | 15% | `orders` by hour | Optimal spread vs concentrated |
| Table Utilization | 15% | Table occupancy | vs benchmark |

**Score Output:** 0–100

**Health Status:**

| Score | Status | Dashboard Display |
|-------|--------|-------------------|
| 85–100 | 🟢 Excellent | Green indicator |
| 70–84 | 🟡 Good | Yellow indicator |
| 50–69 | 🟠 Needs Attention | Orange indicator + notification |
| 0–49 | 🔴 Critical | Red indicator + immediate alert |

---

## 3. AI Briefing Data Pipeline

The scoring engine feeds data to the Claude AI briefing system.

### 3.1 Metrics Collected

```python
# AnalyticsService.get_briefing_metrics(restaurant_id, date)
{
    "gross_revenue": Decimal,
    "net_revenue": Decimal,        # after tax
    "order_count": int,
    "avg_order_value": Decimal,
    "top_5_items": [
        {"name": str, "count": int, "revenue": Decimal, "score": int}
    ],
    "bottom_5_items": [
        {"name": str, "count": int, "score": int}
    ],
    "peak_hours": [
        {"hour": int, "order_count": int}   # 0-23
    ],
    "occupancy_rate_pct": float,
    "avg_turn_time_minutes": float,
    "operational_health_score": int,
    "vs_7day_avg": {
        "revenue_delta_pct": float,
        "order_count_delta_pct": float
    }
}
```

### 3.2 AI System Prompt

```
You are a restaurant business advisor. You will receive yesterday's operational 
metrics for a restaurant. Generate a concise daily briefing (max 300 words) 
covering:
1. One key win to celebrate
2. One operational concern with a specific suggestion
3. One menu recommendation (promote or consider removing an item)
4. One observation about timing/staffing

Be specific, actionable, and encouraging. Do not mention customer names or any 
personal information. Respond in plain text, no markdown.
```

### 3.3 Data Privacy

- **ONLY** aggregated, anonymized metrics sent to Claude API
- No customer names, no PII, no individual order details, no session IDs
- Cost: ~2,000 tokens/briefing, ~₹0.20/briefing at claude-haiku-3 pricing

---

## 4. Subscription Tier Scoring Access

| Scoring Feature | Free | Premium | VIP | Luxury |
|----------------|------|---------|-----|--------|
| Menu Item Scores | Top 5 only | All items | All + history | All + export |
| Table Efficiency | No | Basic | Full | Full + export |
| Operational Health | No | Daily | Daily + trends | Real-time |
| AI Briefing | No | Weekly | Daily | On-demand |
| Date Range | 7 days | 90 days | 1 year | Unlimited |
| Export | No | No | No | CSV + PDF |

---

## 5. Computation Strategy

### Phase 1–3: On-Demand Computation

All scores computed at query time from `orders`, `order_items`, `menu_items`, and `tables` using PostgreSQL aggregate queries. No separate analytics database.

```sql
-- Example: Top items by order count (7-day rolling)
SELECT mi.name, COUNT(oi.id) as order_count, 
       SUM(oi.unit_price_at_order * oi.quantity) as revenue
FROM order_items oi
JOIN menu_items mi ON oi.menu_item_id = mi.id
JOIN orders o ON oi.order_id = o.id
WHERE o.restaurant_id = $1
  AND o.placed_at >= NOW() - INTERVAL '7 days'
  AND o.status != 'cancelled'
GROUP BY mi.id, mi.name
ORDER BY order_count DESC
LIMIT 10;
```

### Phase 4+: Optimization Path

At ~50 concurrent restaurants, consider:
- **Materialized views** for common aggregates (refresh hourly)
- **Read replica** for analytics queries (avoid OLTP impact)
- **Pre-computed daily snapshots** stored in `daily_metrics` table
- **Columnar store** if query complexity exceeds PostgreSQL efficient range

---

## 6. Celery Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `compute_daily_scores` | Daily at 2am (restaurant TZ) | Pre-compute all scores for previous day |
| `generate_ai_briefing` | Daily at 7am UTC | Fetch metrics → call Claude → store briefing |
| `reset_daily_specials` | Daily at midnight (restaurant TZ) | Reset `is_daily_special = false` |
| `reset_weekly_specials` | Weekly at week-start | Reset `is_weekly_special = false` |

---

## 7. Analytics API Mapping

| Endpoint | Scoring Domain | Data |
|----------|---------------|------|
| `GET /analytics/summary` | Operational Health | Revenue, order count, avg order value |
| `GET /analytics/popular-items` | Menu Item Score | Top 10 items by score |
| `GET /analytics/occupancy` | Table Efficiency | Occupancy rate, avg turn time |
| `GET /analytics/peak-hours` | Operational Health | Order distribution by hour |
| `GET /analytics/table-turnaround` | Table Efficiency | Avg clean-to-reseat time |
| `GET /ai/briefing` | All Domains | AI-generated summary |
| `GET /analytics/export` | All Domains | CSV/PDF full export |

---

## 8. Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Revenue < 7-day avg by | 20% | 40% | Email + dashboard banner |
| Order completion rate below | 90% | 80% | Dashboard alert |
| Avg prep time exceeding target by | 25% | 50% | Dashboard alert |
| Table utilization below | 40% | 25% | Weekly briefing mention |
| Menu item with 0 orders in 7 days | — | Any | AI briefing recommendation |

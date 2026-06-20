---
type: Metric
title: Gross Revenue
description: Total gross revenue from all completed orders, tracked daily.
tags:
  - financial
  - core
  - executive
timestamp: 2026-06-20T00:00:00Z
---

# Gross Revenue

Gross revenue is the sum of all `total_line` values from the [orders](../tables/orders.md) table where `status = 'delivered'`.

## Definition

```sql
SELECT
  order_date,
  SUM(total_line) AS gross_revenue
FROM `acme-prod.analytics.orders`
WHERE status = 'delivered'
GROUP BY order_date
ORDER BY order_date
```

## Business Rules

- Only **delivered** orders count toward revenue
- Cancelled and pending orders are excluded
- Refunds are not subtracted here (see Net Revenue metric)
- Currency is always USD

## Related Concepts

- Source table: [orders](../tables/orders.md)
- Related table: [customers](../tables/customers.md) for per-customer revenue breakdown
